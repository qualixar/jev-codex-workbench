#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'MANIFEST.json').read_text())
bad=[]
for rel,expected in manifest['files'].items():
    path=root/rel
    if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:bad.append(rel)
print(json.dumps({'package_version':manifest['version'],'verified_files':len(manifest['files'])-len(bad),'mismatches':bad},indent=2))
sys.exit(1 if bad else 0)
