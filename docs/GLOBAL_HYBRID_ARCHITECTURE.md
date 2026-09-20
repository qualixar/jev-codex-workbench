# Global-hybrid Jev architecture

## Decision

Qualixar Jev Control is one global Codex plugin with two deliberately different
paths. Offline catalog and fixture tools work everywhere. Live `jev_evaluate` is
available everywhere but cannot make a request until the human has selected one
fixed provider profile and created an expiring grant for the exact workspace and
reviewed Git revision.

Supported profiles are immutable in code:

| Profile | Credential | Endpoint | Pinned model |
|---|---|---|---|
| OpenRouter | `OPENROUTER_API_KEY` | OpenRouter Decisions | `typesafe/jev-1.13` |
| TypeSafe direct | `TYPESAFE_API_KEY` | TypeSafe System One | `jev-1.13.0` |

The OpenRouter endpoint is alpha-namespaced. It is contract-tested separately and
does not automatically replace or fall back to TypeSafe direct. Provider choice is
private local configuration; MCP callers cannot submit a URL, model, key, or provider.

## Why this shape

| Alternative | Benefit | Failure mode | Decision |
|---|---|---|---|
| Offline-only global plugin | Smallest network risk | Most users never reach the real Jev value | Rejected as the complete product |
| Unrestricted global live key | Lowest friction | Any workspace could transmit data without a reviewed boundary | Rejected |
| Global dual-provider plugin plus workspace grants | One installation, real Jev, explicit data and billing boundary | Requires a human grant per reviewed workspace/revision | Adopted |
| Hosted Qualixar MCP with OAuth | Best future onboarding | Qualixar would operate infrastructure and become part of the secret/data path | Deferred |

## Trust boundary

```text
Private provider setup
        |
        |  provider ID + owner-only credential file, never chat
        v
Global Codex plugin
        |
        |  offline tools require no grant
        |  live tool requires absolute workspace path
        v
Canonical workspace ID + Git revision
        |
        |  human-created call budget bound to provider profile
        v
Reviewed/minimized state and typed questions
        |
        v
OpenRouter Decisions OR TypeSafe System One
        |
        |  untrusted structured answer
        v
Schema validation -> deterministic policy -> content-addressed receipt
```

Jev never authorizes shell execution, file modification, deployment, identity or
access changes, publication, or an exception to project policy. A successful MCP
response is not proof that an action is correct.

## Authority binding

A live grant is bound to:

- the canonical workspace identity;
- Git `HEAD`, index, and working-tree fingerprint;
- the fixed provider ID and complete provider-profile hash;
- expiry time and remaining HTTP attempts; and
- for custom data, the case, classification, request ID, and request hash.

Changing the repository, provider, endpoint profile, model pin, or exact custom
request invalidates the grant. Retries consume attempts. There is no automatic
provider fallback.

## Data classes

| Class | Transmission policy |
|---|---|
| Public | May be sent when necessary and minimized. |
| Internal-minimized | Requires exact request authorization and content review. |
| Restricted | Keep local; derive a safe representation or abstain. |
| Prohibited | Never send or reproduce. Includes credentials, authentication headers, private keys, and unredacted regulated or personal data. |

## Evidence

Receipts are content-addressed and contain the provider ID, provider-profile hash,
requested and resolved model IDs, workspace identity, revision, input classification,
grant ID, request/rubric/policy hashes, origin, transport attempts, usage, and policy
outcome. Credentials and authorization headers are never stored.

Fixture receipts and live receipts are not interchangeable. Fixture runs prove local
application contracts. Live runs prove only what the recorded provider returned for
that request; they do not establish domain accuracy or production approval.

## Package boundary

The plugin runtime is produced by `scripts/package_plugin_runtime.py` from an explicit
source allowlist. `RUNTIME_MANIFEST.json` hashes every bundled file. The launcher pins
`--scope global-hybrid` and Python 3.11 or newer. The plugin reads credentials only
when health checks the selected profile or a live evaluation is attempted; values are
never returned.

## Release gates

| Gate | Evidence required |
|---|---|
| Provider contracts | Mocked HTTP tests prove exact endpoint, header, model, response validation, retry, and suppressed error bodies for both profiles. |
| Workspace isolation | Cross-workspace, stale-revision, provider-switch, and request-mismatch grants fail closed. |
| Fixture coverage | All 20 workflows and all 60 fixture contracts pass. |
| Installed plugin | Clean install and MCP smoke succeed outside the source workspace. |
| Security | Secret, private-path, dangerous-file, dependency, and permission scans pass. |
| Public package | A clean export contains one initial public commit and no internal Git history. |
| Live proof | Each claimed provider receives a separate human-authorized smoke; unavailable credentials are reported, never simulated. |
