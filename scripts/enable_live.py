#!/usr/bin/env python3
"""Human-created, expiring permission; not an authorization bypass for the agent."""
import argparse,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from jevkit.engine import ROOT
from jevkit.runtime import PROJECT_LIVE,RuntimeContext
from jevkit.providers import resolve_provider
from jevkit.security import SafeError, load_json
p=argparse.ArgumentParser();p.add_argument('--calls',type=int,default=5);p.add_argument('--minutes',type=int,default=30);p.add_argument('--allow-custom',action='store_true');p.add_argument('--case-id');p.add_argument('--state',type=Path);p.add_argument('--request-id');p.add_argument('--data-classification',choices=['public','internal-minimized']);p.add_argument('--revoke',action='store_true');p.add_argument('--state-root',type=Path);p.add_argument('--workspace',type=Path,required=True);a=p.parse_args()
try:
    context=RuntimeContext(ROOT,a.state_root,PROJECT_LIVE,a.workspace)
    if a.revoke:context.revoke_live_grant();print('Live permission revoked.');sys.exit(0)
    required_custom=(a.case_id,a.state,a.request_id,a.data_classification)
    if a.allow_custom and not all(required_custom):
        raise SafeError('REQUEST_GRANT_REQUIRED: custom grants need case, state, request ID, and classification')
    if not a.allow_custom and any(required_custom):
        raise SafeError('CUSTOM_DATA_NOT_AUTHORIZED: remove custom grant arguments or add --allow-custom')
    if not sys.stdin.isatty():raise SafeError('PRIVATE_TERMINAL_REQUIRED: the human must authorize live use')
    provider=resolve_provider()
    print(f'Authorize at most {a.calls} HTTP attempts for {a.minutes} minutes. Retries consume attempts.')
    print(f'{provider.display_name} receives the text state and questions using model {provider.model}.')
    print('This is an API call limit, NOT a dollar or account-wide billing cap. Changing provider invalidates this grant.')
    print('Custom data is '+('ALLOWED; you are responsible for minimization and authorization.' if a.allow_custom else 'BLOCKED; only the supplied synthetic fixtures may be sent.'))
    if input('Type AUTHORIZE to continue: ').strip()!='AUTHORIZE':raise SafeError('CANCELED')
    custom_state=load_json(a.state) if a.state else None
    context.create_live_grant(a.calls,a.minutes,a.allow_custom,case_id=a.case_id,
        state=custom_state,request_id=a.request_id,data_classification=a.data_classification);print('Expiring workspace-scoped local permission granted.')
except SafeError as e:print(str(e),file=sys.stderr);sys.exit(2)
