# Start with Qualixar Jev Codex Workbench

Version **1.1.3** adds standing workspace operation and optional local Laya-MLX to the existing 20 bounded Jev workflows. Codex remains the coding and execution agent. The workbench offers narrow decisions and recoverable evidence; it does not grant execution authority.

## First installation

Use Python 3.11+ and the Codex CLI. In a private terminal:

```bash
git clone https://github.com/qualixar/jev-codex-workbench.git
cd jev-codex-workbench
python3 scripts/install.py
```

The installer configures your selected provider with a hidden credential prompt. Quit and reopen Codex, then review the changed Qualixar Jev hooks in Codex CLI. See [hook trust](docs/TRUSTING_HOOKS.md). For an existing 1.1.2 installation, use the [source-aware upgrade procedure](docs/UPGRADE_1_1_3.md) so an old marketplace does not reinstall old code.

## Enroll a workspace for standing operation

Installation alone does not authorize live provider calls. Review the workspace and run:

```bash
python3 auto_entry.py enroll \
  --workspace /absolute/path/to/reviewed-workspace \
  --provider existing \
  --classification public \
  --days 30 --daily-calls 1000 --daily-bytes 20000000
```

The CLI displays the scope and asks the owner to type `ENABLE`. The classification label records your selection; it does not detect confidential prose. Automatic prompt preparation stays local. Automatic output filtering requires a local Laya-MLX `sieve` route. Explicit remote Jev calls transmit the supplied state to the selected provider, so review that input. Native Codex permissions still apply.

For an unenrolled workspace, the original grant-based path remains available in [legacy live validation](docs/LIVE_VALIDATION.md).
The plugin is globally available in Codex; standing policy follows the Git workspace
root. Subfolders share one enrollment, while another repository needs its own one-time
enrollment and local route selection.

## Check the result

```bash
codex plugin list
python3 auto_entry.py status --workspace /absolute/path/to/reviewed-workspace
python3 scripts/verify_package.py
python3 -m unittest discover -s tests -v
node --test tests/jev_auto_browser.test.mjs
python3 jev.py suite
```

A fresh Codex task should expose `jev_auto_status` and the original catalog/fixture tools. Fixture outputs are simulated; they do not establish live accuracy or token savings. See the [README](README.md) for the four diagrams and [architecture](docs/ARCHITECTURE_1_1_3.md) for the full flow.
