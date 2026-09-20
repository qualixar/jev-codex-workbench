# Start with Qualixar Jev Control

Qualixar Jev Control adds a local selective Policy Mode and 20 bounded Jev workflows
to Codex Desktop and Codex CLI.
It supports OpenRouter Decisions and TypeSafe direct. This is an independent Qualixar
integration, not an official TypeSafe or OpenAI product.

Policy Mode is built to save Codex tokens by resolving narrow routing, ranking, triage,
and evidence decisions before Codex loads more context or explores additional tools. Savings
vary by task; verify them with an on/off benchmark before publishing a percentage.

## Install

Prerequisites: Python 3.11 or newer and the `codex` command available on `PATH`.

```bash
git clone https://github.com/qualixar/jev-codex-workbench.git
python3 jev-codex-workbench/scripts/install.py
```

The installer asks which provider you use and accepts that provider's key through a
hidden prompt. It stores the selection and key outside the repository in owner-only
local files. The key is not printed or passed through Codex chat.

After installation, fully quit and reopen Codex Desktop and start a new task. That
fresh-Desktop tool call is the final host verification step; an existing task does not
prove that the newly installed plugin was loaded. Open `/hooks`, review the Qualixar Jev
hook definitions, and mark them trusted. New or changed plugin hooks are skipped until
that review is complete.

## Verify offline first

Ask the new task:

```text
Use Qualixar Jev Control to check health, list the available workflows,
describe case 08, and run its adversarial fixture. Do not use live Jev.
```

The response should show `global-hybrid`, `policy_mode.mode=assist`, simulated fixture
provenance, and `execution_authorized=false`.

Policy Mode is ON by default in `assist`. It classifies likely bounded decisions locally and
adds a compact instruction without persisting the prompt. To make a matching Jev result
mandatory before Bash or file-edit tools, opt into `enforce`:

```bash
python3 /path/to/jev-codex-workbench/scripts/set_policy_mode.py enforce
```

Restart Codex Desktop after changing modes. Use `off` to disable routing or `assist` to
return to the default.

## Authorize live calls for one workspace

Installing the plugin does not authorize network requests. In a private terminal,
create a time-limited call budget for the exact Git workspace you reviewed:

```bash
python3 /path/to/jev-codex-workbench/scripts/enable_live.py \
  --workspace /absolute/path/to/your/repository --calls 25 --minutes 30
```

The helper displays the selected provider and pinned model before asking you to type
`AUTHORIZE`. The grant becomes invalid if the workspace revision or provider profile
changes. Custom data needs an additional request-bound grant and classification.

## Manual private environment file

If you cannot use the hidden installer, copy `.env.example` to
`~/.config/qualixar-jev-control/.env`. Set the directory to `0700` and the file to
`0600`. Fill only the selected provider's key. A repository-root `.env` is ignored.

## What is implemented

- Seven MCP tools: health, policy status, local policy check, catalog, description,
  fixture execution, and gated live evaluation.
- Twenty decision workflows and 60 nominal, uncertain, and adversarial fixtures.
- Fixed provider endpoints and model pins; no automatic provider fallback.
- Workspace-, revision-, provider-, expiry-, and call-budget-bound live grants.
- Strict response validation, data screening, deterministic policies, and content-addressed receipts.
- A read-only local evidence viewer and optional capture tooling.

Jev output is advice, not authorization. It cannot approve a shell command, file write,
deployment, access decision, or completion claim.

Read [the architecture](docs/GLOBAL_HYBRID_ARCHITECTURE.md), [security policy](SECURITY.md),
and [live validation protocol](docs/LIVE_VALIDATION.md) before using non-synthetic data.
