"""Registry of known AI service endpoints the proxy should inspect.

An entry matches on the request **host** (exact, or any subdomain of it) and,
optionally, on the request **path**. Chat web UIs talk to many endpoints —
analytics beacons, autosuggest, CSP reports — and some echo the prompt text, so a
web-UI entry should carry a `path_pattern` that selects only the one endpoint that
submits a prompt. Entries without a pattern inspect every request to the host
(appropriate for documented APIs where each call is a prompt).

`verified` records whether the request format was confirmed against real captured
traffic (see docs/LOCAL_PROXY_TESTING.md) rather than written from documentation or
from the provider's commonly reported format.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class AiServiceEndpoint:
    """A single AI provider endpoint and how to interpret traffic to it."""

    host: str
    provider: str
    surface: str  # "web_ui" or "api"
    extractor: str  # module name under ai_security_agent.extractors
    path_pattern: str | None = None  # regex matched against the path (no query string)
    verified: bool = True

    def matches_path(self, path: str) -> bool:
        if self.path_pattern is None:
            return True
        return re.search(self.path_pattern, path.split("?", 1)[0]) is not None


KNOWN_ENDPOINTS: tuple[AiServiceEndpoint, ...] = (
    # OpenAI — API is documented; the ChatGPT web format is the commonly reported one
    # (backend-api/conversation) and could not be captured: Cloudflare blocks automation.
    AiServiceEndpoint("api.openai.com", "openai", "api", "openai"),
    AiServiceEndpoint("chatgpt.com", "openai", "web_ui", "chatgpt_web",
                      r"^/backend-(api|anon)/(f/)?conversation$", verified=False),
    AiServiceEndpoint("chat.openai.com", "openai", "web_ui", "chatgpt_web",
                      r"^/backend-(api|anon)/(f/)?conversation$", verified=False),

    # Anthropic — claude.ai needs a login, so its web format is unverified.
    AiServiceEndpoint("api.anthropic.com", "anthropic", "api", "anthropic"),
    AiServiceEndpoint("claude.ai", "anthropic", "web_ui", "claude_web",
                      r"^/api/.+/(retry_)?completion$", verified=False),

    # Google
    AiServiceEndpoint("generativelanguage.googleapis.com", "google", "api", "google"),
    AiServiceEndpoint("gemini.google.com", "google", "web_ui", "gemini_web",
                      r"BardFrontendService/StreamGenerate$"),
    AiServiceEndpoint("bard.google.com", "google", "web_ui", "gemini_web",
                      r"BardFrontendService/StreamGenerate$", verified=False),

    # Perplexity
    AiServiceEndpoint("www.perplexity.ai", "perplexity", "web_ui", "perplexity_web",
                      r"^/rest/sse/perplexity_ask$"),
    AiServiceEndpoint("api.perplexity.ai", "perplexity", "api", "openai"),

    # Not yet captured: keep the permissive generic parser, flagged as unverified.
    # Microsoft Copilot chats over a WebSocket, which this add-on does not inspect yet.
    AiServiceEndpoint("copilot.microsoft.com", "microsoft", "web_ui", "web_ui", verified=False),
    AiServiceEndpoint("chat.mistral.ai", "mistral", "web_ui", "web_ui", verified=False),
    AiServiceEndpoint("api.mistral.ai", "mistral", "api", "openai"),
    AiServiceEndpoint("grok.com", "xai", "web_ui", "web_ui", verified=False),
    AiServiceEndpoint("api.x.ai", "xai", "api", "openai"),
    AiServiceEndpoint("api.cohere.ai", "cohere", "api", "web_ui", verified=False),
)


def _host_matches(entry_host: str, host: str) -> bool:
    return host == entry_host or host.endswith("." + entry_host)


def lookup_request(host: str, path: str) -> AiServiceEndpoint | None:
    """Return the endpoint entry for a request's host *and* path, or None.

    Exact host matches win over subdomain matches. Within a host, the first entry whose
    path pattern matches is used, so a more specific entry must be listed first.
    """
    host = host.lower().rstrip(".")
    candidates = [e for e in KNOWN_ENDPOINTS if e.host == host] or [
        e for e in KNOWN_ENDPOINTS if _host_matches(e.host, host)
    ]
    for entry in candidates:
        if entry.matches_path(path):
            return entry
    return None


def lookup_host(host: str) -> AiServiceEndpoint | None:
    """Return the first entry for a host, ignoring path (used to decide what to watch)."""
    host = host.lower().rstrip(".")
    for entry in KNOWN_ENDPOINTS:
        if entry.host == host:
            return entry
    for entry in KNOWN_ENDPOINTS:
        if _host_matches(entry.host, host):
            return entry
    return None


def is_monitored_host(host: str) -> bool:
    return lookup_host(host) is not None
