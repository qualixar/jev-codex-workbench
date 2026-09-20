#!/usr/bin/env python3
"""Convert an existing capture to H.264 MP4. No cropping, synthetic action or posting."""
from __future__ import annotations
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from jevkit.security import SafeError,private_json,load_json

def main():
    p=argparse.ArgumentParser();p.add_argument('--capture-dir',required=True,type=Path);a=p.parse_args()
    folder=a.capture_dir.resolve();base=(ROOT/'artifacts'/'captures').resolve()
    if base not in folder.parents or a.capture_dir.is_symlink():raise SafeError('CAPTURE_DIRECTORY_REQUIRED')
    source=folder/'recorded-evidence.webm';m=load_json(folder/'capture-manifest.json')
    if source.is_symlink() or not source.is_file():raise SafeError('NO_CAPTURE_VIDEO')
    if m.get('files',{}).get(source.name)!=hashlib.sha256(source.read_bytes()).hexdigest():raise SafeError('CAPTURE_HASH_MISMATCH')
    if not shutil.which('ffmpeg'):raise SafeError('FFMPEG_NOT_INSTALLED: use an approved package manager')
    out=folder/'reel-source.mp4'
    if out.exists():raise SafeError('REEL_ALREADY_EXISTS: not overwritten')
    # Pad rather than crop so the provenance banner cannot silently disappear.
    vf='scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1'
    result=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-n','-i',str(source),'-vf',vf,'-an','-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],capture_output=True,timeout=120)
    if result.returncode:raise SafeError('REEL_TRANSCODE_FAILED')
    out.chmod(0o600)
    private_json(folder/'reel-manifest.json',{'source_run_id':m['run_id'],'source_mode':m['source_mode'],
        'source_capture_sha256':m['files'][source.name],'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),
        'file':out.name,'format':'1080x1920 H.264 MP4, padded, no audio',
        'meaning':'Editorial source footage, not a completed narrated reel or new model call.',
        'publication_review_required':True})
    print(json.dumps({'file':str(out.relative_to(ROOT)),'publication_review_required':True}))
if __name__=='__main__':
    try:main()
    except SafeError as e:print(str(e),file=sys.stderr);sys.exit(2)
    except Exception:print('REEL_FAILED',file=sys.stderr);sys.exit(3)
