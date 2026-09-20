#!/usr/bin/env python3
import sys,shutil,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
# Report presence only; do not dump config, environment, usernames, or credentials.
print(json.dumps({'python_supported':sys.version_info>=(3,11),'python_version':'.'.join(map(str,sys.version_info[:3])),
'codex_cli_available':bool(shutil.which('codex')),'ffmpeg_available':bool(shutil.which('ffmpeg')),
'official_typesafe_skill_detected':any((p/'typesafe-ai'/'SKILL.md').is_file() for p in [root/'.agents'/'skills',Path.home()/'.agents'/'skills',Path.home()/'.codex'/'skills']),
'network_tested':False,'credentials_inspected':False},indent=2))
sys.exit(0 if sys.version_info>=(3,11) else 2)
