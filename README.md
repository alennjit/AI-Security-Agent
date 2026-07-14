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
| Per-provider prompt extractors (OpenAI/Anthropic/Google/generic web UI) | ✅ Working, tested (`proxy/ai_security_agent/extractors/`) |
| mitmproxy addon wiring extractors → classifiers → backend | 🚧 Written, not yet run against live traffic |
| Backend ingestion API + event store | ✅ Working, tested (`backend/`) |
| Dashboard (SIEM-style admin UI) | ⬜ Not started |
| TLS-inspecting proxy deployment (root CA, PAC/GPO) | ⬜ Not started — design only |
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
```
