#!/usr/bin/env python3
"""Capture real browser renderings of recorded evidence. Never records native Codex."""
from __future__ import annotations
import argparse,hashlib,json,shutil,sys,threading,time
from pathlib import Path
from urllib.parse import urlencode
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from jevkit.engine import catalog
from jevkit.web_server import make_server,records
from jevkit.security import SafeError,private_json,private_dir

def main():
    p=argparse.ArgumentParser();p.add_argument('--case',default='08-completion-gate');p.add_argument('--mode',choices=['fixture','live'],default='fixture');p.add_argument('--variant',choices=['nominal','adversarial','uncertain'],default='nominal');p.add_argument('--orientation',choices=['landscape','portrait','both'],default='both');p.add_argument('--seconds',type=int,default=8);p.add_argument('--browser-binary',type=Path);p.add_argument('--offline-render',action='store_true',help='Render local HTML + recorded JSON without browser network access. Clearly labeled snapshot.');a=p.parse_args()
    if not 1<=a.seconds<=30:raise SafeError('INVALID_CAPTURE_DURATION')
    try:from playwright.sync_api import sync_playwright
    except ImportError:raise SafeError('CAPTURE_DEPENDENCY_MISSING: use the approved optional install helper') from None
    ids=[c['id'] for c in catalog()] if a.case=='all' else [a.case]
    if any(cid not in {c['id'] for c in catalog()} for cid in ids):raise SafeError('UNKNOWN_CASE')
    selected=[]
    for cid in ids:
        rs=[r for r in records() if r['case_id']==cid and r['mode']==a.mode and r['variant']==a.variant]
        if not rs:raise SafeError('NO_MATCHING_RUN: execute the workflow first; capture never fabricates receipts')
        selected.append(sorted(rs,key=lambda r:r['recorded_utc'],reverse=True)[0])
    server=make_server(0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}'
    manifest=[]
    try:
        with sync_playwright() as pw:
            options={}
            if a.browser_binary:
                if not a.browser_binary.is_file():raise SafeError('INVALID_BROWSER_BINARY')
                options['executable_path']=str(a.browser_binary.resolve())
            browser=pw.chromium.launch(**options)
            for r in selected:
                for orientation in (['landscape','portrait'] if a.orientation=='both' else [a.orientation]):
                    size={'width':1920,'height':1080} if orientation=='landscape' else {'width':1080,'height':1920}
                    folder=ROOT/'artifacts'/'captures'/r['run_id']/orientation;private_dir(folder)
                    context=browser.new_context(viewport=size,record_video_dir=str(folder),record_video_size=size,
                        reduced_motion='reduce',service_workers='block')
                    context.route('**/*',lambda route:route.continue_() if route.request.url.startswith(base+'/') else route.abort())
                    page=context.new_page();video=page.video
                    url=base+'/#'+urlencode({'case':r['case_id'],'mode':a.mode,'variant':a.variant})
                    if a.offline_render:
                        html=(ROOT/'web'/'index.html').read_text().replace('<link rel="stylesheet" href="/styles.css">','').replace('<script defer src="/app.js"></script>','')
                        page.set_content(html)
                        page.add_style_tag(content=(ROOT/'web'/'styles.css').read_text())
                        page.evaluate('(data) => window.__WORKBENCH_SNAPSHOT__ = data',{'catalog':catalog(),'runs':records()})
                        page.evaluate('(hash) => location.hash = hash',url.split('#')[1])
                        page.add_script_tag(content=(ROOT/'web'/'app.js').read_text())
                    else:
                        page.goto(url)
                    page.wait_for_function('(id) => document.body.dataset.runId === id',arg=r['run_id'],timeout=10000)
                    page.screenshot(path=str(folder/'overview.png'),full_page=False)
                    page.wait_for_timeout(a.seconds*1000)
                    context.close();source=Path(video.path());destination=folder/'recorded-evidence.webm'
                    if destination.exists():destination.unlink()
                    source.rename(destination)
                    item={'case_id':r['case_id'],'run_id':r['run_id'],'source_mode':a.mode,'data_classification':'synthetic',
                        'orientation':orientation,'offline_snapshot':a.offline_render,'capture_kind':'browser replay of a stored receipt, NOT native Codex and NOT a new model call',
                        'provenance_label':r['provenance_label'],'requested_hold_seconds':a.seconds,
                        'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (folder/'overview.png',destination)}}
                    private_json(folder/'capture-manifest.json',item);manifest.append(item)
            browser.close()
    finally:server.shutdown();server.server_close()
    print(json.dumps({'captures':manifest,'publication_review_required':True},indent=2))
if __name__=='__main__':
    try:main()
    except SafeError as e:print(str(e),file=sys.stderr);sys.exit(2)
    except Exception:print('CAPTURE_FAILED: check installed Playwright/Chromium and rerun. No live data was fabricated.',file=sys.stderr);sys.exit(3)
