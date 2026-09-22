#!/usr/bin/env python3
"""Refresh only this plugin using a detected native CLI command; never edit global config."""
from __future__ import annotations
import argparse,subprocess,sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    result=subprocess.run(['codex','plugin','--help'],capture_output=True,text=True)
    if result.returncode:
        print('CODEX_PLUGIN_CLI_UNAVAILABLE');return 2
    # Feature-detection is bounded local introspection, not another research task.
    if 'update' not in result.stdout:
        print('NATIVE_UPDATE_COMMAND_NOT_CONFIRMED: use the installed plugin UI to refresh Qualixar only.');return 2
    cmd=['codex','plugin','update','qualixar-jev-control@qualixar-jev']
    if not a.apply:
        print('Dry run: '+' '.join(cmd));return 0
    r=subprocess.run(cmd,capture_output=True,text=True)
    if r.returncode:
        print('PLUGIN_REFRESH_FAILED: inspect native CLI help locally; no global configuration was modified by this helper.');return 2
    print('Plugin refreshed. Fully restart Codex and trust changed Qualixar hooks once. Verify runtime version with tools/list.');return 0
if __name__=='__main__':raise SystemExit(main())
