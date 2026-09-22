# Review Qualixar Jev Codex Workbench hooks

Codex skips new or changed plugin hooks until the local user reviews and trusts them. Plugin installation, MCP tool availability, and hook trust are separate checks.

1. Fully quit Codex Desktop after installing or refreshing the plugin.
2. Open a private terminal in a repository you trust and run `codex`.
3. Open `/hooks`. Inspect the entries whose source is `qualixar-jev-control@qualixar-jev` and whose command points to that plugin's current `jev_policy_hook.py`.
4. Review the five events in 1.1.3: `SessionStart`, `UserPromptSubmit`, `SubagentStart`, `PreToolUse`, and `PostToolUse`. Trust only the definitions you intend to run. Do not use a broad trust-all action for unrelated plugins you have not reviewed.
5. Quit the CLI and reopen Codex Desktop. In a fresh task, verify the 1.1.3 MCP tools and, where relevant, the hook behavior.

Enrolled prompt preparation builds a local shortlist. Automatic `PostToolUse` reduction runs only when the owner selected the local Laya-MLX `sieve` route. Explicit remote Jev calls still use native Codex permissions and the workspace policy. An unenrolled workspace retains the original policy/grant path.

A plugin update that changes hook content may require review again. The hook menu displays installed and active counts and each selected hook's source and trust state. See the [official Codex hooks reference](https://learn.chatgpt.com/docs/hooks) for current host semantics.

## Managed deployments

An organization may deploy reviewed hooks under its own managed Codex policy. A public plugin cannot make itself managed or auto-trusted. Keep provider credentials, workspace enrollment, and device policy separate. See the official hooks reference for managed-host details.
