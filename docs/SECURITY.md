# Security and privacy controls

## Credentials

The user selects exactly one provider. OpenRouter uses `OPENROUTER_API_KEY`; TypeSafe
direct uses `TYPESAFE_API_KEY`. The adapter reads only the selected variable or an
owner-readable provider-specific key file created by the private helper outside the
repository. A GUI application may not inherit a terminal's shell environment. The
optional file avoids relying on that inheritance but is **plaintext**, not macOS
Keychain. Prefer an organization-approved credential mechanism in managed environments.
Never dump environment variables to investigate credential loading.

The prompt and tools do not need to see the key. However, a general coding agent or
malicious process running as the same OS user may still have filesystem access.
Instructions and chmod are not a security boundary against that adversary. Stronger
isolation, a credential broker, and constrained outbound policy are production work.

## Outbound behavior

HTTPS goes only to the fixed endpoint for the selected profile: TypeSafe System One or
OpenRouter's alpha-namespaced Decisions endpoint. Arbitrary base URLs and per-request
provider selection are rejected. Redirects and environment proxy settings are not
automatically followed. A corporate network
requiring an approved proxy may therefore fail closed; do not bypass that network's
controls. Request byte/question/candidate limits bound payload size. Bytes are not
an exact token estimate. Retries consume the same shared HTTP-attempt grant. Ambiguous
timeouts are not automatically retried, because the service may already have processed
the call. HTTP error bodies are not echoed into logs or the MCP context.

## Local grant

The private interactive helper grants a fixed number of HTTP attempts for a limited
time. CLI and MCP share the SQLite counter. It is not a monetary cap, provider billing
limit, hostile-user sandbox, or account-wide quota. Any process with the same OS user
can potentially alter local files. Do not use this proof-of-concept grant for adversarial
multi-tenant access control. The user can revoke with:

```bash
.venv/bin/python scripts/enable_live.py --workspace "$PWD" --revoke
```

## Data screening and media

Common credential formats, credential-key fields, emails, private IPs/URLs, some home
paths and phone-like values are screened. This is a best-effort pattern check, not an
enterprise DLP engine. It cannot reliably identify names, confidential business facts,
all secret formats, or sensitive pixels. Review before transmission; do not rely on
post-hoc redaction. A false positive should be investigated, not globally disabled.

The viewer serves only allowlisted resources on loopback, rejects unexpected Host and
Origin headers, has no write API, and never exposes custom-source receipts. Loopback
is not authentication against local applications or other processes under the same user.
Do not publish the server, bind it to all interfaces, or tunnel it publicly.

Review screenshots and **every recorded frame** before release. Stop recording before
credential entry; hide account panels, notifications, client names, paths and tabs.
Native Codex recording is deliberately manual. AI redaction cannot certify a video safe.
