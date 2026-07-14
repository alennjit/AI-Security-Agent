"""Best-effort generic extractor for consumer chat web UIs (chat.openai.com,
claude.ai, gemini.google.com, copilot.microsoft.com, etc.).

Unlike the documented API extractors, these web UIs use unofficial,
undocumented internal endpoints that change without notice. This extractor
does not try to match one provider's exact schema — it walks the parsed
JSON body looking for the first plausible "what the user typed" field among
a set of commonly-seen key names, and returns None if nothing matches.

This will need periodic maintenance as providers change their frontend
request shapes. Treat findings from this extractor as lower-confidence than
the documented-API extractors.
"""

from __future__ import annotations

import json
from typing import Any

# Common key names seen across ChatGPT/Claude/Gemini/Copilot web frontends
# for the user-authored message field.
_CANDIDATE_KEYS = ("prompt", "message", "text", "query", "content", "input")


def _walk(node: Any) -> str | None:
    if isinstance(node, dict):
        for key in _CANDIDATE_KEYS:
            value = node.get(key)
            if isinstance(value, str) and value.strip():
                return value
        for value in node.values():
            found = _walk(value)
            if found:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _walk(item)
            if found:
                return found
    return None


def extract(body: bytes) -> str | None:
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return _walk(payload)
