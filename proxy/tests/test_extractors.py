import json

from ai_security_agent.extractors import anthropic, google, openai, web_ui


def test_openai_chat_completions_extracts_last_user_message():
    body = json.dumps(
        {
            "model": "gpt-4",
            "messages": [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "first question"},
                {"role": "assistant", "content": "first answer"},
                {"role": "user", "content": "AKIAABCDEFGHIJKLMNOP is my key"},
            ],
        }
    ).encode()
    assert openai.extract(body) == "AKIAABCDEFGHIJKLMNOP is my key"


def test_openai_responses_api_string_input():
    body = json.dumps({"model": "gpt-4", "input": "hello there"}).encode()
    assert openai.extract(body) == "hello there"


def test_openai_multimodal_content_blocks():
    body = json.dumps(
        {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "part one"},
                        {"type": "image_url", "image_url": {"url": "..."}},
                        {"type": "text", "text": "part two"},
                    ],
                }
            ]
        }
    ).encode()
    assert openai.extract(body) == "part one\npart two"


def test_openai_malformed_body_returns_none():
    assert openai.extract(b"not json") is None


def test_anthropic_messages_api_extracts_last_user_message():
    body = json.dumps(
        {
            "model": "claude-opus-4",
            "messages": [
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "hello"},
                {"role": "user", "content": "my SSN is 219-09-9999"},
            ],
        }
    ).encode()
    assert anthropic.extract(body) == "my SSN is 219-09-9999"


def test_google_generate_content_extracts_last_user_parts():
    body = json.dumps(
        {
            "contents": [
                {"role": "user", "parts": [{"text": "earlier turn"}]},
                {"role": "model", "parts": [{"text": "reply"}]},
                {"role": "user", "parts": [{"text": "confidential data here"}]},
            ]
        }
    ).encode()
    assert google.extract(body) == "confidential data here"


def test_web_ui_finds_prompt_key_anywhere_in_nested_body():
    body = json.dumps(
        {"conversation_id": "abc", "action": "next", "message": "actual user prompt"}
    ).encode()
    assert web_ui.extract(body) == "actual user prompt"


def test_web_ui_returns_none_when_no_candidate_field_present():
    body = json.dumps({"conversation_id": "abc", "action": "next"}).encode()
    assert web_ui.extract(body) is None
