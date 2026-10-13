"""mitmproxy addon: wires domains -> extractors -> DLP classifiers ->
backend event submission.

Run with:  mitmdump -s ai_security_agent/addon.py   (with the `proxy/` directory on
PYTHONPATH so `ai_security_agent` is importable). See docs/LOCAL_PROXY_TESTING.md.

Behaviour guarantees:
  * Detect-and-alert only. Traffic is never blocked or modified.
  * Raw prompt text and raw matches never leave this process — only the
    redacted summary built by `build_event`.
  * Event delivery runs on a worker thread, so a slow or down backend can never
    stall a user's request.
"""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor
from importlib import import_module
from typing import Any

import httpx

from ai_security_agent.dlp.classifiers import ClassificationResult, scan
from ai_security_agent.domains import AiServiceEndpoint, lookup_host

logger = logging.getLogger("ai_security_agent")

BACKEND_EVENTS_URL = os.environ.get("AISA_BACKEND_EVENTS_URL", "http://127.0.0.1:8000/events")
MAX_BODY_BYTES = int(os.environ.get("AISA_MAX_BODY_BYTES", str(2 * 1024 * 1024)))
POST_TIMEOUT_SECONDS = 5.0


def build_event(
    host: str,
    endpoint: AiServiceEndpoint,
    result: ClassificationResult,
    client_ip: str | None,
) -> dict[str, Any]:
    """Build the redacted event payload sent to the backend (no prompt text, no raw matches)."""
    return {
        "host": host,
        "provider": endpoint.provider,
        "surface": endpoint.surface,
        "risk_score": result.risk_score,
        "rationale": result.rationale,
        "categories": sorted(result.categories),
        "finding_count": len(result.findings),
        "client_ip": client_ip,
    }


def _client_ip(flow: Any) -> str | None:
    """Best-effort client address of the device that made the request."""
    try:
        peer = flow.client_conn.peername
        return str(peer[0]) if peer else None
    except (AttributeError, IndexError, TypeError):
        return None


class AiSecurityAgentAddon:
    """Inspect requests to known AI services and report findings to the backend."""

    def __init__(self) -> None:
        self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="aisa-post")

    def request(self, flow: Any) -> None:
        host = flow.request.pretty_host
        endpoint = lookup_host(host)
        if endpoint is None:
            return

        body = self._read_body(flow)
        if body is None:
            return

        try:
            extractor = import_module(f"ai_security_agent.extractors.{endpoint.extractor}")
        except ImportError:
            logger.warning("No extractor module '%s' for host %s", endpoint.extractor, host)
            return

        prompt_text = extractor.extract(body)
        if not prompt_text:
            return

        result = scan(prompt_text)
        if not result.flagged:
            return

        event = build_event(host, endpoint, result, _client_ip(flow))
        logger.info(
            "Flagged prompt: provider=%s risk=%s categories=%s",
            event["provider"], event["risk_score"], ",".join(event["categories"]),
        )
        self._pool.submit(self._post_event, event)

    @staticmethod
    def _read_body(flow: Any) -> bytes | None:
        """Return the (decompressed) request body, or None if absent or too large."""
        raw_len = len(flow.request.raw_content or b"")
        if raw_len == 0 or raw_len > MAX_BODY_BYTES:
            return None
        try:
            return flow.request.get_content() or None
        except ValueError:
            logger.warning("Could not decode request body for %s", flow.request.pretty_host)
            return None

    @staticmethod
    def _post_event(event: dict[str, Any]) -> None:
        try:
            httpx.post(BACKEND_EVENTS_URL, json=event, timeout=POST_TIMEOUT_SECONDS)
        except httpx.HTTPError as exc:
            logger.error("Failed to submit event to backend: %s", exc)

    def done(self) -> None:
        """mitmproxy shutdown hook: flush pending event posts."""
        self._pool.shutdown(wait=True)


addons = [AiSecurityAgentAddon()]
