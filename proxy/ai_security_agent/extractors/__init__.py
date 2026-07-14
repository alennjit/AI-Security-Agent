"""Per-provider request-body -> user-prompt-text extractors.

Each module exposes `extract(body: bytes) -> str | None`, returning the
concatenated user-authored prompt text from the *most recent* user turn in
the request (not system prompts, not prior assistant turns, not the whole
request body) — or None if the body doesn't match the expected shape.
"""
