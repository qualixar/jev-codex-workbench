#!/usr/bin/env python3
"""Set the local Codex Jev Policy Mode without exposing credentials."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jevkit.policy_mode import POLICY_MODES, policy_status, write_policy_mode  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=POLICY_MODES)
    args = parser.parse_args()
    write_policy_mode(args.mode)
    status = policy_status()
    print(f"Jev Policy Mode: {status['mode']}")
    print("Restart Codex Desktop and review the plugin hooks with /hooks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
