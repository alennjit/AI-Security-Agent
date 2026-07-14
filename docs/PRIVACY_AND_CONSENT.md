# Privacy and Consent Model

Read this before changing anything about how the agent notifies, logs, or
withholds information from monitored users. This is a locked decision, not
a default — changing it is Alen's call, made deliberately, not something to
drift into while implementing a feature.

## The model: disclosed policy, silent runtime UI

- The **organization** deploying this tool discloses AI-usage monitoring to
  its employees — in the AUP/employee handbook, at onboarding, or via
  whatever mechanism the client's HR/legal process already uses for
  browsing/email monitoring disclosure. This repo does not generate that
  disclosure language; that's a legal/HR artifact, not code.
- The **agent itself** does not interrupt the user. No popups, no "your
  message was flagged" banners, no visible behavior change. This matches
  how EDR/DLP tools already run in Alen's MSP environment (CrowdStrike,
  ThreatLocker) — monitored, but not intrusive.

## Why this and not full covert monitoring

Fully covert monitoring — no disclosure anywhere, ever — crosses into
wiretapping/interception-of-communications statute territory in a lot of
US states (two-party/all-party consent states) and is a GDPR problem in the
EU regardless of state. "The org discloses it exists, the UI just doesn't
nag about it" is the model basically every commercial DLP/EDR/CASB product
uses, and it's the one that survives a "did the employee have notice"
question in an employment dispute. This is not legal advice — before this
is deployed against a real client's real employees, a lawyer should review
the specific disclosure language and applicable state/country law. This
doc records the *engineering* default; it doesn't substitute for that
review.

## What this means for the code

- No client-facing notification code should be added to the proxy addon or
  any future endpoint component without an explicit decision to do so.
- Findings/events stored by the backend must never include the raw
  secret/PII value that triggered the finding (see CLAUDE.md, ARCHITECTURE.md)
  — this protects the *monitored user*, not just the org, since a breach of
  the DLP tool's own database shouldn't itself become a secrets leak.
- Per-client deployment (`deploy/`) should eventually include a template
  disclosure notice as a reference artifact for the MSP/LLC side of the
  business, even though it's not something the software itself enforces.
