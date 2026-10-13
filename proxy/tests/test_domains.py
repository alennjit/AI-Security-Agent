from ai_security_agent.domains import is_monitored_host, lookup_host


def test_exact_match_known_host():
    endpoint = lookup_host("api.anthropic.com")
    assert endpoint is not None
    assert endpoint.provider == "anthropic"
    assert endpoint.surface == "api"


def test_subdomain_suffix_match():
    endpoint = lookup_host("edge.chatgpt.com")
    assert endpoint is not None
    assert endpoint.provider == "openai"


def test_case_and_trailing_dot_normalized():
    assert lookup_host("Claude.AI.") is not None


def test_unknown_host_is_not_monitored():
    assert not is_monitored_host("example.com")
    assert lookup_host("example.com") is None


def test_is_monitored_host_matches_lookup():
    assert is_monitored_host("claude.ai") is True


# --- path-aware matching (web UIs) -------------------------------------------------

from ai_security_agent.domains import lookup_request  # noqa: E402

GEMINI_SUBMIT = "/_/BardChatUi/data/assistant.lamda.BardFrontendService/StreamGenerate"


def test_gemini_submit_endpoint_matches_but_other_endpoints_do_not():
    assert lookup_request("gemini.google.com", GEMINI_SUBMIT).extractor == "gemini_web"
    assert lookup_request("gemini.google.com", "/_/BardChatUi/data/batchexecute") is None
    assert lookup_request("gemini.google.com", "/_/BardChatUi/jserror") is None


def test_perplexity_ask_matches_but_analytics_does_not():
    assert lookup_request("www.perplexity.ai", "/rest/sse/perplexity_ask").extractor == "perplexity_web"
    assert lookup_request("www.perplexity.ai", "/rest/event/analytics") is None
    assert lookup_request("www.perplexity.ai", "/rest/sse/perplexity_ask?x=1") is not None


def test_documented_api_hosts_match_every_path():
    assert lookup_request("api.openai.com", "/v1/chat/completions").surface == "api"
    assert lookup_request("api.anthropic.com", "/v1/messages").provider == "anthropic"


def test_chatgpt_and_claude_web_patterns_are_marked_unverified():
    chat = lookup_request("chatgpt.com", "/backend-api/conversation")
    assert chat is not None and chat.verified is False
    assert lookup_request("chatgpt.com", "/backend-api/me") is None
    claude = lookup_request("claude.ai", "/api/organizations/o1/chat_conversations/c1/completion")
    assert claude is not None and claude.verified is False


def test_verified_flag_true_for_captured_endpoints():
    assert lookup_request("gemini.google.com", GEMINI_SUBMIT).verified is True
    assert lookup_request("www.perplexity.ai", "/rest/sse/perplexity_ask").verified is True


def test_unknown_host_never_matches_a_request():
    assert lookup_request("example.com", "/anything") is None
