#!/usr/bin/env python3
"""Install the local Codex marketplace/plugin and configure one live provider."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.configure_provider import configure  # noqa: E402
from jevkit.security import SafeError  # noqa: E402


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
    for command in commands:
        result = runner(command, text=True, capture_output=True)
        if result.returncode != 0:
            message = (result.stderr or "").strip()
            if "already" in message.lower() and "marketplace" in command:
                continue
            raise SafeError(
                "PLUGIN_INSTALL_FAILED: "
                + (message.splitlines()[-1] if message else "Codex returned an error")
            )


def main() -> int:
    if sys.version_info < (3, 11):
        raise SafeError("PYTHON_3_11_REQUIRED")
    if not sys.stdin.isatty():
        raise SafeError("PRIVATE_TERMINAL_REQUIRED: run this yourself outside agent logs")
    print("Qualixar Jev Control installer")
    print("Your key is entered through a hidden prompt and is never passed to Codex chat.")
    configure()
    install_plugin(ROOT)
    print("Installation complete. Fully quit and reopen Codex Desktop, then start a new task.")
    print("Live calls still require a separate workspace-bound human grant.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SafeError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2)
