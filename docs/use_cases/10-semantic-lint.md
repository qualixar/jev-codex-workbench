# 10-semantic-lint — Check repository conventions

**Industry context:** Software engineering. **Category:** Verification.

## What this demonstrates

Check qualitative conventions against explicit rules, alongside rather than instead of existing linters.

This is a runnable decision workflow, not a production integration. It changes no
external system. Codex must use its normal permissions and deterministic tools for
actual actions. Model judgments remain advisory.

## Reviewed contract

Required top-level state fields: `rules`, `change`.
The executable source of truth is `use_cases/10-semantic-lint.json`.
Read the nominal fixture's `state` for its complete shape; never send `mock_values`
to the provider. Question meaning belongs in instructions, not just IDs.
Policy kind: `route`. Default thresholds are demonstration settings,
not evidence of calibration or suitability for a high-stakes workflow.

## Run without spending API calls

```bash
.venv/bin/python jev.py describe 10-semantic-lint
.venv/bin/python jev.py run 10-semantic-lint
.venv/bin/python jev.py run 10-semantic-lint --variant adversarial
.venv/bin/python jev.py run 10-semantic-lint --variant uncertain
```

| Scenario | Expected local status | Interpretation |
|---|---|---|
| nominal | `RECOMMEND` | Local fixture policy expectation only |
| adversarial | `BLOCK` | Local fixture policy expectation only |
| uncertain | `REVIEW` | Local fixture policy expectation only |

## Run with Jev

After the human authorizes live stock-fixture calls:

```bash
.venv/bin/python jev.py run 10-semantic-lint --mode live --scope project-live --workspace "$PWD"
```

Alternatively use the Codex MCP `jev_evaluate` tool with this case ID. A live result
may differ from the fixture's simulated answer. Preserve it. The scenario named
uncertain does not force live Jev to express uncertainty.

## Acceptance checks

Confirm required state fields, complete typed answers, actual origin label, model ID
for live runs, and a saved run ID. Verify that the configured policy is deterministic
for a given answer and that `execution_authorized` remains false. A fixture contract
passes when the application branch matches its authored expectation; this is not model
accuracy. The MCP host gate requires an actual Codex tool call, not just the CLI.

## Capture and demonstration plan

Shot 1: show the actual input and explain the bounded question in one sentence.
Shot 2: show the selected option / score / probability and the separate policy result.
Shot 3: show the adversarial or uncertain fixture with its SIMULATED label intact.
Closing point: "This narrows a decision. It does not authorize an action or prove truth."

```bash
.venv/bin/python scripts/capture.py --case 10-semantic-lint --orientation both --seconds 8
```

Switch to `--mode live` only after a matching live receipt exists. Capture is a browser
replay, not a new model call or native Codex screen recording. The 1080×1920 portrait
clip is source footage for a later reel; narration and publication are intentionally
not automated here.

## Adapting to your real system

Prepare the smallest representative text state with authorized synthetic or de-identified
data. Review it privately before granting custom-data access. Do not read the whole
enterprise repository, ticket store or memory database automatically. Use a separate
local JSON file and `--mode live --scope project-live --workspace "$PWD" --state PATH --request-id REVIEW_ID --data-classification internal-minimized` after a custom-data grant. The default
viewer/export hides custom data. Inspect actual external APIs before writing an adapter;
do not infer a deployed integration from this case's industry label.
