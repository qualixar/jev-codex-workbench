# One-time hook trust for Codex Desktop

Policy Mode is installed globally, but Codex deliberately does not run new or changed
plugin hooks until the local user reviews them. This protects users from a plugin silently
gaining pre-prompt or pre-tool execution.

Codex Desktop currently has no `/hooks` command. Use the Codex CLI once; it shares the same
local configuration and hook-trust state as Desktop.

1. Fully quit Codex Desktop.
2. Open a private terminal and run `codex` from any directory you already trust.
3. When Codex says hooks need review, choose **Review hooks**.
4. Trust only these three entries from `qualixar-jev-control@qualixar-jev`:
   `UserPromptSubmit`, `PreToolUse`, and `PostToolUse`.
5. Exit the CLI with `/exit`, then reopen Codex Desktop and start a new task.

After this one-time review, Policy Mode runs locally on every submitted task in `assist`
mode. A plugin update that changes a hook requires a fresh review because Codex binds trust
to the hook's content hash.

Do not choose a broad “trust all” option if the screen lists hooks from other plugins that
you have not reviewed.

## Managed enterprise deployment

Managed hooks are for an organization that controls devices and Codex policy through its
own `requirements.toml` and MDM deployment. A public plugin cannot mark its own hooks as
managed or auto-trusted. An administrator may deploy reviewed hook scripts in an approved
managed directory and configure them under the organization’s managed Codex policy. Keep
provider credentials, data classification, and workspace grants separate from that device
policy. See the current OpenAI hooks documentation before deployment.
