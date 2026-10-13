"""Extractor for the ChatGPT web app conversation request.

UNVERIFIED: not captured — chatgpt.com is behind a Cloudflare bot check that blocks
automated browsers, so this follows the commonly reported format:

    {"action": "next",
     "messages": [{"author": {"role": "user"},
                   "content": {"content_type": "text", "parts": ["<prompt>", ...]}}], ...}

It takes the text parts of the last user message and ignores non-text parts (such as
image references). A mismatch returns None. Verify with a human-driven capture session
(see docs/LOCAL_PROXY_TESTING.md) before relying on it.
"""

from __future__ import annotations

import json
from typing import Any


def _text_of(message: dict[str, Any]) -> str:
    content = message.get("content")
    if not isinstance(content, dict):
        return ""
    parts = content.get("parts")
    if not isinstance(parts, list):
        return ""
    return "\n".join(p for p in parts if isinstance(p, str))


def extract(body: bytes) -> str | None:
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return None
    messages = payload.get("messages") if isinstance(payload, dict) else None
    if not isinstance(messages, list):
        return None
    for message in reversed(messages):
        if not isinstance(message, dict):
            continue
        author = message.get("author")
        if isinstance(author, dict) and author.get("role") == "user":
            return _text_of(message).strip() or None
    return None
