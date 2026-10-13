# CLAUDE.md — AI Security Agent

Repo-specific context for Claude Code. This extends (does not replace) the
global `C:\Users\alenf\CLAUDE.md` conventions — type hints, docstrings,
`pathlib`/`logging`, `subprocess.run(shell=False)`, env-var secrets, pytest
with mocked external calls, no unmarked stubs.

## What this is

A network-level DLP product that detects when confidential data (secrets,
PII, client-confidential material) is being pasted into AI model prompts —
ChatGPT, Claude.ai, Gemini, Copilot, etc. — and surfaces it to admins via a
SIEM-style dashboard. Part of Alen's solo cybersecurity LLC, sibling project
to [Lightweight-SIEM](https://github.com/alennjit/Lightweight-SIEM).

**Locked decisions (2026-07-13):**
- Interception layer: **network/DNS + TLS-inspecting forward proxy**, not a
  browser extension or full endpoint agent. Rationale: catches API usage and
  non-browser apps, not just browser chat UIs, and mirrors the SSL-inspection
  pattern already used with FortiGate at Alen's MSP job — this could
  eventually integrate with existing client firewalls (ICAP) rather than
  requiring a standalone appliance per client.
- Consent model: **disclosed via AUP/employee handbook, silent UI at runtime**
  — no popups, no in-the-moment interruption. This is the model most
  commercial DLP/EDR agents use and is the most legally defensible without
  being disruptive. See `docs/PRIVACY_AND_CONSENT.md` — read this before
  changing anything about how/whether the agent notifies end users.
- Repo visibility: public (matches Game-Trainer, Lightweight-SIEM).
- DLP findings must **redact matched secret/PII values before they are
  logged, stored, or sent to the backend** — the tool that detects secrets
  must not become a new secret store. Store type + position + a truncated/
  hashed snippet only, never the raw match. This is a hard rule, not a
  nice-to-have — see `proxy/ai_security_agent/dlp/classifiers.py`.

## Stack

- **proxy/** — Python 3.11+, `mitmproxy` addon. Intercepts TLS-inspected
  traffic to known AI service domains (see `domains.py`), extracts the
  prompt text per-provider (`extractors/`), runs it through the DLP
  classifiers, POSTs findings to the backend.
- **backend/** — Python 3.11+, FastAPI + SQLAlchemy + SQLite (dev) /
  Postgres (prod, later). Ingests events, exposes them for the dashboard.
- **dashboard/** — React + TypeScript + Vite, same stack and color tokens as
  Lightweight-SIEM. Working (event feed, breakdowns, filters, live refresh); no
  auth yet — see `docs/ROADMAP.md`. Its `node_modules` may be a junction to
  `E:\aisa-dev\dashboard\node_modules` on Alen's machine (C: space); a fresh
  `npm install` replaces the junction with a real folder.
- **deploy/** — root CA generation + distribution notes, proxy PAC/GPO
  config. This is where client deployment (via Datto RMM, matching Alen's
  existing MSP tooling) will live. Not yet built.

## File structure

```
AI-Security-Agent/
├── CLAUDE.md
├── README.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── PRIVACY_AND_CONSENT.md
│   └── ROADMAP.md
├── proxy/
│   ├── ai_security_agent/
│   │   ├── domains.py        ← registry of known AI service domains/endpoints
│   │   ├── addon.py          ← mitmproxy addon entry point
│   │   ├── extractors/       ← per-provider request-body → prompt-text parsers
│   │   └── dlp/
│   │       ├── rules.py      ← pattern/keyword definitions, weights
│   │       └── classifiers.py← scan(text) -> ClassificationResult, redacted
│   └── tests/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py         ← Event/Finding SQLAlchemy models
│   │   ├── db.py
│   │   └── api/events.py     ← POST/GET /events
│   └── tests/
└── dashboard/                 ← React/TS/Vite admin UI (working, no auth yet)
```

## What NOT to do

- Do not store, log, or print raw secret/PII matches — redact at the point
  of detection, before the value leaves the classifier function.
- Do not build TLS interception, root-CA distribution, or any client
  deployment tooling without flagging it first — that's the part with real
  legal/operational blast radius (a bad root CA push breaks every client
  machine's TLS trust). Design docs and local dev/testing are fine to build
  freely.
- Do not add per-action user notifications/popups to the proxy or agent —
  the consent model is disclosure-at-policy-level, not runtime interruption.
  If this changes, it's Alen's call, not a default to drift into.
- Do not hardcode client-identifying data (company names, real employee
  info) anywhere in this repo — it's public.
