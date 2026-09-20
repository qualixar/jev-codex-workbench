#!/usr/bin/env python3
"""Build a network-free snapshot from the actual stored synthetic receipts."""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from jevkit.engine import catalog
from jevkit.web_server import records
from jevkit.security import canonical,private_dir,private_json

def build(root=ROOT):
    data={'catalog':catalog(root),'runs':records(root)}
    html=(root/'web'/'index.html').read_text()
    html=html.replace('<link rel="stylesheet" href="/styles.css">','<style>'+(root/'web'/'styles.css').read_text()+'</style>')
    js=canonical(data).decode().replace('<',r'\u003c')
    script='<script>window.__WORKBENCH_SNAPSHOT__='+js+';</script><script>'+(root/'web'/'app.js').read_text()+'</script>'
    html=html.replace('<script defer src="/app.js"></script>','').replace('</body>',script+'</body>')
    # Snapshot uses inline scripts, but forbids network activity and embedding.
    csp="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; img-src data:; base-uri 'none'; form-action 'none'"
    html=html.replace('<meta charset="utf-8">','<meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="'+csp+'">')
    dest=root/'artifacts'/'exports';private_dir(dest);path=dest/'evidence-viewer.html';path.write_text(html);path.chmod(0o600)
    private_json(dest/'viewer-manifest.json',{'snapshot':True,'file':'evidence-viewer.html','sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'synthetic_receipts':len(data['runs']),'fixture_receipts':sum(r['mode']=='fixture' for r in data['runs']),
        'live_receipts':sum(r['mode']=='live' for r in data['runs']),'publication_review_required':True})
    return path
if __name__=='__main__':
    build();print('Wrote artifacts/exports/evidence-viewer.html — offline snapshot; not a new inference.')
