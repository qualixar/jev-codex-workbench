"""Standing permission belongs to a workspace, not to its current Git status."""
from __future__ import annotations
import time, uuid
from pathlib import Path
from urllib.parse import urlsplit
from .common import AutoError, canonical, number, read_private, state_dir, workspace, workspace_id, write_private

PROVIDERS=('typesafe','openrouter','laya-mlx')
DEFAULTS={
 'schema_version':1,'version':'1.1.3','enabled':True,
 'max_calls_per_day':1000,'max_bytes_per_day':20_000_000,'max_request_bytes':48_000,
 'timeout_seconds':12,'cache_seconds':600,'retention_days':7,
 'drop_probability':0.10,'min_reduction':0.20,'min_chars':2000,
 'max_blocks':48,'block_lines':25,'native_output_rewrite':True,
 'prepare_context':True,'browser_origins':[],'browser_max_steps':10,
 'data_classification':'public','case_ids':[],
 'local_recipe_ids':['sieve','prepare','browser','probe'],
}

def make_policy(path, provider, days=30, **overrides):
    if provider not in PROVIDERS or not isinstance(days,int) or not 1<=days<=365: raise AutoError('POLICY_CONFIG')
    p={**DEFAULTS,**overrides,'workspace_id':workspace_id(path),'provider':provider,
       'policy_id':uuid.uuid4().hex,'expires_at':time.time()+days*86400}
    validate_policy(p,path); return p

def validate_policy(p,path,now=None):
    now=time.time() if now is None else now
    if not isinstance(p,dict) or p.get('schema_version')!=1 or p.get('provider') not in PROVIDERS: raise AutoError('POLICY_CONFIG')
    if p.get('workspace_id') != workspace_id(path): raise AutoError('POLICY_WORKSPACE_MISMATCH')
    if p.get('enabled') is not True or not number(p.get('expires_at'),0,10**12) or p['expires_at']<=now: raise AutoError('AUTO_DISABLED_OR_EXPIRED')
    for name,lo,hi in [('max_calls_per_day',1,100_000),('max_bytes_per_day',1000,10**10),('max_request_bytes',1000,100_000),('max_blocks',1,48),('block_lines',1,100),('min_chars',500,100_000),('browser_max_steps',1,30),('retention_days',1,30)]:
        if not isinstance(p.get(name),int) or isinstance(p[name],bool) or not lo<=p[name]<=hi: raise AutoError('POLICY_RANGE')
    for name,lo,hi in [('timeout_seconds',1,30),('cache_seconds',0,3600),('drop_probability',0,.2),('min_reduction',0,1)]:
        if not number(p.get(name),lo,hi): raise AutoError('POLICY_RANGE')
    if p.get('data_classification') not in ('public','internal-minimized'): raise AutoError('DATA_CLASSIFICATION')
    for name in ('native_output_rewrite','prepare_context'):
        if not isinstance(p.get(name),bool): raise AutoError('POLICY_BOOLEAN')
    for name in ('case_ids','local_recipe_ids','browser_origins'):
        if not isinstance(p.get(name),list) or len(p[name])>100 or not all(isinstance(x,str) for x in p[name]): raise AutoError('POLICY_LIST')
    for value in p['browser_origins']:
        u=urlsplit(value)
        if u.scheme not in ('http','https') or not u.hostname or u.username or u.password or u.path not in ('','/') or u.query or u.fragment: raise AutoError('BROWSER_ORIGIN')
    routes=p.get('routes',{})
    if not isinstance(routes,dict) or any(not isinstance(k,str) or v not in PROVIDERS for k,v in routes.items()):raise AutoError('POLICY_ROUTES')
    if len(canonical(p))>16_000: raise AutoError('POLICY_SIZE')
    return p

def load_policy(path,base=None):
    f=state_dir(path,base)/'policy.json'
    try: p=read_private(f,16_000)
    except FileNotFoundError: raise AutoError('WORKSPACE_NOT_ENROLLED') from None
    return validate_policy(p,path)

def save_policy(path,p,base=None):
    validate_policy(p,path); write_private(state_dir(path,base)/'policy.json',p)

def revoke(path,base=None):
    f=state_dir(path,base)/'policy.json'
    p=read_private(f,16_000);p['enabled']=False;write_private(f,p)
