#!/usr/bin/env python3
"""Codex lifecycle adapter for the local Jev policy control plane."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> int:
    plugin_root = Path(os.environ.get("PLUGIN_ROOT", Path(__file__).resolve().parents[1]))
    runtime = plugin_root / "runtime"
    if not runtime.is_dir():
        return 0
    sys.path.insert(0, str(runtime))
    from jevkit.policy_mode import handle_hook_event, policy_mode

    try:
        raw = sys.stdin.buffer.read(128_001)
        if len(raw) > 128_000:
            return 0
        event = json.loads(raw)
    except (ValueError, UnicodeError, RecursionError):
        return 0
    data_root = Path(os.environ.get("PLUGIN_DATA", Path.home() / ".local" / "state" / "jev-control"))
    try:
        result = handle_hook_event(event, data_root=data_root)
    except Exception:
        result = (
            {
                "decision": "block",
                "reason": "Jev Policy Mode enforce failed safely; inspect the hook configuration.",
            }
            if policy_mode() == "enforce" and event.get("hook_event_name") == "UserPromptSubmit"
            else None
        )
    if result is not None:
        print(json.dumps(result, ensure_ascii=True, allow_nan=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
