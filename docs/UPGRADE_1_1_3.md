# Upgrade Qualixar Jev Codex Workbench to 1.1.3

The plugin marketplace source matters. If it still points at a 1.1.2 checkout, adding the plugin again can reinstall 1.1.2 even when another directory contains the new source.

1. Preserve any uncommitted work in your existing checkout. Use a clean release checkout for the upgrade. Run `python3 scripts/verify_package.py` there.
2. Fully quit Codex Desktop and leave any active Codex CLI task. Use a separate private terminal for the commands below. This avoids an active task invoking a hook file while its old plugin cache is being replaced.
3. From the 1.1.3 checkout, replace only the Qualixar Jev plugin and its marketplace source:

```bash
cd /absolute/path/to/jev-codex-workbench
codex plugin remove qualixar-jev-control@qualixar-jev
codex plugin marketplace remove qualixar-jev
codex plugin marketplace add "$PWD"
codex plugin add qualixar-jev-control@qualixar-jev
codex plugin list
```

The final listing must show `qualixar-jev-control@qualixar-jev` version `1.1.3` from this checkout. Do not remove another marketplace, change your Codex model, replace SLM, or overwrite global configuration.

4. Start Codex CLI and review the current Qualixar Jev hook definitions. Trust only the hooks you intend to run. Then restart Codex Desktop and verify `jev_auto_status` in a fresh task. Plugin installation alone does not establish hook trust.
5. If you want standing operation, enroll a reviewed workspace privately with `python3 auto_entry.py enroll --help`. An unenrolled workspace retains the original grant-based behavior. Existing credentials remain in the private provider store.

The upgrade does not publish or push the repository. See [the README](../README.md) for the user path and [architecture](ARCHITECTURE_1_1_3.md) for boundaries.
