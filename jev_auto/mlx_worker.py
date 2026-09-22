"""Actual laya_mlx integration, intended to run only in the dedicated Mac venv."""
from __future__ import annotations
import contextlib, hashlib, importlib.metadata, json, os, platform, sys
from pathlib import Path
from .common import AutoError, canonical, decode, read_private, safe_path
from .mlx_preflight import preflight

def main():
    agent=None;cfg=None
    for raw in sys.stdin.buffer:
        try:
            req=decode(raw,150_000)
            if req.get('kind')=='load':
                cfg=req['config']
                if platform.system()!='Darwin' or platform.machine()!='arm64':raise AutoError('MLX_APPLE_SILICON_REQUIRED')
                folder=Path(cfg['model_dir'])
                if not folder.is_dir():raise AutoError('MLX_MODEL_DIRECTORY')
                h=hashlib.sha256()
                with (folder/'model.safetensors').open('rb') as f:
                    for part in iter(lambda:f.read(1<<20),b''):h.update(part)
                if h.hexdigest()!=cfg['weight_sha256']:raise AutoError('MLX_WEIGHT_HASH')
                # Pin non-weight files too: enrollment supplies the installer-generated manifest.
                manifest=read_private(Path(cfg['artifact_manifest']),100_000)
                for name,sha in manifest['files'].items():
                    rel=Path(name)
                    if rel.is_absolute() or '..' in rel.parts:raise AutoError('MLX_ARTIFACT_PATH')
                    artifact=safe_path(folder/rel)
                    h=hashlib.sha256()
                    with artifact.open('rb') as stream:
                        for part in iter(lambda:stream.read(1<<20),b''):h.update(part)
                    if h.hexdigest()!=sha:raise AutoError('MLX_ARTIFACT_HASH')
                import laya_mlx
                with contextlib.redirect_stdout(sys.stderr):
                    agent=laya_mlx.load(str(folder),dtype='float16',batch_size=16,compile=False,cache_prompts=True)
                result={'ready':True,'runtime_version':importlib.metadata.version('laya-mlx'),'checkpoint':cfg['repository']}
            elif req.get('kind')=='predict' and agent is not None:
                preflight(agent.tok,agent.cfg,req['state'],req['questions'])
                with contextlib.redirect_stdout(sys.stderr):raw_result=agent.predict(req['state'],req['questions'])
                # The artifact is verified above. Do not leak its absolute local path as model name.
                result={**raw_result,'model':cfg['repository']}
            else:raise AutoError('MLX_LOAD_FIRST')
            message={'ok':True,'result':result}
        except AutoError as e:message={'ok':False,'error':str(e)}
        except Exception:message={'ok':False,'error':'MLX_RUNTIME_FAILURE'}
        print(canonical(message).decode(),flush=True)
if __name__=='__main__':main()
