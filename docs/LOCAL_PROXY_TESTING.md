# Local proxy testing

How to run the inspection proxy on one machine and watch it catch (fake) secrets
in AI prompts. Nothing here touches other devices or the system trust store.

## Safety rules

- The mitmproxy CA you generate lets whoever holds its private key impersonate
  any website to anything that trusts it. **Do not install it system-wide.** Keep
  it in a throwaway `confdir`, and trust it only for the specific client under
  test (`curl --cacert`, or a dedicated browser profile).
- Use **fake** secrets in test prompts (for example the AWS documentation key
  `AKIAIOSFODNN7EXAMPLE`). Test prompts sent to real AI services leave your machine.
- Bind the proxy to `127.0.0.1` unless you deliberately want other devices to use it.
- Fleet deployment (distributing a root CA, PAC/GPO routing) is a separate,
  higher-risk step and is **not** covered here.

## Run it

```bash
# 1. Backend (any free port; here 8010) — database kept outside the repo
cd backend
DATABASE_URL="sqlite:///E:/aisa-dev/events.db" \
AISA_CORS_ORIGINS="http://localhost:5173" \
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010

# 2. Proxy with the add-on (proxy/ must be on PYTHONPATH)
cd proxy
AISA_BACKEND_EVENTS_URL="http://127.0.0.1:8010/events" PYTHONPATH="$(pwd)" \
mitmdump --listen-host 127.0.0.1 --listen-port 8081 \
         --set confdir=E:/aisa-dev/mitm-conf -s ai_security_agent/addon.py

# 3. Dashboard
cd dashboard
VITE_API_BASE_URL=http://localhost:8010 npm run dev
```

The first start generates the CA in `confdir` (`mitmproxy-ca-cert.pem`).

## Send a test prompt

```bash
curl --proxy http://127.0.0.1:8081 --cacert E:/aisa-dev/mitm-conf/mitmproxy-ca-cert.pem \
     --ssl-no-revoke \
     https://api.anthropic.com/v1/messages \
     -H 'x-api-key: fake' -H 'anthropic-version: 2023-06-01' -H 'content-type: application/json' \
     -d '{"model":"claude-haiku-4-5-20251001","max_tokens":5,
          "messages":[{"role":"user","content":"debug: aws_key=AKIAIOSFODNN7EXAMPLE"}]}'
```

The upstream API answers 401 (the key is fake) — that's expected. The proxy
still sees the request body, the add-on flags the AWS key, and an event appears
in the dashboard with the secret redacted.

To simulate multiple devices, add `--interface 127.0.0.2` (or `.3`, `.4`) to curl.

## Gotchas

- **`--ssl-no-revoke` on Windows**: curl's Schannel backend runs a certificate
  revocation check that a local test CA cannot pass.
- **Port clashes**: if a port is taken, pick another rather than killing the
  process, and allow the dashboard's origin with `AISA_CORS_ORIGINS`.
- **Certificate pinning**: apps that pin certificates will refuse a proxied
  connection. Browsers and API clients that use the system or a supplied CA do not.
- **Streaming and very large bodies**: bodies over `AISA_MAX_BODY_BYTES` (2 MB) are skipped.

## What has been validated

OpenAI chat completions, Anthropic Messages and Gemini `generateContent` API
requests: flagged prompts produce redacted events; clean prompts and unrelated
hosts produce none. Browser web-UI traffic (chatgpt.com, claude.ai, gemini.google.com)
still needs capture-and-compare against the generic web-UI extractor.
