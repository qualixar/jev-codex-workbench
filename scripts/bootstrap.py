#!/usr/bin/env python3
"""Offline, idempotent setup. Only this project changes. Never upgrades Codex."""
from __future__ import annotations
import argparse,hashlib,json,os,re,subprocess,sys,tomllib,venv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from jevkit.security import SafeError,private_json,private_dir,canonical,load_json
BEGIN='# BEGIN JEV-CONTROL MANAGED BLOCK v1'
END='# END JEV-CONTROL MANAGED BLOCK v1'
def digest(data):return hashlib.sha256(data).hexdigest()

def configure(root,python):
    folder=root/'.codex';private_dir(folder);path=folder/'config.toml'
    if path.is_symlink():raise SafeError('UNSAFE_CODEX_CONFIG')
    old=path.read_bytes() if path.exists() else b''
    try:parsed=tomllib.loads(old.decode())
    except Exception:raise SafeError('EXISTING_CODEX_CONFIG_INVALID: unchanged') from None
    canonical_root = root.resolve()
    section='\n'.join([BEGIN,'[mcp_servers.jev_control]',f'command = {json.dumps(str(python))}',
        f'args = [{json.dumps(str(canonical_root/"jev.py"))}, "mcp", "--scope", "project-live", "--workspace", {json.dumps(str(canonical_root))}]',f'cwd = {json.dumps(str(canonical_root))}',
        'env_vars = ["JEV_PROVIDER", "TYPESAFE_API_KEY", "OPENROUTER_API_KEY"]','startup_timeout_sec = 15','tool_timeout_sec = 120','enabled = true',END])+'\n'
    text=old.decode()
    if BEGIN in text:
        pattern=re.compile(re.escape(BEGIN)+r'[\s\S]*?'+re.escape(END)+r'\n?')
        if len(pattern.findall(text))!=1:raise SafeError('MANAGED_CONFIG_CONFLICT')
        if pattern.search(text).group()==section:return 'already_configured'
        raise SafeError('MANAGED_CONFIG_CHANGED: use documented rollback before relocating the package')
    if 'jev_control' in parsed.get('mcp_servers',{}):raise SafeError('EXISTING_JEV_SERVER: not overwritten; review existing registration')
    updated=(text+('\n' if text and not text.endswith('\n') else '')+'\n'+section).encode()
    try:tomllib.loads(updated.decode())
    except Exception:raise SafeError('NEW_CODEX_CONFIG_INVALID: unchanged') from None
    local=root/'.local';private_dir(local)
    backup=local/'codex-config.before'
    if backup.exists():raise SafeError('EXISTING_ROLLBACK_BACKUP: review previous setup state')
    fd=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as f:f.write(old)
    private_json(local/'installation.json',{'before_sha256':digest(old),'after_sha256':digest(updated),'config_existed':path.exists(),'scope':'project-live','workspace':str(canonical_root)})
    tmp=folder/'config.toml.jev-new'
    fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as f:f.write(updated)
    os.replace(tmp,path)
    return 'project_mcp_configured'

def main():
    if sys.version_info<(3,11):raise SafeError('PYTHON_3_11_REQUIRED: install through your approved package manager')
    parser=argparse.ArgumentParser();parser.add_argument('--skip-tests',action='store_true',help='Diagnostic use only; does not mark installation verified.');a=parser.parse_args()
    target=ROOT/'.venv'
    if target.is_symlink():raise SafeError('UNSAFE_VENV_PATH')
    python=target/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if not python.exists():venv.EnvBuilder(with_pip=True).create(target)
    test_status='NOT_RUN'
    if not a.skip_tests:
        result=subprocess.run([str(python),'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,check=False)
        if result.returncode:raise SafeError('OFFLINE_TESTS_FAILED: Codex configuration was not changed')
        test_status='PASSED'
    config_status=configure(ROOT,python)
    report={'stage':'OFFLINE_SETUP','offline_tests':test_status,'codex_configuration':config_status,
        'codex_host_connection':'NOT_VERIFIED','live_api':'NOT_VERIFIED','native_capture':'NOT_PERFORMED',
        'global_config_modified':False,'model_selection_modified':False,'credential_stored_by_setup':False}
    private_json(ROOT/'.local'/'SETUP_REPORT.json',report)
    print(json.dumps(report,indent=2));return 0
if __name__=='__main__':
    try:sys.exit(main())
    except SafeError as e:print(str(e),file=sys.stderr);sys.exit(2)
