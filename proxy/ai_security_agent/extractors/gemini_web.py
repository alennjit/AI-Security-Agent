"""Extractor for the Gemini web app (gemini.google.com) chat submit request.

Verified against a captured request. The body is `application/x-www-form-urlencoded`
with a single relevant field, `f.req`, whose value is JSON containing another JSON
document as a *string*:

    f.req = [null, "<json string>"]
    inner = [[ "<prompt text>", 0, null, ... ], ["en"], null, "<token>", ...]

The prompt is `inner[0][0]`. Google changes this wire format without notice, so every
step is defensive and a mismatch returns None (nothing is reported) rather than raising.
"""

from __future__ import annotations

import json
from urllib.parse import parse_qs


def extract(body: bytes) -> str | None:
    try:
        fields = parse_qs(body.decode("utf-8"), keep_blank_values=True)
        f_req = json.loads(fields["f.req"][0])
        inner = json.loads(f_req[1])
        prompt = inner[0][0]
    except (KeyError, IndexError, TypeError, ValueError, UnicodeDecodeError):
        return None
    return prompt if isinstance(prompt, str) and prompt.strip() else None
