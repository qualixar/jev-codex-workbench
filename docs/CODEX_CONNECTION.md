# Connect from the actual Codex host

Bootstrap writes a managed `mcp_servers.jev_control` block to this project's
`.codex/config.toml`. It preserves existing project settings and does not touch the
global config or selected model. The registered command points to this folder's venv
and `jev.py mcp`; keep the folder at its permanent location after setup.

Open the folder as a trusted project in Codex using its normal controls. Do not bypass
managed trust policy. Reload/restart the session when configuration or skills change.
Where available, inspect `codex mcp list` and the `/mcp` status. Then use actual tool
calls from Codex: `jev_health`, `jev_catalog`, `jev_describe` for case 08, and
`jev_run_fixture` for its adversarial scenario. Record the tool names and successful
results, not configuration screenshots alone.

The project skill is `.agents/skills/jev-control/SKILL.md`. Invoke `$jev-control` to
request this workflow explicitly. The existing official `typesafe-ai` skill is
complementary API guidance, not another server. Detect and reuse it. Do not install
multiple copies because the first one is not visible in a session; inspect current
skill discovery and restart first.

When the official skill is genuinely missing, use the current TypeSafe documentation
and inspect the upstream source before an approved installation. Its documented
installer is `npx skills add typesafe-ai/skills --skill typesafe-ai`; this is an optional
network step and is not needed for the package's core executable adapter. Never paste
an API key into that command. Do not install an unreviewed community Jev MCP.

The global plugin makes the tools discoverable in other repositories after Codex
Desktop restarts. Availability is not authority: live use in another repository still
requires a new human-created grant bound to that repository, revision, and selected
provider profile. Preserve the target project's existing AGENTS.md, skills, and config;
the global plugin does not need to overwrite them.
