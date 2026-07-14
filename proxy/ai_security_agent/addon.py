"""mitmproxy addon: wires domains -> extractors -> DLP classifiers ->
backend event submission.

Run with: `mitmdump -s ai_security_agent/addon.py` against a client whose
traffic is routed through this proxy and that trusts mitmproxy's root CA
(see docs/ARCHITECTURE.md and deploy/ for how that gets distributed).

NOT yet validated against live captured traffic from each provider — the
extractors were built and tested against synthetic payloads matching each
provider's documented (or observed, for web UIs) request shape. Before
relying on this against real traffic, capture real requests per provider
and confirm the extractors still match. See README.md status table.
"""

from __future__ import annotations

import logging
from importlib import import_module

import httpx
from mitmproxy import http

from ai_security_agent.dlp.classifiers import scan
from ai_security_agent.domains import lookup_host

logger = logging.getLogger("ai_security_agent")

BACKEND_EVENTS_URL = "http://127.0.0.1:8000/events"


class AiSecurityAgentAddon:
    def request(self, flow: http.HTTPFlow) -> None:
        host = flow.request.pretty_host
        endpoint = lookup_host(host)
        if endpoint is None:
            return

        try:
            extractor = import_module(f"ai_security_agent.extractors.{endpoint.extractor}")
        except ImportError:
            logger.warning("No extractor module '%s' for host %s", endpoint.extractor, host)
            return

        prompt_text = extractor.extract(flow.request.content or b"")
        if not prompt_text:
            return

        result = scan(prompt_text)
        if not result.flagged:
            return

        event = {
            "host": host,
            "provider": endpoint.provider,
            "surface": endpoint.surface,
            "risk_score": result.risk_score,
            "rationale": result.rationale,
            "categories": sorted(result.categories),
            "finding_count": len(result.findings),
        }

        try:
            httpx.post(BACKEND_EVENTS_URL, json=event, timeout=5.0)
        except httpx.HTTPError as exc:
            logger.error("Failed to submit event to backend: %s", exc)


addons = [AiSecurityAgentAddon()]
