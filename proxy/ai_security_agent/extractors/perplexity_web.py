"""Extractor for the Perplexity web app's ask request (`/rest/sse/perplexity_ask`).

Verified against a captured request: a JSON body with the typed text at top-level
`query_str`, repeated at `params.dsl_query`. Perplexity also echoes the query into
analytics beacons (`/rest/event/analytics`); the registry's path pattern excludes
those so a prompt is reported once.
"""

from __future__ import annotations

import json


def extract(body: bytes) -> str | None:
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict):
        return None

    query = payload.get("query_str")
    if not isinstance(query, str) or not query.strip():
        params = payload.get("params")
        query = params.get("dsl_query") if isinstance(params, dict) else None
    return query if isinstance(query, str) and query.strip() else None
