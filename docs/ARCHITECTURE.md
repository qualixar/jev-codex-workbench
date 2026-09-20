# Architecture and boundaries

## Implemented path

Codex calls the project-local stdio MCP process. Five fixed tools route to a catalog,
a specification reader, the fixture engine or the live adapter. The adapter validates
text input and a reviewed question set, screens for common secrets, reserves a call
from a shared expiring local grant, sends a fixed-origin HTTPS request, validates the
answer contract, evaluates policy and writes an evidence receipt.

The viewer reads only screened synthetic receipts. Capture replays a stored receipt
in a clean browser context. It does not make a new model call, record another app,
or turn a fixture into measured inference. The exporter excludes custom-source data.

The core HTTP client is deliberately small and standard-library-only. The MCP server
implements the narrow stdio tool subset needed here, rather than claiming support for
every MCP feature. It requires an actual Codex-host compatibility check on the user's
machine. No official TypeSafe SDK or community MCP is bundled.

## MCP surface

| Tool | Behavior | Live grant needed |
|---|---|---|
| `jev_health` | Safe readiness and grant status | No |
| `jev_catalog` | List 20 known use cases | No |
| `jev_describe` | Read one reviewed specification | No |
| `jev_run_fixture` | Run a labeled stock fixture | No |
| `jev_evaluate` | Evaluate one known case with Jev | Yes; extra approval for custom state |

The generic `jev_evaluate` interface accepts only a catalog case ID plus optionally
approved state. It does not accept arbitrary questions, endpoint URLs, shell commands,
credentials, or tools to execute. The use-case templates are code-reviewed files.

## Policy and uncertainty

Choice routes need both a minimum winning probability and minimum reported confidence.
Score uses its probability-weighted value, not an assumed integer class. Noul has a
probability of yes, not a separate confidence field. The default thresholds are
**illustrative and uncalibrated**. Uncertain evidence is retained for review. A failed
completion receipt blocks completion regardless of a favorable semantic answer.

`CHECKS_PASSED` means the configured checks passed on supplied evidence; it is not a
proof of correctness. `RECOMMEND` is advice, not authorization. Evidence receipts bind
hashes and local observations but are not signed, tamper-proof execution attestations.
A hostile process with the same OS identity can change files and must be addressed by
a stronger isolation/trust architecture before production use.

## Trust boundary and data egress

Local: code, policy, fixture data, credentials, grants, receipts and viewer.
Remote: **the selected provider—OpenRouter or TypeSafe direct—receives live state and
questions.** Hosted Jev is not local inference. There is no automatic provider fallback.
The existing Codex provider may separately process its agent context according to the
user's Codex setup. An MCP wrapper does not change that provider's data handling.
Do not send enterprise code, customer data or personal material without authority.

## Existing bounded-loops and memory systems

Keep bounded-loops as the scheduler. A future inspected adapter may call `jev_evaluate`
at an existing node boundary and map REVIEW/BLOCK/RECOMMEND into established transitions.
Do not invent its API or install a second scheduler. Persist only approved durable
knowledge through the existing SuperLocalMemory admission path; use Mesh only for its
existing ephemeral coordination role. Case 20 recommends admission but performs no
memory write. These integration points are **design guidance, not shipped connectors**.

Six diagrams in `docs/architecture/` distinguish implemented paths from optional future
adapters. Mermaid sources are editable; no remote diagram-render service is required.
