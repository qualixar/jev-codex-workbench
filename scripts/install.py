#!/usr/bin/env python3
"""Install the local Codex marketplace/plugin and configure one live provider."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.configure_provider import configure  # noqa: E402
from jevkit.policy_mode import write_policy_mode  # noqa: E402
from jevkit.security import SafeError  # noqa: E402


def ensure_default_policy(config_root: Path | None = None) -> Path:
    """Enable low-friction local routing without replacing an explicit user choice."""
    return write_policy_mode("assist", config_root, overwrite=False)


def install_plugin(
    root: Path = ROOT,
    *,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> None:
    if shutil.which("codex") is None:
        raise SafeError("CODEX_CLI_REQUIRED: install or update Codex first")
    commands = [
        ["codex", "plugin", "marketplace", "add", str(root.resolve()), "--json"],
        [
            "codex",
            "plugin",
            "add",
            "qualixar-jev-control@qualixar-jev",
            "--json",
        ],
    ]
    expected_version = json.loads(
        (root / "plugins" / "qualixar-jev-control" / ".codex-plugin" / "plugin.json").read_text()
    )["version"]
    for command in commands:
        result = runner(command, text=True, capture_output=True)
        if result.returncode != 0:
            raise SafeError("PLUGIN_INSTALL_FAILED: use the documented upgrade steps")
        try:
            details = json.loads(result.stdout or "{}")
        except json.JSONDecodeError:
            raise SafeError("PLUGIN_INSTALL_RESULT_INVALID") from None
        if "marketplace" in command:
            installed_root = details.get("installedRoot")
            if installed_root and Path(installed_root).resolve() != root.resolve():
                raise SafeError("MARKETPLACE_SOURCE_MISMATCH: use the documented upgrade steps")
        elif details.get("version") and details["version"] != expected_version:
            raise SafeError("PLUGIN_VERSION_MISMATCH: use the documented upgrade steps")


def main() -> int:
    if sys.version_info < (3, 11):
        raise SafeError("PYTHON_3_11_REQUIRED")
    if not sys.stdin.isatty():
        raise SafeError("PRIVATE_TERMINAL_REQUIRED: run this yourself outside agent logs")
    print("Qualixar Jev Control installer")
    print("Your key is entered through a hidden prompt and is never passed to Codex chat.")
    configure()
    ensure_default_policy()
    install_plugin(ROOT)
    print("Installation complete. Review the changed Qualixar Jev hooks in the Codex CLI,")
    print("then fully quit and reopen Codex Desktop before relying on hook behavior.")
    print("Run `python3 auto_entry.py enroll --help` in a private terminal to review")
    print("one-time workspace enrollment. Enrolled workspaces use standing daily limits;")
    print("unenrolled workspaces retain the original grant-based path.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SafeError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2)
