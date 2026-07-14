# Architecture

## Goal

Detect confidential data leaving an organization via AI model prompts, at
the network layer, without relying on cooperation from the endpoint or
browser.

## Data flow

```
Client device
   │  (all traffic routed via PAC file / GPO / DHCP option to the proxy,
   │   trusting a deployed root CA for TLS inspection — see deploy/)
   ▼
Forward proxy (mitmproxy + ai_security_agent addon)
   │  1. Match request host against domains.py registry
   │  2. If match: run the provider-specific extractor to pull prompt text
   │     out of the request body (JSON for API calls, form/XHR for web UIs)
   │  3. Run DLP classifiers (proxy/ai_security_agent/dlp/) against the text
   │  4. If any finding: build a redacted Event (never the raw match) and
   │     POST it to the backend
   │  5. Traffic is NOT blocked or modified — v1 is detect-and-alert, not
   │     prevent. Blocking is a phase-3 consideration once false-positive
   │     rates are known (see ROADMAP.md).
   ▼
Backend (FastAPI + SQLite/Postgres)
   │  Stores Events + Findings, exposes them via API
   ▼
Dashboard (React/TS, not yet built)
   Admin views: event feed, risk-scored alerts (1-10 scale, matches the
   scoring convention from Alen's shadow-it-scanner project), per-device/
   per-user trends, drill-down without ever exposing the raw secret value.
```

## Why network/TLS-proxy over a browser extension or full endpoint agent

- Covers API-based usage (scripts, IDE plugins, custom integrations) that a
  browser extension would miss entirely.
- Covers non-Chrome/Edge browsers and any app that calls an AI API directly.
- Reuses a pattern the MSP side of Alen's work already deploys and trusts
  (FortiGate SSL inspection) — client orgs likely already have the
  infrastructure and policy precedent for TLS-inspecting proxies, which
  lowers the deployment barrier vs. asking for browser-extension installs
  on every managed device.
- Trade-off, noted honestly: TLS interception requires a root CA on every
  monitored device. That's a bigger blast-radius deployment step than a
  browser extension, and it breaks certificate pinning on apps that use it
  (some AI vendor mobile apps may pin — needs testing per provider before
  wide rollout). This is exactly why `deploy/` (root CA + PAC/GPO tooling)
  is explicitly *not* being built casually — see CLAUDE.md.

## DLP classifier design

`proxy/ai_security_agent/dlp/classifiers.py` exposes `scan(text: str) ->
ClassificationResult`. It never returns the raw matched substring — only:
category, a truncated/masked snippet (e.g. `AKIA****************1234`),
start/end offset, and a per-category weight. `ClassificationResult`
aggregates these into a 1-10 risk score with a plain-English rationale
string, matching the risk-scoring convention used elsewhere in Alen's
tooling.

Categories implemented so far:
- Cloud/API credentials (AWS access keys, GitHub tokens, Slack tokens,
  generic `-----BEGIN PRIVATE KEY-----` blocks, JWT-shaped strings)
- PII (SSNs, credit card numbers validated via Luhn, email addresses)
- Confidential-material keyword markers (configurable keyword list —
  "confidential", "internal use only", "NDA", "do not distribute", plus a
  per-deployment customizable list for client/project code names)

Not yet implemented (see ROADMAP.md): source-code detection, per-client
custom keyword lists loaded from config rather than hardcoded, ML-based
classification for content that doesn't match a fixed pattern.

## Provider extractors

Each provider's chat API and web UI ships prompt text in a different JSON
shape. `proxy/ai_security_agent/extractors/` has one module per provider
that knows how to pull the user-authored text (not the whole request, not
system prompts/history — just what the user typed) out of a request body.
This is where new providers get added as they show up.
