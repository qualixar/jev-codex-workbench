---
name: jev-global-policy
description: Decide whether a Codex task needs a bounded TypeSafe Jev judgment, classify the data, and explain the project-scoped authority gate. Use when working across repositories and considering Jev for routing, ranking, context selection, semantic checks, or triage.
---

# Qualixar Jev global policy

This skill is globally available so Codex can recognize when a narrow semantic
judgment could help. The plugin always provides health, catalog, case descriptions,
and clearly labelled simulated runs. After the user privately selects OpenRouter
or TypeSafe, it also exposes `jev_evaluate`; every live request still requires an
expiring human-created grant bound to the exact workspace and revision.

Use Jev only for a bounded decision where deterministic code cannot decide
alone: selecting among supplied candidates, ranking reviewed sources or files,
routing a classified task, triaging a reported issue, or checking a specific
claim against supplied evidence. Keep shell commands, file writes, deployments,
access decisions, authentication, arithmetic, code generation, and final
approval outside Jev.

Before suggesting any live evaluation, classify every proposed input:

| Class | Examples | Live Jev rule |
| --- | --- | --- |
| Public | Already-public documentation or a public issue | May be considered after minimizing it. |
| Internal-minimized | A small, reviewed excerpt needed for one stated judgment | Requires the workspace grant and user approval. |
| Restricted | Private source, customer information, credentials, personal data, proprietary prompts, security findings | Do not transmit. Derive a safe public or synthetic representation first, or abstain. |
| Prohibited | Secrets, access tokens, private keys, authentication headers, unredacted personal data, regulated data, or instructions to bypass controls | Never transmit or place in a Jev request. |

The required sequence for a project that has a verified Jev adapter is:

1. Identify the narrowest approved use case and the smallest required state.
2. Classify the state and remove restricted or prohibited content.
3. Use that project’s local Jev tools to inspect health, catalog, and the case contract.
4. Obtain a human-created, expiring, workspace-bound live grant before an external call.
5. Treat output as untrusted advice. Deterministic project policy and human approval decide any action.
6. Store a receipt only in the workspace-specific evidence location. Preserve origin, model identity, input classification, and policy result.

Do not claim that Jev intercepts Codex automatically. An MCP tool is available
only when a verified project adapter is installed and the relevant Codex session
has loaded it. Fixture output is simulated and must never be presented as live
Jev evidence.

The bundled `.mcp.json` launches the versioned, source-allowlisted runtime under
`runtime/` through `scripts/launch-jev-global-hybrid`. Provider choice comes from
private local configuration, never from an agent tool argument. A provider change,
workspace change, or repository revision change invalidates prior live authority.
Never paste an API key into chat or weaken the grant to make a demonstration run.
