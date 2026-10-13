# Deployment guide (PAC + GPO + inspection CA)

How to roll the inspection proxy out to a client's Windows fleet. **Nothing in this repo applies
itself to any machine.** The scripts generate artifacts, and the ones that change a machine
support `-WhatIf`, refuse unsafe input, and have a rollback.

Status: the CA generator, PAC generator and tests were exercised end to end on a single machine
(including real mitmproxy-issued certificates). The Windows/GPO scripts were parse-checked and
exercised in `-WhatIf`/refusal modes; the Group Policy cmdlets and the systemd unit have **not**
been run against a real domain or Linux host. Treat them as a reviewed starting point and pilot first.

## Safety model

| Risk | Mitigation |
|---|---|
| Stolen CA key could impersonate any website | **Name-constrained CA**: critical X.509 Name Constraints limit it to the AI-service hostnames. Clients reject certificates it signs for anything else (verified: `example.com`, `www.google.com`, `mail.google.com` are refused). Per client, 2-year validity, path length 0. |
| Proxy outage breaks internet access | PAC returns `PROXY host:port; DIRECT` — **fail open**. |
| Intercepting traffic we can't inspect | PAC routes only hosts whose parser is **verified** (see the coverage table). `--include-unverified` is for pilots only. |
| Everything else being intercepted | PAC sends all other traffic `DIRECT`; the proxy never sees it. |
| Wrong CA pushed to fleet | Installer requires the expected SHA-1 thumbprint, a Name Constraints extension, no private key, a CA cert, and non-expiry. |
| Bad rollout hits everyone | GPO created **unlinked**; linking needs an explicit OU and refuses the domain root. Pilot ring first. |
| Domain-wide trust by accident | Do **not** use `certutil -dspublish` — it publishes trust for the whole forest. |

## Before anything else: disclosure

The consent model is **disclosure through the acceptable-use policy, silent at runtime**
(see `PRIVACY_AND_CONSENT.md`). Employees must be told. Use `templates/AUP_AI_MONITORING_NOTICE.md`
as a starting point and have counsel review it for the client's jurisdictions. Do not deploy to a
client whose policy does not cover this.

## 1. Proxy host

```bash
# per-client CA (run on the proxy host or a secure workstation; keep the key off shared drives)
python deploy/ca/generate_ca.py --client-name "Acme Corp" --out /etc/aisa/conf
```
It prints the **thumbprint** (needed by the installer and the checker) and writes:
`mitmproxy-ca.pem` (private key + cert — stays on the proxy host only), `mitmproxy-ca-cert.pem`,
and `ca-cert.cer` (the only file that goes to clients).

Copy `deploy/proxy-host/config.yaml` into the same folder. **`upstream_cert: false` is required** —
without it, real certificates for Google/Perplexity carry unrelated names and clients reject the
forged certificate. A test guards this.

Run the proxy as a service (`deploy/proxy-host/aisa-proxy.service`, an untested template). Bind it to
the internal interface and firewall the port to client subnets only. Back up the CA key offline
and restrict who can read it — whoever holds it can sign for the permitted AI hostnames.

## 2. PAC file

```bash
python deploy/pac/generate_pac.py --proxy proxy.corp.example:8080 --out build/proxy.pac
```
Host `proxy.pac` on an internal web server over plain HTTP, reachable without authentication
(it only lists hostnames). Regenerate it whenever the service registry changes.

## 3. Pilot ring

1. **Disclose** (above). Pick a pilot OU with a few willing machines.
2. **Trust the CA** on the pilot machines — either
   - RMM (e.g. Datto component): `Install-AisaRootCa.ps1 -CertPath ca-cert.cer -ExpectedThumbprint <thumbprint>` (try `-WhatIf` first), or
   - a GPO: Computer Configuration → Policies → Windows Settings → Security Settings → Public Key Policies → Trusted Root Certification Authorities → import `ca-cert.cer`, linked **only** to the pilot OU.
3. **Create the PAC GPO** (unlinked):
   `New-AisaPacGpo.ps1 -PacUrl http://proxy.corp.example/proxy.pac -WhatIf`, then without `-WhatIf`.
   Review it in GPMC, then link it to the pilot OU (`-Link -TargetOu "OU=AI-Pilot,DC=..."`).
4. **Verify** on a pilot machine after `gpupdate /force`:
   `Test-AisaDeployment.ps1 -PacUrl <url> -ExpectedThumbprint <thumbprint>` — read-only; all checks must pass.
5. **Watch the dashboard** while pilot users use the AI services normally. Check for broken apps.
6. Widen in rings (a department, then the fleet) only after a quiet week.

## Rollback

In this order, so clients never trust nothing while still routed to the proxy:
1. `Remove-AisaPacGpo.ps1 -TargetOu "<each linked OU>"` (unlinks, deletes). Clients stop using the proxy at the next policy refresh.
2. Wait for the refresh (or `gpupdate /force` on pilots).
3. `Remove-AisaRootCa.ps1 -Thumbprint <thumbprint>` via RMM, or remove the trust GPO.

The `AutoConfigURL` value is written as a Group Policy *preference*, so it can linger on a machine
after the GPO is gone. To clear it via RMM:
`Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -ErrorAction SilentlyContinue`

**If the CA key is ever exposed:** run `Remove-AisaRootCa.ps1` fleet-wide, generate a new CA, and
redeploy. The name constraints limit what an attacker could have impersonated in the meantime.

## Known limits

- **QUIC / HTTP3:** browsers can reach some services over UDP/443, which a PAC proxy never sees. Block UDP/443 to the
  monitored hosts at the firewall, or set the Chrome/Edge `QuicAllowed` policy to false.
- **Firefox** uses its own certificate store. Set the `security.enterprise_roots.enabled` policy (or the
  `Certificates > ImportEnterpriseRoots` policy) so it trusts the Windows store.
- **Certificate pinning:** apps that pin certificates will fail through the proxy. Test the AI apps your client uses.
- **Not covered:** mobile devices, unmanaged BYOD, apps that ignore the system proxy, and Microsoft Copilot (WebSocket).
- **Inspection is detect-and-alert only.** The proxy never blocks or edits traffic.
- **CA lifetime:** 2 years. Calendar the rotation; deploy the new CA before the old one expires.
