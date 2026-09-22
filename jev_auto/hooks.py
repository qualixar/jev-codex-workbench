"""Codex-specific hook adapter. Unsupported/missing data leaves ordinary work intact."""
from __future__ import annotations
import json,sys
from pathlib import Path
from .common import AutoError, decode, workspace
from .settings import load_policy
from .ipc import ensure,request
from .sieve import PROTECTED

def plain_output(event):
    response=event.get('tool_response')
    if isinstance(response,str):return response
    if isinstance(response,dict):
        if response.get('isError') or response.get('exit_code',0) not in (0,None):return None
        for name in ('output','stdout','text'):
            if isinstance(response.get(name),str):return response[name]
    return None

def handle(event,base=None,caller=None,starter=None):
    if not isinstance(event,dict):return None
    name=event.get('hook_event_name');cwd=event.get('cwd')
    if not isinstance(cwd,str):return None
    try:
        path=workspace(cwd);p=load_policy(path,base)
        if name=='PreToolUse':return None
        (starter or ensure)(path,base)
    except (AutoError,OSError):return None
    call=caller or (lambda path,obj:request(path,obj,base,timeout=p['timeout_seconds']+5))
    session=event.get('session_id') or event.get('turn_id')
    try:
        if name=='SessionStart':
            call(path,{'op':'prepare_runtime'})
            return {'hookSpecificOutput':{'hookEventName':name,'additionalContext':'Jev Auto 1.1.3 is enrolled here. Eligible decisions use the standing budget; do not request per-turn grants. Preserve SLM and the existing Computer Use skill.'}}
        if name=='UserPromptSubmit' and isinstance(session,str):
            goal=event.get('prompt','')
            call(path,{'op':'set_goal','session':session,'goal':goal})
            result=call(path,{'op':'prepare','goal':goal})
            if result.get('packet'):return {'hookSpecificOutput':{'hookEventName':name,'additionalContext':result['packet']}}
        if name=='SubagentStart':
            return {'hookSpecificOutput':{'hookEventName':name,'additionalContext':'Use this workspace\'s Jev Auto service and shared budget. Pass your narrow goal explicitly to jev_prepare or jev_reduce. Do not create grants, copy full receipts, or alter SLM.'}}
        if name=='PreToolUse':return None  # no extra model call before every command
        if name=='PostToolUse' and p['native_output_rewrite']:
            # A tool result may contain confidential prose that pattern matching
            # cannot recognize. Automatic reduction is local-only.
            if p.get('routes',{}).get('sieve',p['provider'])!='laya-mlx':return None
            tool=event.get('tool_name','')
            # Never rewrite machine-consumed MCP objects or the Computer Use script result.
            if tool not in ('Bash','Read','Grep') or PROTECTED.search(str(event.get('tool_input',{}))):return None
            text=plain_output(event)
            if text is None or not isinstance(session,str):return None
            result=call(path,{'op':'sieve','session':session,'text':text,'tool':tool,'tool_input':event.get('tool_input',{})})
            if result.get('changed'):
                # Documented Codex PostToolUse semantics, not Claude's updatedMCPToolOutput.
                return {'continue':False,'stopReason':result['text']}
    except Exception:
        # Optimisation failure must not fail a user's already-authorized task.
        return None
    return None

def main():
    try:
        event=decode(sys.stdin.buffer.read(512_001))
        result=handle(event)
        if result is not None:print(json.dumps(result,ensure_ascii=True,allow_nan=False))
    except Exception:pass
if __name__=='__main__':main()
