# Qualixar Jev Control for Codex

Give Codex a selective Jev judgment layer for routing, ranking, triage, evidence checks,
and completion review. Version 1.1.2 adds a clear hook-trust path for Policy Mode: a local control plane that decides
when a bounded Jev judgment could help before Codex expands context or uses governed tools.
Choose OpenRouter or TypeSafe once; every live call still needs an explicit, expiring grant
for the exact workspace and repository revision.

**Jev Policy Mode is built to save Codex tokens.** It moves narrow semantic decisions—such
as which files, tests, tools, skills, or sources deserve deeper attention—ahead of expensive
context expansion and tool exploration. When that early decision removes unnecessary work,
Codex uses less context and can spend its reasoning budget on the selected path. The amount
saved depends on the task, so this release claims the mechanism and provides the controls;
it does not invent a universal percentage.

This is an independent open-source integration from **Qualixar**, created by
**Varun Pratap Bhardwaj**. It works with TypeSafe's Jev service but is not an
official TypeSafe or OpenAI product.

## Install for Codex Desktop or Codex CLI

Prerequisites: Python 3.11 or newer and the `codex` command available on `PATH`.

```bash
git clone https://github.com/qualixar/jev-codex-workbench.git
python3 jev-codex-workbench/scripts/install.py
```

The installer uses Codex's native marketplace commands, asks whether you use
OpenRouter or TypeSafe, and accepts the selected API key through a hidden terminal
prompt. It never prints the key or puts it in the repository. Then fully quit and
reopen the Codex Desktop app and start a new task. OpenAI documents the same local
plugin configuration for Codex Desktop and Codex CLI; native Desktop verification is
the post-install step for this release. The hook review is a one-time CLI action because
Codex Desktop currently does not expose `/hooks`. In a private terminal, run `codex`, choose
**Review hooks**, and trust only the three `qualixar-jev-control@qualixar-jev` entries:
`UserPromptSubmit`, `PreToolUse`, and `PostToolUse`. Quit the CLI, then restart Codex Desktop.
Codex deliberately skips new or changed plugin hooks until that review is complete. See
[Hook trust](docs/TRUSTING_HOOKS.md).

## Policy Mode

Policy Mode runs a deterministic classifier locally on each submitted task. It makes no
provider request and stores no prompt text. It returns one of four outcomes:

| Outcome | Meaning |
|---|---|
| `SKIP` | Continue with Codex; no bounded Jev judgment was identified. |
| `SUGGEST` | A supplied Jev workflow may reduce unnecessary exploration. |
| `REQUIRE` | In opt-in enforce mode, governed write or shell tools wait for the matching Jev evaluation. |
| `BLOCK` | Sensitive material was detected locally and must not be sent to Jev. |

Policy Mode is **ON by default**. The installer selects `assist`, so every submitted task
gets local policy classification without making every task a Jev API call. Change the mode
from a private terminal:

```bash
python3 jev-codex-workbench/scripts/set_policy_mode.py off
python3 jev-codex-workbench/scripts/set_policy_mode.py assist
python3 jev-codex-workbench/scripts/set_policy_mode.py enforce
```

`enforce` governs Bash and file-edit calls only when a known bounded semantic decision is
matched. It does not send every turn to Jev. A successful Jev response satisfies the turn
gate, but the response still cannot authorize execution. See [Policy Mode](docs/POLICY_MODE.md)
and [Hook trust](docs/TRUSTING_HOOKS.md).

Six tools work without a key or live request:

- `jev_health` reports the local runtime scope and safety state.
- `jev_policy_status` reports the configured mode and control boundaries.
- `jev_policy_check` runs the local no-network classifier on one task intent.
- `jev_catalog` lists the 20 supplied decision workflows.
- `jev_describe` explains one workflow's contract and limits.
- `jev_run_fixture` runs a clearly labelled synthetic example.

A fifth tool, `jev_evaluate`, calls the selected live provider only when a matching human-created
  workspace grant exists.

Installing the plugin does not itself authorize network calls. The provider cannot be
selected through an MCP argument, and the adapter accepts only two fixed destinations:
TypeSafe System One or OpenRouter's alpha-namespaced Decisions endpoint. There is no
automatic fallback between providers because that would silently change billing and
the external processor receiving the reviewed input.

| Provider | Credential | Release pin | Official reference |
|---|---|---|---|
| OpenRouter Decisions | `OPENROUTER_API_KEY` | `typesafe/jev-1.13` | [OpenRouter Jev 1.13](https://openrouter.ai/typesafe/jev-1.13) |
| TypeSafe direct | `TYPESAFE_API_KEY` | `jev-1.13.0` | [TypeSafe quick start](https://docs.typesafe.ai/introduction/quickstart) |

### Why this is not an `npx` installer

Codex already has a native plugin and marketplace mechanism. Adding an `npx`
wrapper would require Node.js, add another package-distribution trust boundary,
and still call the same two Codex commands. The native installation is shorter,
easier to audit, and works with the Codex Desktop app. An npm wrapper may be added
later only if a verified platform gap justifies it.

## What it does

Jev is used here as a narrow decision component, not as a replacement coding
agent. Codex gathers the evidence and proposes candidates. Jev can judge a bounded
question. Deterministic policy and the human operator retain authority over any
real action.

| # | Workflow | Practical use |
|---:|---|---|
| 01 | Skill routing | Choose the smallest relevant agent skill. |
| 02 | Task routing | Send work to the appropriate bounded workflow. |
| 03 | Tool selection | Select among reviewed tools for one task. |
| 04 | File ranking | Rank likely-relevant files before deeper reading. |
| 05 | Context sieve | Keep useful context and reject irrelevant or unsafe input. |
| 06 | Injection triage | Route suspicious instructions for review or blocking. |
| 07 | Claim verification | Compare a claim with supplied evidence. |
| 08 | Completion gate | Check whether stated acceptance evidence is present. |
| 09 | Patch review | Prioritize patch risks for human review. |
| 10 | Semantic lint | Detect meaning-level contradictions missed by syntax checks. |
| 11 | Failure classification | Classify an observed failure for recovery routing. |
| 12 | Worker routing | Select a suitable worker profile for bounded work. |
| 13 | Issue triage | Route incoming issues by evidence and impact. |
| 14 | Incident triage | Prioritize incident reports without taking action. |
| 15 | Test selection | Rank tests that best cover a stated change. |
| 16 | Documentation drift | Compare documentation claims with current evidence. |
| 17 | Security-review routing | Route findings to the appropriate review path. |
| 18 | Support triage | Classify support requests without sending responses. |
| 19 | Research ranking | Rank reviewed sources against a research question. |
| 20 | Memory admission | Decide whether a candidate fact belongs in durable memory. |

Each workflow ships with nominal, uncertain, and adversarial fixtures: 20 cases,
60 deterministic fixture contracts. Fixture output proves the local branching and
contract behavior only. It is not a live Jev response, an accuracy benchmark, or
evidence of production adoption.

## Try the offline path after installation

In a fresh Codex task, ask:

```text
Use Qualixar Jev Control to list the available bounded judgment workflows,
describe completion gate, and run its adversarial fixture. Do not use live Jev.
```

The result should identify the `global-hybrid` scope, keep
`execution_authorized=false`, and label fixture provenance as simulated.

## Authorize live use in one workspace

The key is global to your local user account, but authority is not. Run the grant helper
from a private terminal for each workspace you choose to use:

```bash
python3 /path/to/jev-codex-workbench/scripts/enable_live.py \
  --workspace /absolute/path/to/your/repository --calls 25 --minutes 30
```

The helper shows the selected provider and pinned model, asks the operator to type
`AUTHORIZE`, and creates an expiring grant bound to that workspace, its current Git
revision, and the provider profile. Agents must not create, extend, or bypass that
grant. Custom data also requires exact request authorization and classification. See
[live validation](docs/LIVE_VALIDATION.md) and [security controls](SECURITY.md).

## Verification

The release checklist requires the package-integrity check, the Python test suite, all
60 fixture contracts, plugin validation, a clean-checkout install, secret/path scans,
and an installed-plugin smoke test outside the source workspace.

Run the local checks with:

```bash
python3 scripts/verify_package.py
python3 scripts/bootstrap.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python jev.py suite
```

The read-only evidence viewer is available locally with:

```bash
.venv/bin/python jev.py serve
```

Open `http://127.0.0.1:8765`. The viewer reads screened synthetic receipts; it
cannot spend API calls or read credentials.

## Architecture and trust boundary

```text
Codex Desktop / CLI
        |
        `-- global Qualixar plugin
               |-- offline: health, catalog, describe, fixtures
               `-- live: provider profile -> workspace/revision grant
                         -> classification -> Jev API
                         -> validation -> local receipt -> policy
```

Jev output is untrusted advice. It cannot authorize shell commands, file writes,
deployments, access decisions, or completion. Native Codex permissions and the
operator's existing controls remain in force.

Policy Mode can save Codex tokens when its bounded decision prevents unnecessary context
expansion or tool exploration. It can also improve decision discipline by separating a
narrow semantic judgment from Codex's broader reasoning and execution work. This repository
does not claim a universal percentage or guaranteed quality gain. Those stronger claims
require controlled on/off measurements using Codex-side usage and task acceptance results,
not TypeSafe usage fields alone.

## Repository map

| Path | Purpose |
|---|---|
| `plugins/qualixar-jev-control/` | Installable global Codex plugin with gated live access. |
| `.agents/plugins/marketplace.json` | Codex marketplace entry. |
| `.agents/skills/jev-control/` | Project-live operating skill. |
| `jevkit/`, `jev.py` | Adapter, contracts, policies, receipts, MCP and CLI. |
| `use_cases/`, `fixtures/` | 20 workflow specifications and 60 fixtures. |
| `tests/` | Unit, integration, isolation, and plugin-runtime checks. |
| `docs/use_cases/` | Per-case purpose, acceptance, and capture guidance. |

Python 3.11 or newer is required. macOS and Linux are supported targets. Native
Windows behavior has not been verified. [`.env.example`](.env.example) documents both
supported variables as an alternative manual configuration path. It is owner-only but
plaintext. A populated copy is read
only from `~/.config/qualixar-jev-control/.env`, with a `0700` directory and `0600`
file; the repository's own `.env` is deliberately not loaded.

## Industry use

The workflows can be adapted to software engineering, security operations,
financial-services review, insurance triage, legal-document review, customer
support, e-commerce, research, knowledge systems, RAG, DevOps, and agent
platforms. These are adaptation paths, not claims of regulatory approval or
production accuracy. Start with synthetic data and keep consequential decisions
under qualified human review. See [the industry mapping](docs/INDUSTRY_MAPPING.md).

## Project documents

- [Start here](START_HERE.md)
- [Architecture](docs/GLOBAL_HYBRID_ARCHITECTURE.md)
- [Security](SECURITY.md)
- [Publishing and evidence rules](docs/PUBLISHING_GATES.md)
- [Contributing](CONTRIBUTING.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

## Licence

MIT. Copyright © 2026 Varun Pratap Bhardwaj / Qualixar.

TypeSafe, Jev, OpenAI, Codex, and other third-party names and trademarks belong
to their respective owners. This repository does not redistribute model weights
or TypeSafe's official skill.
