"""Human setup once; runtime operations do not ask for a grant on every request."""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
from .common import AutoError, canonical, home_root, read_private, state_dir, workspace, write_private
from .settings import make_policy,save_policy,load_policy,revoke
from .ipc import address,ensure,request

def bridge_record(path,p):
    root=Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))/'qualixar-jev-control'
    f=root/'auto-bridge.json'
    try:data=read_private(f,100_000)
    except FileNotFoundError:data={'schema_version':1,'workspaces':{}}
    data['workspaces'][str(workspace(path))]={'socketPath':str(address(path)),'allowedOrigins':p['browser_origins'],
                                          'maxSteps':p['browser_max_steps']}
    write_private(f,data)

def main(argv=None):
    parser=argparse.ArgumentParser(description='Qualixar Jev Auto 1.1.3')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('mcp')
    en=sub.add_parser('enroll');en.add_argument('--workspace',required=True);en.add_argument('--provider',choices=['existing','typesafe','openrouter','laya-mlx'],default='existing')
    en.add_argument('--days',type=int,default=30);en.add_argument('--daily-calls',type=int,default=1000);en.add_argument('--daily-bytes',type=int,default=20_000_000)
    en.add_argument('--classification',choices=['public','internal-minimized'],default='public');en.add_argument('--browser-origin',action='append',default=[])
    for name in ('status','start','stop','revoke','warmup','stats','bridge-config'):
        p=sub.add_parser(name);p.add_argument('--workspace',required=True)
    route=sub.add_parser('route-local');route.add_argument('--workspace',required=True);route.add_argument('--recipe',action='append',choices=['sieve','prepare','browser','probe'],default=[])
    recall=sub.add_parser('recall');recall.add_argument('--workspace',required=True);recall.add_argument('--receipt-id',required=True);recall.add_argument('--start',type=int,default=1);recall.add_argument('--end',type=int,default=120)
    probe=sub.add_parser('probe');probe.add_argument('--workspace',required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='mcp':
            from .mcp import serve
            serve();return 0
        path=workspace(args.workspace)
        if args.command in ('enroll','route-local'):
            if not sys.stdin.isatty():raise AutoError('PRIVATE_TERMINAL_SETUP_REQUIRED')
        if args.command=='enroll':
            provider=args.provider
            if provider=='existing':
                from jevkit.providers import resolve_provider
                provider=resolve_provider().provider_id
            from jevkit.engine import catalog
            p=make_policy(path,provider,args.days,max_calls_per_day=args.daily_calls,
                max_bytes_per_day=args.daily_bytes,data_classification=args.classification,
                browser_origins=args.browser_origin,case_ids=[c['id'] for c in catalog()])
            if provider=='laya-mlx':p['mlx']=read_private(home_root()/'mlx-installation.json',100_000)
            print('One-time workspace enrollment. Applies to reviewed workspace data, not the entire computer.')
            print('Provider:',provider,'Days:',args.days,'Maximum attempts/day:',args.daily_calls)
            print('No per-turn grants. Native Codex/browser permissions stay unchanged. Same-user local controls are not tamper-proof.')
            if input('Type ENABLE to activate: ').strip()!='ENABLE':raise AutoError('SETUP_CANCELLED')
            save_policy(path,p);bridge_record(path,p);ensure(path)
            print('Jev Auto enabled. Restart Codex after plugin update and review changed hooks once.');return 0
        if args.command=='route-local':
            p=load_policy(path);p['mlx']=read_private(home_root()/'mlx-installation.json',100_000)
            if not args.recipe:raise AutoError('SELECT_LOCAL_RECIPE')
            print('Local routes:',','.join(args.recipe),'No automatic cloud fallback for these recipes.')
            if input('Type LOCAL to activate: ').strip()!='LOCAL':raise AutoError('SETUP_CANCELLED')
            p.setdefault('routes',{}).update({r:'laya-mlx' for r in args.recipe});save_policy(path,p)
            ensure(path);print(canonical(request(path,{'op':'warmup'},timeout=130)).decode());return 0
        if args.command=='revoke':
            revoke(path)
            try:request(path,{'op':'shutdown'})
            except AutoError:pass
            print('Further Auto requests disabled. Existing native Codex use is unchanged.');return 0
        if args.command=='stop':print(canonical(request(path,{'op':'shutdown'})).decode());return 0
        if args.command=='status':
            try:
                p=load_policy(path);print(canonical({'enrolled':True,'provider':p['provider'],'routes':p.get('routes',{}),'expires_at':p['expires_at']}).decode())
            except AutoError:print('{"enrolled":false}')
            return 0
        ensure(path)
        if args.command=='bridge-config':print('Browser connection is registered; bridge loadConfig() reads it without API keys.');return 0
        if args.command=='start':print(canonical(request(path,{'op':'health'})).decode());return 0
        if args.command=='warmup':print(canonical(request(path,{'op':'warmup'},timeout=130)).decode());return 0
        if args.command=='stats':print(canonical(request(path,{'op':'stats'})).decode());return 0
        if args.command=='recall':print(canonical(request(path,{'op':'recall','receipt_id':args.receipt_id,'start':args.start,'end':args.end})).decode());return 0
        if args.command=='probe':
            # A live/synthetic request; never a substituted fixture response.
            result=request(path,{'op':'probe'})
            print(canonical(result).decode());return 0
    except AutoError as e:print(str(e),file=sys.stderr);return 2
    except Exception:print('SETUP_OR_RUNTIME_FAILURE: details suppressed; run the supplied local tests.',file=sys.stderr);return 2
    return 0
