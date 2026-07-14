"""Extractor for Anthropic's Messages API request bodies."""

from __future__ import annotations

import json

from ai_security_agent.extractors._common import last_user_message_text


def extract(body: bytes) -> str | None:
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    messages = payload.get("messages")
    if not isinstance(messages, list):
        return None
    return last_user_message_text(messages)
