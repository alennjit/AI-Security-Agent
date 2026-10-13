# AI Security Agent

Network-level DLP for AI usage. Detects when confidential data — secrets,
credentials, PII, client-confidential material — is being sent to AI model
prompts (ChatGPT, Claude, Gemini, Copilot, and others), and surfaces it to
admins through a SIEM-style dashboard.

Part of Alen's cybersecurity LLC, sibling project to
[Lightweight-SIEM](https://github.com/alennjit/Lightweight-SIEM).

See `docs/ARCHITECTURE.md` for the technical design and
`docs/PRIVACY_AND_CONSENT.md` for the consent model — read that one before
touching anything user-facing.

## Status

This table is the live source of truth for what's actually built — keep it
updated as work lands, don't let it drift from the code.

| Component | Status |
|---|---|
| AI service domain/endpoint registry | ✅ Working (`proxy/ai_security_agent/domains.py`) |
| DLP content classifiers (secrets, PII, confidential markers) | ✅ Working, tested (`proxy/ai_security_agent/dlp/`) |
| Per-provider prompt extractors (API formats + Gemini, Perplexity, ChatGPT, Claude web UIs) | ✅ Working, tested (`proxy/ai_security_agent/extractors/`); endpoint-aware registry matches host + path so analytics beacons are ignored |
| mitmproxy addon wiring extractors → classifiers → backend | ✅ Validated end to end on live traffic from a local test proxy (OpenAI, Anthropic, Gemini API requests); non-blocking event delivery, gzip + size-limit handling, per-client IP. 6 tests. Browser sessions verified for Gemini and Perplexity; ChatGPT and claude.ai parsers written but unverified; Copilot (WebSocket) unsupported — see `docs/LOCAL_PROXY_TESTING.md`. |
| Backend ingestion API + event store | ✅ Working, tested (`backend/`) |
| Dashboard (SIEM-style admin UI) | ✅ Working (`dashboard/`, React + TypeScript + Vite): summary tiles, breakdown by AI service and data type, filterable event table with per-event rationale, live auto-refresh, light/dark. No login yet. |
| Local proxy test setup | ✅ Documented and repeatable — see `docs/LOCAL_PROXY_TESTING.md` (test CA is never installed system-wide) |
| Fleet deployment tooling (`deploy/`) | 🚧 Built and tested on one machine, **not yet piloted on a real fleet**: name-constrained per-client CA generator, PAC generator, Windows CA install/remove, PAC GPO create/remove, read-only deployment checker, proxy-host config. GPO scripts parse-checked and WhatIf-tested only (no domain available). See `docs/DEPLOYMENT.md` |
| Auth / multi-tenant client separation | ⬜ Not started |

## Quick reference

```bash
# Proxy DLP engine — run tests
cd proxy && pip install -r requirements.txt && pytest tests/ -v

# Backend API — run dev server
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload

# Backend — run tests
cd backend && pytest tests/ -v

# Dashboard — dev server (expects the backend; set VITE_API_BASE_URL if not on :8000)
cd dashboard && npm install && npm run dev

# Run the proxy locally against real AI traffic: docs/LOCAL_PROXY_TESTING.md
# Roll out to a client's fleet (CA, PAC, GPO, rollback): docs/DEPLOYMENT.md

# Deployment tooling tests
cd deploy && pytest tests/ -v
```
