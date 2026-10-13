# Dashboard

Admin console for AI Security Agent. React + TypeScript + Vite.

```bash
npm install
VITE_API_BASE_URL=http://localhost:8000 npm run dev   # default API base is :8000
npm run build                                          # type-check + production build
```

The backend must allow this origin: set `AISA_CORS_ORIGINS` on the backend if the
dev server isn't on `localhost:5173`.

## What it shows

- Summary tiles: flagged prompts, critical (8–10), elevated (5–7), distinct devices.
- Breakdown by AI service and by data type.
- Event table with risk badge, service, client, data types and findings; filters
  for risk level, AI service and host/client search; a "Why?" row reveals the
  engine's rationale. Auto-refreshes every 10 s.

## Security notes

- Events contain no prompt text and no raw matched values — only a summary,
  categories and counts. Everything is still rendered as plain text, never HTML.
- There is no authentication yet. Do not expose the backend or this UI beyond
  localhost until auth exists.
- Severity is conveyed by icon and label as well as color.
