"""Developer tool: record the *shape* of POST requests to monitored AI hosts.

Used to author and verify per-provider extractors for chat web UIs, whose request
formats are undocumented and change. For each request it writes ONE JSON line with:
  host, path, method, content-type, body length, and a "shape" in which every string
  is replaced by `<str:LEN>` — no prompt text is ever written to disk.
If the environment variable AISA_CANARY is set (a unique string you type into the
chat UI yourself), the shape also records the JSON path where that canary appears,
which is exactly what an extractor needs to know.

Run (dev only, with the proxy on localhost):
  AISA_CANARY=CANARY-7Q2X AISA_SHAPES_OUT=E:/aisa-dev/captures/shapes.jsonl \
  PYTHONPATH=proxy mitmdump --listen-port 8081 --set confdir=... -s proxy/tools/capture_shapes.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl

from ai_security_agent.domains import lookup_host

CANARY = os.environ.get("AISA_CANARY", "")
OUT = Path(os.environ.get("AISA_SHAPES_OUT", "shapes.jsonl"))
MAX_DEPTH = 8


def _shape(value: Any, path: str, hits: list[str], depth: int = 0) -> Any:
    """Return a copy of `value` with strings replaced by length markers; record canary paths."""
    if depth > MAX_DEPTH:
        return "<deep>"
    if isinstance(value, dict):
        return {k: _shape(v, f"{path}.{k}", hits, depth + 1) for k, v in value.items()}
    if isinstance(value, list):
        # keep the first few items; real payloads can have hundreds of history turns
        return [_shape(v, f"{path}[{i}]", hits, depth + 1) for i, v in enumerate(value[:6])]
    if isinstance(value, str):
        if CANARY and CANARY in value:
            hits.append(path)
        nested = _try_json(value)
        if nested is not None:
            return {"<json-in-string>": _shape(nested, path + "<json>", hits, depth + 1)}
        return f"<str:{len(value)}>"
    return value if isinstance(value, (int, float, bool)) or value is None else f"<{type(value).__name__}>"


def _try_json(text: str) -> Any | None:
    stripped = text.lstrip()
    if stripped[:1] in "[{" and len(text) > 2:
        try:
            return json.loads(text)
        except ValueError:
            return None
    return None


def _describe_body(content_type: str, body: bytes) -> tuple[Any, list[str]]:
    hits: list[str] = []
    text = body.decode("utf-8", errors="replace")
    if "json" in content_type:
        try:
            return _shape(json.loads(text), "$", hits), hits
        except ValueError:
            pass
    if "x-www-form-urlencoded" in content_type:
        fields = {k: _shape(v, f"form.{k}", hits) for k, v in parse_qsl(text, keep_blank_values=True)}
        return {"<form>": fields}, hits
    if CANARY and CANARY in text:
        hits.append("raw-body")
    return f"<{content_type or 'unknown'}:{len(body)} bytes>", hits


class CaptureShapes:
    def request(self, flow: Any) -> None:
        host = flow.request.pretty_host
        if lookup_host(host) is None or flow.request.method != "POST":
            return
        body = flow.request.get_content() or b""
        if not body:
            return
        ctype = flow.request.headers.get("content-type", "").split(";")[0].strip().lower()
        shape, hits = _describe_body(ctype, body)
        record = {
            "host": host,
            "path": flow.request.path.split("?")[0],
            "content_type": ctype,
            "length": len(body),
            "canary_paths": hits,
            "shape": shape,
        }
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")


addons = [CaptureShapes()]
