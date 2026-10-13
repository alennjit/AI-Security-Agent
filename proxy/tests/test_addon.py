"""Tests for the mitmproxy addon, driven with a fake flow (no live proxy needed)."""

from __future__ import annotations

import gzip
import json
from types import SimpleNamespace

import pytest

from ai_security_agent import addon as addon_module
from ai_security_agent.addon import AiSecurityAgentAddon


class FakeRequest:
    def __init__(self, host: str, body: bytes, gzipped: bool = False) -> None:
        self.pretty_host = host
        self._plain = body
        self.raw_content = gzip.compress(body) if gzipped else body

    def get_content(self) -> bytes:
        return self._plain


def make_flow(host: str, body: bytes, gzipped: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        request=FakeRequest(host, body, gzipped),
        client_conn=SimpleNamespace(peername=("192.168.1.77", 51234)),
    )


@pytest.fixture()
def posted(monkeypatch) -> list[dict]:
    events: list[dict] = []
    monkeypatch.setattr(AiSecurityAgentAddon, "_post_event", staticmethod(events.append))
    return events


def run(flow: SimpleNamespace) -> None:
    agent = AiSecurityAgentAddon()
    agent.request(flow)
    agent.done()  # flush the worker thread


def anthropic_body(prompt: str) -> bytes:
    return json.dumps({"model": "m", "messages": [{"role": "user", "content": prompt}]}).encode()


def test_flagged_prompt_posts_redacted_event(posted):
    run(make_flow("api.anthropic.com", anthropic_body("key AKIAIOSFODNN7EXAMPLE here")))
    assert len(posted) == 1
    event = posted[0]
    assert event["provider"] == "anthropic"
    assert event["client_ip"] == "192.168.1.77"
    assert event["risk_score"] >= 8
    assert "AKIAIOSFODNN7EXAMPLE" not in json.dumps(event)


def test_clean_prompt_posts_nothing(posted):
    run(make_flow("api.anthropic.com", anthropic_body("What's a good banana bread recipe?")))
    assert posted == []


def test_unmonitored_host_is_ignored(posted):
    run(make_flow("example.com", anthropic_body("AKIAIOSFODNN7EXAMPLE")))
    assert posted == []


def test_oversized_body_is_skipped(posted, monkeypatch):
    monkeypatch.setattr(addon_module, "MAX_BODY_BYTES", 10)
    run(make_flow("api.anthropic.com", anthropic_body("AKIAIOSFODNN7EXAMPLE")))
    assert posted == []


def test_malformed_json_does_not_crash(posted):
    run(make_flow("api.openai.com", b"not json at all"))
    assert posted == []


def test_gzipped_body_is_decoded(posted):
    run(make_flow("api.anthropic.com", anthropic_body("ssn 219-09-9999"), gzipped=True))
    assert len(posted) == 1
