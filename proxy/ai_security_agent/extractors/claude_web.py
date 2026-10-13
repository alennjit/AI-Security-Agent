"""Extractor for the claude.ai web app completion request.

UNVERIFIED: not captured — claude.ai requires a signed-in account, which an automated
browser run doesn't have. This follows the commonly reported format: a JSON body with the
typed text in a top-level `prompt` field posted to
`/api/organizations/<org>/chat_conversations/<id>/completion`. A mismatch returns None.
Verify with a human-driven capture session before relying on it.
"""

from __future__ import annotations

import json


def extract(body: bytes) -> str | None:
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return None
    prompt = payload.get("prompt") if isinstance(payload, dict) else None
    return prompt if isinstance(prompt, str) and prompt.strip() else None
