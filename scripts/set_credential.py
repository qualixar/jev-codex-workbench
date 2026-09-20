#!/usr/bin/env python3
"""Backward-compatible entry point for private provider credential setup."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from configure_provider import configure
from jevkit.security import SafeError
try:
    if not sys.stdin.isatty():raise SafeError('PRIVATE_TERMINAL_REQUIRED: run this yourself outside agent logs')
    print('This stores one selected provider key in an owner-only local file outside the project. It is NOT encrypted.')
    print('Use JEV_PROVIDER plus the matching environment variable when policy prohibits local plaintext storage.')
    if input('Type STORE to continue: ').strip()!='STORE':raise SafeError('CANCELED')
    configure()
except SafeError as e:print(str(e),file=sys.stderr);sys.exit(2)
