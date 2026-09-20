#!/usr/bin/env python3
"""Optional capture dependency installation. Requires explicit local approval."""
import sys,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
if '--approved-network-install' not in sys.argv:
    print('Not installed. Review requirements-capture.txt, then rerun with --approved-network-install. This downloads Playwright and Chromium.',file=sys.stderr);sys.exit(2)
if Path(sys.prefix).resolve()!= (root/'.venv').resolve():
    print('Use .venv/bin/python scripts/install_capture.py --approved-network-install',file=sys.stderr);sys.exit(2)
subprocess.run([sys.executable,'-m','pip','install','-r',str(root/'requirements-capture.txt')],check=True)
subprocess.run([sys.executable,'-m','playwright','install','chromium'],check=True)
