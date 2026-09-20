#!/usr/bin/env python3
import sys,hashlib,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from jevkit.security import SafeError,load_json
from jevkit.runtime import revoke_workspace_grant
try:
    path=ROOT/'.codex'/'config.toml';backup=ROOT/'.local'/'codex-config.before';manifest=ROOT/'.local'/'installation.json'
    if path.is_symlink() or backup.is_symlink():raise SafeError('UNSAFE_ROLLBACK_PATH')
    m=load_json(manifest)
    sha=lambda b:hashlib.sha256(b).hexdigest()
    if not path.exists() or sha(path.read_bytes())!=m['after_sha256']:raise SafeError('ROLLBACK_CONFLICT: current config differs; nothing changed')
    data=backup.read_bytes()
    if sha(data)!=m['before_sha256']:raise SafeError('ROLLBACK_BACKUP_MISMATCH')
    if m['config_existed']:
        temp=path.with_suffix('.restore')
        fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as f:f.write(data)
        os.replace(temp,path)
    else:path.unlink()
    workspace=Path(m.get('workspace',ROOT))
    revoke_workspace_grant(ROOT,workspace)
    backup.unlink();manifest.unlink()
    print('Project MCP configuration restored; live grants revoked. Existing credentials, evidence, and virtual environment remain unchanged.')
except SafeError as e:print(str(e),file=sys.stderr);sys.exit(2)
