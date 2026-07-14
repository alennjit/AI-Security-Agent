"""Registry of known AI service domains/endpoints the proxy should inspect.

Each entry maps a hostname (as seen in the TLS SNI / Host header) to the
provider it belongs to and which extractor knows how to pull prompt text out
of requests to it. New providers/domains get added here as they're found —
this list will never be exhaustive, so `is_monitored_host` also does a
suffix match against known parent domains for providers that use many
subdomains (e.g. *.openai.com).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AiServiceEndpoint:
    """A single AI provider's host and how to interpret traffic to it."""

    host: str
    provider: str
    surface: str  # "web_ui" or "api"
    extractor: str  # module name under ai_security_agent.extractors


KNOWN_ENDPOINTS: tuple[AiServiceEndpoint, ...] = (
    # OpenAI
    AiServiceEndpoint("chat.openai.com", "openai", "web_ui", "web_ui"),
    AiServiceEndpoint("chatgpt.com", "openai", "web_ui", "web_ui"),
    AiServiceEndpoint("api.openai.com", "openai", "api", "openai"),

    # Anthropic
    AiServiceEndpoint("claude.ai", "anthropic", "web_ui", "web_ui"),
    AiServiceEndpoint("api.anthropic.com", "anthropic", "api", "anthropic"),

    # Google
    AiServiceEndpoint("gemini.google.com", "google", "web_ui", "web_ui"),
    AiServiceEndpoint("bard.google.com", "google", "web_ui", "web_ui"),
    AiServiceEndpoint(
        "generativelanguage.googleapis.com", "google", "api", "google"
    ),

    # Microsoft Copilot
    AiServiceEndpoint("copilot.microsoft.com", "microsoft", "web_ui", "web_ui"),

    # Perplexity
    AiServiceEndpoint("www.perplexity.ai", "perplexity", "web_ui", "web_ui"),
    AiServiceEndpoint("api.perplexity.ai", "perplexity", "api", "web_ui"),

    # Mistral
    AiServiceEndpoint("chat.mistral.ai", "mistral", "web_ui", "web_ui"),
    AiServiceEndpoint("api.mistral.ai", "mistral", "api", "web_ui"),

    # xAI
    AiServiceEndpoint("grok.com", "xai", "web_ui", "web_ui"),
    AiServiceEndpoint("api.x.ai", "xai", "api", "web_ui"),

    # Cohere
    AiServiceEndpoint("api.cohere.ai", "cohere", "api", "web_ui"),
)

_HOST_INDEX: dict[str, AiServiceEndpoint] = {e.host: e for e in KNOWN_ENDPOINTS}


def lookup_host(host: str) -> AiServiceEndpoint | None:
    """Return the matching endpoint config for a request Host/SNI value.

    Does an exact match first, then a suffix match so subdomains of a known
    host (e.g. `edge.chatgpt.com`) still resolve to the parent provider.
    """
    host = host.lower().rstrip(".")
    if host in _HOST_INDEX:
        return _HOST_INDEX[host]
    for known_host, endpoint in _HOST_INDEX.items():
        if host.endswith("." + known_host):
            return endpoint
    return None


def is_monitored_host(host: str) -> bool:
    return lookup_host(host) is not None
