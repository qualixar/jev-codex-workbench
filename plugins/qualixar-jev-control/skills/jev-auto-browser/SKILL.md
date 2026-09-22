---
name: jev-auto-browser
description: Execute short Jev-selected navigation bursts inside Codex's existing Computer Use browser, with compact handoffs and no separate browser driver.
---
# Workbench browser bridge

Prerequisites: workspace is enrolled, broker running, and its browser origins were approved.
Use the existing Computer Use skill to obtain an authorized tab in cua_repl. Follow that
installed skill's bootstrap exactly; do not invent its tab discovery calls, replace it,
launch Playwright/CDP, or import another browser connection.

Import bridge.mjs from THIS installed skill directory into the existing cua_repl runtime.
The runtime must support node:fs, node:net and local filesystem access. If not, return
`BRIDGE_IPC_UNAVAILABLE` and continue the normal Computer Use workflow, not a new driver.

```javascript
const mod = await import('file:///ABSOLUTE_INSTALLED_SKILL_PATH/bridge.mjs');
const cfg = await mod.loadConfig('/ABSOLUTE_ENROLLED_WORKSPACE');
const flow = mod.createSession(existingAuthorizedTab, {
  ...cfg,
  goal: 'Open the next result pages and reach the requested public evidence.',
  controls: [{op:'scroll', direction:'down'}],
  discover: true,
  maxMs: 45000
});
const outcome = await flow.run();
console.log(outcome);
```

Replace the two paths with observed local paths, not guessed values. existingAuthorizedTab
means the live tab object obtained by the user's Computer Use skill, not a new instance.
If enrollment used a custom `XDG_CONFIG_HOME`, pass that directory as the second
argument to `loadConfig`; the browser runtime does not expose environment variables.
The defaults discover navigation labels only. For other benign observed controls, supply
explicit `{op:'click', name:'EXACT_OBSERVED_LABEL'}` entries. Never invent selectors, use
hidden DOM fields, send cookies/credentials, or ask Jev to interpret screenshots.

The helper owns several mechanical steps and returns a compact outcome. It does not claim
that every screenshot, browser decision or Codex internal reasoning step is intercepted.
A DONE judgment returns `needs_verification`, not verified success. Inspect the final page
with the native skill and check the user's requirement. Composing text, credential entry,
consequential submission, ambiguous controls and unavailable APIs return to normal Codex.
Full history is available via flow.inspect() only when needed; do not print it by default.

Native control calls used: getAXState({emit:false,disableDiffing:true}), click(index),
pressKey(key), and reload(). These are adapted from the pinned MIT upstream bridge.
A native smoke test is required on the installed host. Mock tests alone are insufficient.
