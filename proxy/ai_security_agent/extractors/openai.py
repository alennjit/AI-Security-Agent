"""Extractor for OpenAI's Chat Completions / Responses API request bodies."""

from __future__ import annotations

import json

from ai_security_agent.extractors._common import last_user_message_text


def extract(body: bytes) -> str | None:
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    messages = payload.get("messages")
    if isinstance(messages, list):
        return last_user_message_text(messages)

    # Responses API: {"input": "..."} or {"input": [{"role": "user", ...}]}
    input_field = payload.get("input")
    if isinstance(input_field, str):
        return input_field or None
    if isinstance(input_field, list):
        return last_user_message_text(input_field)

    return None
