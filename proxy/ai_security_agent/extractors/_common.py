"""Shared helpers for parsing the OpenAI/Anthropic-style `messages` shape,
where `content` is either a plain string or a list of typed content blocks
(`[{"type": "text", "text": "..."}]`, interleaved with image/tool blocks).
"""

from __future__ import annotations

from typing import Any


def content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "\n".join(parts)
    return ""


def last_user_message_text(messages: list[dict[str, Any]]) -> str | None:
    for message in reversed(messages):
        if message.get("role") == "user":
            text = content_to_text(message.get("content"))
            return text or None
    return None
