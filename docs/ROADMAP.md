# Roadmap

## Phase 1 — DLP engine (current)
- [x] AI service domain/endpoint registry
- [x] DLP classifiers: credentials, PII, confidential keywords, 1-10 risk
      scoring, redaction-by-design
- [x] Per-provider prompt extractors (OpenAI, Anthropic, Google, generic
      web-UI JSON)
- [x] Backend ingestion API (FastAPI) + event store (SQLite)
- [ ] mitmproxy addon validated against real captured traffic samples for
      each provider (currently only unit-tested against synthetic payloads)

## Phase 2 — Dashboard
- [ ] Scaffold React + TypeScript + Vite dashboard (mirror Lightweight-SIEM)
- [ ] Event feed, risk-scored alert list, per-user/per-device drill-down
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
