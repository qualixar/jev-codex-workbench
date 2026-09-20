# Live verification protocol

## 1. Stock synthetic smoke

After offline tests and actual Codex MCP discovery pass, the human selects OpenRouter
or TypeSafe and enters that key in private Terminal. The human then grants 25 attempts
for 30 minutes. Check `jev.py health`; verify the provider ID and credential boolean,
never inspect the secret. Call case 01 once through **Codex's `jev_evaluate` tool** to
prove the actual host → MCP → selected-provider path. If the host is unavailable, the
CLI smoke is useful but must be reported as CLI-only rather than host integration.

```bash
.venv/bin/python jev.py run 01-skill-routing --mode live --scope project-live --workspace "$PWD"
.venv/bin/python jev.py suite --mode live --variant nominal --scope project-live --workspace "$PWD"
```

Do not run both CLI and MCP smokes unnecessarily. The smoke plus suite needs 21 calls
without retries. Inspect actual model, answer shape, usage, transport attempts and
policy result. A REVIEW/BLOCK answer can be a valid live result. Stop on authentication,
contract, quota, or transport errors rather than swapping in fixture output.

Run a separate smoke and grant for each provider that the release claims as live-tested.
Never infer OpenRouter behavior from a TypeSafe-direct result or automatically fall back
between providers. OpenRouter's Decisions endpoint is alpha-namespaced, so preserve its
exact request and resolved model IDs in the receipt.

## 2. Boundary coverage

All 60 offline fixtures cover application branching, not model quality. To test all
60 scenarios against Jev, request a fresh grant (for example 70 attempts and 60 minutes)
and run `jev.py suite --mode live --variant all --scope project-live --workspace "$PWD"`. Never imply that Jev was forced to
be uncertain simply because the scenario file is named `uncertain`: in live mode the
model supplies its own probabilities. The fixture's simulated uncertainty is local only.

## 3. Real code demonstration

Run `scripts/collect_demo.py` before and after Codex fixes the isolated cache bug.
The original result must show one failure among four tests. Preserve the tests. Review
the minimal implementation diff. The collector writes `.local/demo-state.json`.

For a live semantic review of that source-bound state, the human must approve:

```bash
.venv/bin/python scripts/collect_demo.py
.venv/bin/python scripts/enable_live.py --workspace "$PWD" --calls 5 --minutes 10 \
  --allow-custom --case-id 08-completion-gate --state .local/demo-state.json \
  --request-id cache-demo-review --data-classification internal-minimized
.venv/bin/python jev.py run 08-completion-gate --mode live \
  --scope project-live --workspace "$PWD" --state .local/demo-state.json \
  --request-id cache-demo-review --data-classification internal-minimized
```

The custom-data grant is not authority to send unrelated private repositories. The
collector's age field is a local observation, not a continuously refreshing timestamp;
**recollect immediately before evaluation**. The conservative viewer/export deliberately
hide all custom-source runs, even this harmless demo. Record the sanitized native
Codex/Terminal demonstration manually instead of weakening that default.

## 4. Evaluation before production claims

Create a separately labeled human-reviewed dataset representative of the actual target
workflow, with a holdout set. Compare errors, false acceptance, false escalation and
abstention. Lock rubric/model/thresholds before final evaluation. Investigate disagreements
and avoid treating fixture labels as empirical truth. Only then consider private pilot
routing in an inspected external harness. No accuracy or cost-savings conclusion is
encoded in this package, and latency in a receipt is client-observed wall time, not a
provider-wide benchmark.
