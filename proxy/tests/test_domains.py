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
