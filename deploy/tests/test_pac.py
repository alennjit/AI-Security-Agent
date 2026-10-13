"""Tests for the PAC generator, including evaluating the generated JavaScript with Node."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "pac" / "generate_pac.py"
spec = importlib.util.spec_from_file_location("generate_pac", SCRIPT)
generate_pac = importlib.util.module_from_spec(spec)
sys.modules["generate_pac"] = generate_pac
spec.loader.exec_module(generate_pac)

PROXY = "proxy.corp.example:8080"
NODE = shutil.which("node") or (r"C:\Program Files\nodejs\node.exe" if Path(r"C:\Program Files\nodejs\node.exe").exists() else None)


def evaluate(pac: str, url: str, host: str) -> str:
    """Run FindProxyForURL under Node with the standard PAC helper dnsDomainIs stubbed in."""
    harness = pac + f"""
function dnsDomainIs(host, domain) {{ return host.length >= domain.length && host.substring(host.length - domain.length) === domain; }}
console.log(FindProxyForURL({json.dumps(url)}, {json.dumps(host)}));
"""
    return subprocess.run([NODE, "-e", harness], capture_output=True, text=True, check=True, shell=False).stdout.strip()


def test_default_includes_only_verified_hosts():
    hosts = generate_pac.monitored_hosts()
    assert {"api.openai.com", "api.anthropic.com", "gemini.google.com", "www.perplexity.ai"} <= set(hosts)
    assert "claude.ai" not in hosts        # parser written but unverified
    assert "chatgpt.com" not in hosts
    assert "copilot.microsoft.com" not in hosts


def test_include_unverified_adds_pilot_hosts():
    hosts = generate_pac.monitored_hosts(include_unverified=True)
    assert {"claude.ai", "chatgpt.com", "copilot.microsoft.com"} <= set(hosts)


def test_proxy_value_is_validated_because_it_is_embedded_in_javascript():
    for bad in ("", "no-port", "host:80; evil()", 'host:80"); alert(1); ("', "http://host:80"):
        with pytest.raises(ValueError):
            generate_pac.build_pac(bad, ["api.openai.com"])


def test_fail_open_by_default_and_fail_closed_on_request():
    assert f'"PROXY {PROXY}; DIRECT"' in generate_pac.build_pac(PROXY, ["a.example"])
    closed = generate_pac.build_pac(PROXY, ["a.example"], fail_open=False)
    assert f'"PROXY {PROXY}"' in closed
    assert f'"PROXY {PROXY}; DIRECT"' not in closed


@pytest.mark.skipif(NODE is None, reason="node not available to evaluate the PAC file")
def test_generated_pac_routes_correctly_when_evaluated():
    pac = generate_pac.build_pac(PROXY, generate_pac.monitored_hosts())
    expect_proxy = f"PROXY {PROXY}; DIRECT"
    assert evaluate(pac, "https://api.openai.com/v1/chat/completions", "api.openai.com") == expect_proxy
    assert evaluate(pac, "https://gemini.google.com/app", "gemini.google.com") == expect_proxy
    assert evaluate(pac, "https://edge.api.openai.com/x", "edge.api.openai.com") == expect_proxy   # subdomain
    assert evaluate(pac, "wss://api.openai.com/ws", "api.openai.com") == expect_proxy
    assert evaluate(pac, "https://API.OpenAI.com/", "API.OpenAI.com") == expect_proxy             # case-insensitive


@pytest.mark.skipif(NODE is None, reason="node not available to evaluate the PAC file")
def test_everything_else_goes_direct():
    pac = generate_pac.build_pac(PROXY, generate_pac.monitored_hosts())
    assert evaluate(pac, "https://example.com/", "example.com") == "DIRECT"
    assert evaluate(pac, "https://mail.google.com/", "mail.google.com") == "DIRECT"   # not gemini.google.com
    assert evaluate(pac, "https://www.google.com/", "www.google.com") == "DIRECT"
    assert evaluate(pac, "http://api.openai.com/", "api.openai.com") == "DIRECT"      # plain http not routed
    assert evaluate(pac, "https://notapi.openai.com.evil.example/", "notapi.openai.com.evil.example") == "DIRECT"
    assert evaluate(pac, "https://evilapi.openai.com.example/", "evilapi.openai.com.example") == "DIRECT"


# --- proxy-host config invariants -------------------------------------------------

CONFIG = Path(__file__).resolve().parents[1] / "proxy-host" / "config.yaml"


def _active_lines(path: Path) -> list[str]:
    return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.lstrip().startswith("#")]


def test_proxy_config_pins_the_settings_the_constrained_ca_depends_on():
    active = _active_lines(CONFIG)
    assert "upstream_cert: false" in active      # without it, Google/Perplexity certs break under the name-constrained CA
    assert "ssl_insecure: false" in active
    assert "block_global: true" in active
