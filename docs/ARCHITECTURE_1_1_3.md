# Qualixar Jev Codex Workbench 1.1.3 architecture

This document describes the source and authority boundaries behind the README diagrams. The images are conceptual maps; the code paths and gates below define behavior.

## Components and authority

![Workbench architecture](assets/qualixar-jev-codex-workbench-architecture.png)

Codex retains the selected coding model, tool execution, native permissions, and its existing browser. The Qualixar plugin exposes an MCP facade and lifecycle hooks. The `jev_auto` broker owns a workspace-scoped policy, private Unix socket, budget, cache, and local receipts. TypeSafe Jev or OpenRouter is the selected remote decision provider. Laya-MLX is an optional local route for selected small recipes. SuperLocalMemory remains a separate installed memory system.

No Jev or Laya response authorizes a shell command, file write, deployment, access decision, or task completion. An MCP result is advisory evidence for Codex to use under its own controls.

## Decision request

![Request decision flow](assets/request-decision-flow.png)

1. The owner selects a provider, installs the plugin, and privately enrolls a reviewed Git workspace. Enrollment stores an expiry, daily call and payload-byte limits, allowed browser origins, and a data-classification label. The label records the owner's intended scope; it does **not** detect confidential prose.
2. A Codex call to `jev_evaluate` supplies a specific workflow and state. The facade validates the tool name and arguments, then asks the broker through the local socket.
3. The broker re-reads policy before reserving a provider attempt. It checks workspace identity, expiry, recipe, provider route, and budget. It screens recognized secret and private-path patterns; this is a safeguard, not a substitute for reviewing material before an explicit remote call.
4. Exact requests can reuse an unexpired content-addressed cache entry. Simultaneous identical requests coalesce in the resident broker. A changed state or question has a different key and requires a fresh decision.
5. The model result is validated against the expected answer schema. The full decision receipt stays in private local storage; the MCP response returns a compact policy status and receipt ID. `jev_recall` retrieves detail when needed.

**Automatic prompt preparation is local.** The `UserPromptSubmit` hook may store the goal in the workspace's private local state and return a deterministic shortlist. It does not send the new prompt or skill excerpts to a cloud provider. When the owner explicitly routes `prepare` to local Laya-MLX, that selection may run in the local worker. Explicit remote Jev calls still transmit their supplied state to the selected provider.

## Extractive output and exact recall

![Evidence flow](assets/evidence-flow.png)

1. A successful plain-text tool result is eligible only when the native hook is trusted, the output is large enough, the goal is known, and the owner selected the **local Laya-MLX** `sieve` route. The automatic hook does not forward raw tool output to a cloud provider.
2. Failing commands, errors, mandatory instructions, constraints, structured SLM output, and uncertain blocks are kept. An unsupported or unavailable reduction path leaves the original output in place.
3. The sieve chooses exact source blocks. It does not write a model-generated replacement summary. If it can omit enough material to provide a net reduction, the compact view contains the retained text and a marker with omitted line numbers and a receipt ID.
4. `jev_recall` restores any permitted omitted range from private local source storage. The source, local receipt, and model-visible compact view have different roles; character withholding is not a host token-saving measurement.

The explicit `jev_reduce` tool can be called with reviewed text. If that workspace's `sieve` route is remote, the supplied text may be sent to the selected provider; the automatic hook remains local-only.

## Existing browser bridge

![Existing browser path](assets/existing-browser-path.png)

The browser bridge imports into Codex's existing Computer Use runtime and receives an already authorized tab handle. It reads the tab's accessibility state, verifies the enrolled origin, constructs actions only from observed controls, asks the broker for a bounded next action, executes it in the same tab, and returns a compact handoff. Codex independently checks the final page. The bridge never opens a second browser, obtains credentials, types into forms, or treats a model's `DONE` judgment as final proof.

The owner configures the maximum browser steps at enrollment. The bridge rejects a larger per-run override, and the broker independently checks each request's step index against the enrolled cap. This is a workflow boundary for the agent, not an OS isolation boundary against arbitrary same-user code.

## Optional local route

The isolated MLX installer verifies a pinned runtime commit and the downloaded checkpoint weight hash. The local worker warms once and remains resident. The owner may route `sieve` and `probe` locally; these selected recipes do not silently fall back to the cloud. Preflight checks the actual model input budget before inference, and unjudged source blocks remain in the output. The Codex coding model does not change.

## Measurement boundary

The broker records provider attempts, payload bytes, evidence receipts, and proposed characters withheld. It does not know actual Codex host tokens or subscription savings. To claim a task-level effect, compare accepted baseline and treatment runs with the same coding model and effort, including retries, elapsed time, host usage, provider usage, and any local compute estimate. Unknown values stay null. See the measurement tools in `jev_auto/measure.py` and the public test commands in the README.
