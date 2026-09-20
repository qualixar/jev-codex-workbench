#!/usr/bin/env python3
"""Explicit opt-in export of screened synthetic receipts and their matching captures.
Never exports custom-source runs, credentials, .local, Codex config or raw native recordings.
"""
from __future__ import annotations
import argparse,csv,hashlib,io,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from jevkit.web_server import records
from jevkit.security import canonical,private_dir,load_json,SafeError

def main():
    p=argparse.ArgumentParser();p.add_argument('--include-captures',action='store_true');a=p.parse_args()
    rs=records();by_id={r['run_id']:r for r in rs}
    if not rs:raise SafeError('NO_EXPORTABLE_EVIDENCE')
    dest=ROOT/'artifacts'/'exports';private_dir(dest);out=dest/'evidence-bundle.zip'
    items={f'runs/{r["run_id"]}.json':canonical(r)+b'\n' for r in rs}
    if a.include_captures:
        for mp in (ROOT/'artifacts'/'captures').glob('*/*/capture-manifest.json'):
            if mp.is_symlink() or any(p.is_symlink() for p in mp.parents if p!=ROOT.parent):continue
            m=load_json(mp)
            if m.get('run_id') not in by_id or m.get('data_classification')!='synthetic':continue
            if m.get('source_mode')!=by_id[m['run_id']]['mode']:continue
            for name,digest in m.get('files',{}).items():
                if name not in ('overview.png','recorded-evidence.webm'):continue
                file=mp.parent/name
                if file.is_symlink() or not file.is_file():continue
                data=file.read_bytes()
                if hashlib.sha256(data).hexdigest()!=digest:raise SafeError('CAPTURE_HASH_MISMATCH')
                items[str(file.relative_to(ROOT/'artifacts'))]=data
            items[str(mp.relative_to(ROOT/'artifacts'))]=canonical(m)
            rm=mp.parent/'reel-manifest.json'
            if rm.exists() and not rm.is_symlink():
                rmeta=load_json(rm);rf=mp.parent/'reel-source.mp4'
                if rf.is_file() and not rf.is_symlink() and rmeta.get('sha256')==hashlib.sha256(rf.read_bytes()).hexdigest():
                    items[str(rf.relative_to(ROOT/'artifacts'))]=rf.read_bytes();items[str(rm.relative_to(ROOT/'artifacts'))]=canonical(rmeta)
    ledger=io.StringIO();writer=csv.writer(ledger);writer.writerow(['case_id','run_id','origin','model','policy','usable_claim','publication_review'])
    for r in rs:
        claim='Offline fixture exercised local policy' if r['mode']=='fixture' else 'Recorded API returned this result on synthetic input'
        writer.writerow([r['case_id'],r['run_id'],r['mode'],r['model_resolved'],r['policy']['status'],claim,'REQUIRED'])
    items['claim-ledger.csv']=ledger.getvalue().encode()
    items['READ-ME-FIRST.md']=b'# Evidence hand-back\n\nThis is NOT a production benchmark. Fixture results are simulated. Live results are actual API receipts on synthetic data. Native Codex recording and custom enterprise data are excluded. Review all frames and your early-access publication terms before publishing.\n'
    manifest={'schema_version':1,'files':{k:hashlib.sha256(v).hexdigest() for k,v in items.items()},
        'fixture_runs':sum(r['mode']=='fixture' for r in rs),'live_runs':sum(r['mode']=='live' for r in rs),
        'custom_runs_exported':0,'publication_review_required':True}
    items['MANIFEST.json']=canonical(manifest)
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in sorted(items.items()):z.writestr(name,data)
    out.chmod(0o600)
    print(json.dumps({'file':'artifacts/exports/evidence-bundle.zip','files':len(items),'publication_review_required':True},indent=2))
if __name__=='__main__':
    try:main()
    except SafeError as e:print(str(e),file=sys.stderr);sys.exit(2)
    except Exception:print('EXPORT_FAILED',file=sys.stderr);sys.exit(3)
