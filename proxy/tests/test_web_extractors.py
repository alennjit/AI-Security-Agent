"""Tests for the chat-web-UI extractors.

Gemini and Perplexity fixtures follow the structure of requests captured from the real
sites (strings replaced with synthetic text). ChatGPT and claude.ai fixtures follow the
commonly reported formats and are NOT verified against real traffic.
"""

from __future__ import annotations

import json
from urllib.parse import urlencode

from ai_security_agent.extractors import chatgpt_web, claude_web, gemini_web, perplexity_web


def gemini_body(prompt: str) -> bytes:
    inner = [[prompt, 0, None, None, None, None], ["en"], None, "x" * 40, "y" * 32, None]
    f_req = json.dumps([None, json.dumps(inner)])
    return urlencode({"f.req": f_req, "at": "token", "": ""}).encode()


def test_gemini_extracts_prompt_from_nested_form_json():
    assert gemini_web.extract(gemini_body("my key is AKIAIOSFODNN7EXAMPLE")) == "my key is AKIAIOSFODNN7EXAMPLE"


def test_gemini_ignores_batchexecute_style_bodies():
    other = urlencode({"f.req": json.dumps([[["MkEWBc", "[]", None, "generic"]]]), "at": "t"}).encode()
    assert gemini_web.extract(other) is None


def test_gemini_survives_garbage():
    for body in (b"", b"not a form", urlencode({"f.req": "{broken"}).encode(),
                 urlencode({"f.req": json.dumps([None, "[]"])}).encode()):
        assert gemini_web.extract(body) is None


def test_perplexity_prefers_query_str():
    body = json.dumps({"query_str": "ssn 219-09-9999", "params": {"dsl_query": "ssn 219-09-9999"}}).encode()
    assert perplexity_web.extract(body) == "ssn 219-09-9999"


def test_perplexity_falls_back_to_dsl_query():
    body = json.dumps({"params": {"dsl_query": "hello there", "mode": "copilot"}}).encode()
    assert perplexity_web.extract(body) == "hello there"


def test_perplexity_survives_garbage():
    assert perplexity_web.extract(b"nope") is None
    assert perplexity_web.extract(json.dumps(["list"]).encode()) is None
    assert perplexity_web.extract(json.dumps({"query_str": "   "}).encode()) is None


def test_chatgpt_extracts_last_user_message_text_parts():
    body = json.dumps({
        "action": "next",
        "messages": [
            {"author": {"role": "user"}, "content": {"content_type": "text", "parts": ["earlier question"]}},
            {"author": {"role": "assistant"}, "content": {"content_type": "text", "parts": ["answer"]}},
            {"author": {"role": "user"}, "content": {"content_type": "multimodal_text",
                                                      "parts": ["token ghp_" + "a" * 36, {"asset_pointer": "file-1"}]}},
        ],
    }).encode()
    assert chatgpt_web.extract(body) == "token ghp_" + "a" * 36


def test_chatgpt_survives_garbage():
    assert chatgpt_web.extract(b"{}") is None
    assert chatgpt_web.extract(json.dumps({"messages": "nope"}).encode()) is None
    assert chatgpt_web.extract(json.dumps({"messages": [{"author": {"role": "assistant"}}]}).encode()) is None


def test_claude_web_extracts_prompt():
    assert claude_web.extract(json.dumps({"prompt": "hello", "timezone": "UTC"}).encode()) == "hello"
    assert claude_web.extract(json.dumps({"prompt": ""}).encode()) is None
    assert claude_web.extract(b"garbage") is None
