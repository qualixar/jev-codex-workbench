#!/usr/bin/env python3
"""Run the isolated demo's actual tests and bind evidence to the source revision.
Never executes commands supplied by Jev or arbitrary user strings.
"""
from __future__ import annotations
import ast,hashlib,json,re,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from jevkit.security import canonical,private_json,screen,SafeError

def collect(root=ROOT):
    folder=root/'demo_project'
    paths=[folder/'cache.py',folder/'test_cache.py']
    for p in paths:
        if p.is_symlink() or not p.is_file():raise SafeError('UNSAFE_DEMO_SOURCE')
    before={p.name:p.read_text() for p in paths}
    tested_hash=hashlib.sha256(canonical(before)).hexdigest()
    start=time.monotonic()
    result=subprocess.run([sys.executable,'-m','unittest','-v','test_cache.py'],cwd=folder,text=True,capture_output=True,timeout=20)
    syntax_exit=0
    try:
        for name,source in before.items():ast.parse(source,filename=name)
    except SyntaxError:syntax_exit=1
    after={p.name:p.read_text() for p in paths}
    source_hash=hashlib.sha256(canonical(after)).hexdigest()
    output=(result.stdout+'\n'+result.stderr).replace(str(root),'[PROJECT_ROOT]')
    m=re.search(r'Ran (\d+) tests? in',output)
    state={'requirement':'A cached value must be absent at OR after its expiry instant; fresh values still work and negative TTL is rejected.',
        'diff_summary':'Current demo implementation and test source, collected directly from disk:\n'+canonical(after).decode(),
        'evidence':{'test_exit_code':result.returncode,'lint_exit_code':syntax_exit,
        'lint_scope':'Python AST syntax check only; NOT a comprehensive linter or security review.',
        'tests_executed':int(m.group(1)) if m else 0,'source_hash':source_hash,'tested_source_hash':tested_hash,
        'age_seconds':round(time.monotonic()-start,3),'test_summary':output,
        'collector':'Fixed unittest command in the isolated demonstration folder; local receipt, not tamper-proof attestation.'}}
    _,findings=screen(state)
    if findings:raise SafeError('DEMO_OUTPUT_NEEDS_PRIVATE_REVIEW')
    private_json(root/'.local'/'demo-state.json',state)
    return {'state_file':'.local/demo-state.json','test_exit_code':result.returncode,'tests_executed':state['evidence']['tests_executed'],
        'source_hash':source_hash,'source_unchanged_during_tests':source_hash==tested_hash,
        'next':'Inspect test result. Submit freshly collected state only after approving custom-source API use.'}

if __name__=='__main__':
    try:print(json.dumps(collect(),indent=2))
    except SafeError as e:print(str(e),file=sys.stderr);sys.exit(2)
    except Exception:print('DEMO_COLLECTION_FAILED',file=sys.stderr);sys.exit(3)
