"""Extractor for Google's Gemini `generateContent` API request bodies."""

from __future__ import annotations

import json


def extract(body: bytes) -> str | None:
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    contents = payload.get("contents")
    if not isinstance(contents, list):
        return None

    for entry in reversed(contents):
        if not isinstance(entry, dict):
            continue
        if entry.get("role") not in (None, "user"):
            continue
        parts = entry.get("parts")
        if not isinstance(parts, list):
            continue
        text = "\n".join(
            str(part.get("text", ""))
            for part in parts
            if isinstance(part, dict) and "text" in part
        )
        if text:
            return text

    return None
