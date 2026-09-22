"""Compatibility facade: existing tools stay available; automatic calls return compact data."""
from __future__ import annotations
import json,sys
from pathlib import Path
from .common import AutoError,canonical,decode
from .ipc import ensure,request
from .settings import load_policy

VERSIONS=('2025-11-25','2025-06-18','2025-03-26','2024-11-05')

def definitions(legacy):
    tools=legacy.tools(scope='global-hybrid')
    for t in tools:
        if t['name']=='jev_evaluate':
            t['description']='Evaluate one approved case using enrolled workspace authority. No per-request grant is needed in Jev Auto. Return a compact recommendation and local receipt ID, never execution authority.'
            t['inputSchema'].pop('allOf',None);t['inputSchema']['required']=['case_id','workspace_path','state']
    def tool(name,description,props,required):
        return {'name':name,'description':description,'inputSchema':{'type':'object','properties':props,'required':required,'additionalProperties':False}}
    wp={'type':'string','minLength':1,'maxLength':4096};goal={'type':'string','minLength':1,'maxLength':4000}
    tools += [
      tool('jev_auto_status','Report this workspace\'s Auto status and actual counters; never infer host token savings.',{'workspace_path':wp},['workspace_path']),
      tool('jev_prepare','Prepare a compact file/optional-guidance shortlist for a narrow task. Mandatory instructions and SLM are unchanged.',{'workspace_path':wp,'goal':goal},['workspace_path','goal']),
      tool('jev_reduce','Select relevant blocks from supplied text, keeping omissions exactly recoverable. Never pass secrets.',{'workspace_path':wp,'goal':goal,'text':{'type':'string','maxLength':100000}},['workspace_path','goal','text']),
      tool('jev_recall','Fetch a local receipt or exact omitted line range. No model inference or cloud request.',{'workspace_path':wp,'receipt_id':{'type':'string','pattern':'^[a-f0-9]{64}$'},'start':{'type':'integer','minimum':1},'end':{'type':'integer','minimum':1}},['workspace_path','receipt_id']),
    ]
    return tools

def dispatch(name,args,legacy,caller=None):
    if not isinstance(args,dict):raise AutoError('MCP_ARGUMENTS')
    known={t['name']:t for t in definitions(legacy)}
    if name not in known:raise AutoError('MCP_TOOL_NAME')
    schema=known[name]['inputSchema']
    if set(args)-set(schema['properties']) or set(schema.get('required',[]))-set(args):raise AutoError('MCP_ARGUMENTS')
    for k,v in args.items():
        spec=schema['properties'][k];kind=spec.get('type')
        if kind=='string' and (not isinstance(v,str) or len(v)<spec.get('minLength',0) or len(v)>spec.get('maxLength',100000)):raise AutoError('MCP_ARGUMENT_TYPE')
        if kind=='integer' and (not isinstance(v,int) or isinstance(v,bool) or v<spec.get('minimum',0)):raise AutoError('MCP_ARGUMENT_TYPE')
        if kind=='object' and not isinstance(v,dict):raise AutoError('MCP_ARGUMENT_TYPE')
        if 'enum' in spec and v not in spec['enum']:raise AutoError('MCP_ARGUMENT_ENUM')
    path=args.get('workspace_path')
    auto_names={'jev_auto_status','jev_prepare','jev_reduce','jev_recall'}
    if name in auto_names or name=='jev_evaluate':
        if caller is None:
            try:ensure(path)
            except AutoError as error:
                if name=='jev_evaluate' and str(error)=='WORKSPACE_NOT_ENROLLED':return legacy.call(name,args,scope='global-hybrid')
                raise
        call=caller or (lambda obj:request(path,obj))
        if name=='jev_auto_status':return {'health':call({'op':'health'}),'usage':call({'op':'stats'})}
        if name=='jev_prepare':return call({'op':'prepare','goal':args['goal']})
        if name=='jev_reduce':return call({'op':'sieve','goal':args['goal'],'text':args['text'],'tool':'explicit_reduce'})
        if name=='jev_recall':return call({'op':'recall','receipt_id':args['receipt_id'],'start':args.get('start',1),'end':args.get('end',120)})
        return call({'op':'evaluate','case_id':args['case_id'],'state':args['state']})
    return legacy.call(name,args,scope='global-hybrid')

def serve():
    from jevkit import mcp_server as legacy
    initialized=False
    while True:
        line=sys.stdin.buffer.readline(512_001)
        if not line:break
        rid=None
        try:
            if not line.endswith(b'\n') and len(line)>512000:raise AutoError('MCP_MESSAGE_SIZE')
            req=decode(line)
            if not isinstance(req,dict) or req.get('jsonrpc')!='2.0':raise AutoError('MCP_REQUEST')
            if 'id' not in req:continue
            rid=req['id'];method=req.get('method');params=req.get('params') or {}
            if not isinstance(params,dict):raise AutoError('MCP_PARAMS')
            if method=='initialize':
                v=params.get('protocolVersion');initialized=True
                result={'protocolVersion':v if v in VERSIONS else VERSIONS[0],
                        'serverInfo':{'name':'qualixar-jev','version':'1.1.3'},'capabilities':{'tools':{'listChanged':False}},
                        'instructions':'Enrolled workspaces use standing Jev Auto authority. Use compact recommendations; detailed receipts are local. Preserve SLM and the existing browser. Never create grants yourself.'}
            elif method=='ping':result={}
            elif not initialized:raise AutoError('MCP_INITIALIZE_FIRST')
            elif method=='tools/list':result={'tools':definitions(legacy)}
            elif method=='tools/call':
                try:
                    output=dispatch(params.get('name'),params.get('arguments',{}),legacy)
                    result={'content':[{'type':'text','text':canonical(output).decode()}],'isError':False}
                except Exception as e:
                    safe=str(e) if isinstance(e,AutoError) else 'JEV_TOOL_UNAVAILABLE'
                    result={'content':[{'type':'text','text':safe}],'isError':True}
            else:
                print(json.dumps({'jsonrpc':'2.0','id':rid,'error':{'code':-32601,'message':'Method not found'}}),flush=True);continue
            out={'jsonrpc':'2.0','id':rid,'result':result}
        except AutoError as e:out={'jsonrpc':'2.0','id':rid,'error':{'code':-32602,'message':str(e)}}
        except Exception:out={'jsonrpc':'2.0','id':rid,'error':{'code':-32603,'message':'Internal error'}}
        print(canonical(out).decode(),flush=True)
