#!/usr/bin/env python3
"""Install the reviewed MLX revision separately; download a pinned public checkpoint.
Runs on the user's Mac, not during package validation. No cloud API key is requested.
"""
from __future__ import annotations
import argparse,hashlib,json,os,platform,subprocess,sys,venv
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from jev_auto.common import AutoError,home_root,private_dir,write_private,read_private

RUNTIME_COMMIT='0a859518634112655cb97c745dbf04f5191aaf13'
MODELS={
 'english':{'repository':'aac6fef/laya-mlx','revision':'047678560251f28113ee8f5df4be82102c7bf336','weight_sha256':'b9c07bf14be2fa5c78a9193a3e6d840ac80e89e62fc40f425834c3d8a6eaa3de'},
 'multilingual':{'repository':'aac6fef/laya-multilingual-mlx','revision':'ba40c87fcb357f1643d04d71323af9cdc3b9e591','weight_sha256':'7fc5834af4d8fdfb268d272a9d1a66e5819a0daac98241651c4c888cc43adff1'},
}

def checked(command,env=None):
    r=subprocess.run(command,capture_output=True,text=True,env=env)
    if r.returncode:raise AutoError('MLX_INSTALL_COMMAND_FAILED: '+Path(command[0]).name)
    return r.stdout

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',choices=list(MODELS),default='english');p.add_argument('--download-stage',type=Path)
    a=p.parse_args(argv)
    if a.download_stage:
        spec=read_private(a.download_stage,10_000)
        from huggingface_hub import snapshot_download
        root=Path(spec['model_dir']);root.mkdir(parents=True,exist_ok=True)
        snapshot_download(spec['repository'],revision=spec['revision'],local_dir=str(root),
                          allow_patterns=['*.json','*.safetensors','tokenizer/*','encoder/config.json','LICENSE','NOTICE','README.md'])
        hashes={}
        for f in sorted(root.rglob('*')):
            if f.is_file() and '.cache' not in f.relative_to(root).parts:
                h=hashlib.sha256()
                with f.open('rb') as s:
                    for block in iter(lambda:s.read(1<<20),b''):h.update(block)
                hashes[str(f.relative_to(root))]=h.hexdigest()
        if hashes.get('model.safetensors')!=spec['weight_sha256']:raise AutoError('MLX_DOWNLOAD_WEIGHT_HASH')
        for name in ('rl_agent_config.json','encoder/config.json','tokenizer/tokenizer.json'):
            if name not in hashes:raise AutoError('MLX_MODEL_ARTIFACT_MISSING')
        write_private(Path(spec['artifact_manifest']),{'schema_version':1,'repository':spec['repository'],'revision':spec['revision'],'files':hashes})
        return 0
    if platform.system()!='Darwin' or platform.machine()!='arm64':raise AutoError('APPLE_SILICON_MAC_REQUIRED')
    if sys.version_info<(3,11):raise AutoError('PYTHON_3_11_REQUIRED')
    if not sys.stdin.isatty():raise AutoError('PRIVATE_TERMINAL_SETUP_REQUIRED')
    print('Installs pinned laya-mlx code (Apache-2.0) and a public checkpoint in a separate environment.')
    print('Model files consume disk/RAM. No training is required. No Codex settings or SLM files are changed.')
    if input('Type INSTALL to download and install: ').strip()!='INSTALL':raise AutoError('INSTALL_CANCELLED')
    root=private_dir(home_root());envdir=root/'mlx-env';python=envdir/'bin'/'python'
    if not python.exists():venv.EnvBuilder(with_pip=True).create(envdir)
    install_env={k:v for k,v in os.environ.items() if not any(t in k.upper() for t in ('KEY','TOKEN','PASSWORD','SECRET'))}
    install_env['HF_HUB_DISABLE_TELEMETRY']='1'
    checked([str(python),'-m','pip','install','mlx==0.32.2',
             'git+https://github.com/mizorewww/laya-mlx.git@'+RUNTIME_COMMIT],install_env)
    checked([str(python),'-m','pip','check'],install_env)
    direct=checked([str(python),'-c',"import importlib.metadata as m; print(m.distribution('laya-mlx').read_text('direct_url.json'))"],install_env)
    if json.loads(direct).get('vcs_info',{}).get('commit_id')!=RUNTIME_COMMIT:raise AutoError('MLX_RUNTIME_REVISION')
    spec={**MODELS[a.checkpoint],'python':str(python),'model_dir':str(root/('model-'+a.checkpoint)),
          'artifact_manifest':str(root/('model-'+a.checkpoint+'-manifest.json')),'runtime_commit':RUNTIME_COMMIT}
    draft=root/'mlx-installation.pending.json';write_private(draft,spec)
    checked([str(python),str(Path(__file__).resolve()),'--download-stage',str(draft)],install_env)
    frozen=checked([str(python),'-m','pip','freeze','--all'],install_env)
    (root/'mlx-installed.freeze.txt').write_text(frozen);(root/'mlx-installed.freeze.txt').chmod(0o600)
    write_private(root/'mlx-installation.json',spec)
    draft.unlink()
    print('Pinned MLX installation complete. Use auto_entry.py route-local or enroll; warmup is separate from steady-state latency.')
    return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except AutoError as e:print(str(e),file=sys.stderr);raise SystemExit(2)
