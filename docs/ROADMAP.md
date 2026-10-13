# Roadmap

## Phase 1 — DLP engine (current)
- [x] AI service domain/endpoint registry
- [x] DLP classifiers: credentials, PII, confidential keywords, 1-10 risk
      scoring, redaction-by-design
- [x] Per-provider prompt extractors (OpenAI, Anthropic, Google, generic
      web-UI JSON)
- [x] Backend ingestion API (FastAPI) + event store (SQLite)
- [x] mitmproxy addon validated against live API traffic (OpenAI, Anthropic,
      Gemini) through a local test proxy — see `docs/LOCAL_PROXY_TESTING.md`
- [x] Browser web-UI traffic: Gemini and Perplexity captured from real browser
      sessions, parsers verified; endpoint-aware registry ignores telemetry that echoes prompts
- [ ] ChatGPT and claude.ai: capture from signed-in sessions (ChatGPT blocks
      automation via Cloudflare; claude.ai needs a login). Parsers exist but are unverified
- [ ] Microsoft Copilot: chats over a WebSocket — needs a message-level hook
- [ ] Multipart uploads / file attachments and streaming request bodies

## Phase 2 — Dashboard
- [x] React + TypeScript + Vite dashboard (mirrors Lightweight-SIEM)
- [x] Event feed, summary tiles, breakdown by AI service and data type, filters,
      live refresh, per-event rationale
- [ ] Per-device drill-down view and time-range filter/trend chart
- [ ] Auth (this needs to exist before this is ever pointed at real traffic)

## Phase 3 — Deployment
- [x] Per-client **name-constrained** inspection CA generator (a stolen key cannot
      impersonate sites outside the AI-service list; enforcement verified)
- [x] Trust distribution scripts for RMM/GPO: install (thumbprint + constraint checks,
      `-WhatIf`) and rollback
- [x] PAC generator driven by the service registry (verified hosts only by default, fail-open)
- [x] PAC GPO create/remove scripts (unlinked by default, pilot-OU linking only)
- [x] Read-only deployment checker; proxy-host config + systemd unit template
- [x] Disclosure notice template for client AUPs (`docs/templates/`, needs counsel review)
- [ ] **Pilot on a real domain**: run the GPO scripts against a test OU (not yet done)
- [ ] Per-application cert-pinning compatibility check on the AI apps a client actually uses
- [ ] Block or disable QUIC/HTTP3 to monitored hosts so browsers can't bypass the proxy
- [ ] Firefox enterprise-roots policy; mobile/BYOD strategy

## Phase 4 — Multi-tenant / product-ization
- [ ] Multi-client separation in backend (this becomes a real product across
      MSP clients, not a single-org tool)
- [ ] Per-client custom keyword/config lists
- [ ] Billing/licensing if this becomes an LLC-sold product

## Explicitly deferred / not planned for v1
- Blocking/preventing the prompt from being sent (v1 is detect-and-alert
  only — revisit once false-positive rates on real traffic are known)
- Source-code-specific detection (regex-only heuristics are too noisy;
  needs a real classifier, not v1 scope)
- Full endpoint agent (clipboard/process monitoring) — network/DNS proxy
  covers the agreed v1 scope; revisit only if network-layer coverage proves
  insufficient
