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
- [ ] Validate browser web-UI traffic (chatgpt.com, claude.ai, gemini.google.com):
      capture real requests and compare against the generic web-UI extractor
- [ ] Streaming / WebSocket / multipart upload bodies

## Phase 2 — Dashboard
- [x] React + TypeScript + Vite dashboard (mirrors Lightweight-SIEM)
- [x] Event feed, summary tiles, breakdown by AI service and data type, filters,
      live refresh, per-event rationale
- [ ] Per-device drill-down view and time-range filter/trend chart
- [ ] Auth (this needs to exist before this is ever pointed at real traffic)

## Phase 3 — Deployment
- [ ] Root CA generation + trust distribution story (via Datto RMM, matching
      existing MSP tooling)
- [ ] PAC file / GPO proxy routing config generator
- [ ] Per-provider cert-pinning compatibility check (some mobile AI apps may
      pin — needs verification before claiming full coverage)
- [ ] Disclosure notice template for client AUPs (non-code artifact)

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
