#!/usr/bin/env python3
"""Auto for enrolled workspaces; preserve 1.1.2 behavior for unenrolled workspaces."""
from __future__ import annotations
import json,os,sys
from pathlib import Path

def main():
    plugin=Path(os.environ.get('PLUGIN_ROOT',Path(__file__).resolve().parents[1]))
    runtime=plugin/'runtime'
    if not runtime.is_dir():return 0
    sys.path.insert(0,str(runtime))
    try:
        raw=sys.stdin.buffer.read(512_001)
        if len(raw)>512000:return 0
        event=json.loads(raw)
        from jev_auto.settings import load_policy
        from jev_auto.common import workspace
        auto=False
        try:
            if isinstance(event.get('cwd'),str):load_policy(workspace(event['cwd']));auto=True
        except Exception:pass
        if auto:
            from jev_auto.hooks import handle
            result=handle(event)
        else:
            from jevkit.policy_mode import handle_hook_event,policy_mode
            data=Path(os.environ.get('PLUGIN_DATA',Path.home()/'.local'/'state'/'jev-control'))
            try:result=handle_hook_event(event,data_root=data)
            except Exception:
                result={'decision':'block','reason':'Legacy enforce could not validate its policy.'} if policy_mode()=='enforce' and event.get('hook_event_name')=='UserPromptSubmit' else None
        if result is not None:print(json.dumps(result,ensure_ascii=True,allow_nan=False,separators=(',',':')))
    except Exception:pass
    return 0
if __name__=='__main__':raise SystemExit(main())
