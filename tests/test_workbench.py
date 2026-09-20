from __future__ import annotations
import copy,io,json,os,shutil,subprocess,sys,tempfile,threading,time,unittest,urllib.error,urllib.request
from pathlib import Path
from unittest.mock import patch
from jevkit.engine import ROOT,catalog,spec,fixture,questions_for,simulated_response,run,policy
from jevkit.credentials import get_credential
from jevkit.security import SafeError,screen,canonical,load_json,private_json
from jevkit.contract import validate_questions,validate_response
from jevkit.authorization import CallBudget
from jevkit.client import evaluate,retry_delay,NoRedirect
from jevkit.mcp_server import call,tools
from jevkit.providers import provider_profile
from jevkit.web_server import make_server

def provider_budget(path: Path) -> CallBudget:
    profile=provider_profile('typesafe')
    return CallBudget(path,provider_id=profile.provider_id,
                      provider_profile_sha256=profile.profile_sha256)

class FixtureContracts(unittest.TestCase):pass
for c in catalog():
    for variant in ('nominal','adversarial','uncertain'):
        def test(self,cid=c['id'],v=variant):
            result=run(cid,v,persist=False)
            self.assertTrue(result['fixture_contract_passed'])
            self.assertFalse(result['policy']['execution_authorized'])
            self.assertEqual(result['model_resolved'],'fixture-not-a-model')
            self.assertIsNone(result['usage'])
            self.assertIn('NOT LIVE JEV',result['provenance_label'])
        setattr(FixtureContracts,'test_'+c['id'].replace('-','_')+'_'+variant,test)

class Safety(unittest.TestCase):
    def test_secret_field_redacted(self):
        output,found=screen({'password':'synthetic-password-only'})
        self.assertEqual(output['password'],'[REDACTED:CREDENTIAL]');self.assertIn('CREDENTIAL',found)
    def test_email_redacted(self):
        output,found=screen('A contact at demo'+'@'+'example.org')
        self.assertEqual(output,'A contact at [REDACTED:EMAIL]')
    def test_known_opaque_secret_redacted(self):
        key='this-is-a-synthetic-test-secret';output,found=screen('hello '+key,(key,));self.assertNotIn(key,output)
    def test_openrouter_key_format_redacted(self):
        key='sk-or-v1-'+'A'*48
        output,found=screen('token='+key)
        self.assertNotIn(key,output);self.assertIn('API_KEY',found)
    def test_provider_specific_secret_fields_redacted(self):
        output,found=screen({'OPENROUTER_API_KEY':'synthetic-openrouter-key',
                             'TYPESAFE_API_KEY':'synthetic-typesafe-key'})
        self.assertEqual(output['OPENROUTER_API_KEY'],'[REDACTED:CREDENTIAL]')
        self.assertEqual(output['TYPESAFE_API_KEY'],'[REDACTED:CREDENTIAL]')
        self.assertIn('CREDENTIAL',found)
    def test_private_url_redacted(self):
        value,found=screen('https://'+'service.internal'+'/demo');self.assertIn('PRIVATE_URL',found)
    def test_json_nan_rejected(self):
        with self.assertRaises(SafeError):canonical({'v':float('nan')})
    def test_symlink_input_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'real').write_text('{}');(p/'link').symlink_to(p/'real')
            with self.assertRaises(SafeError):load_json(p/'link')
    def test_credential_not_echoed_in_invalid_error(self):
        with patch.dict(os.environ,{'TYPESAFE_API_KEY':'bad\nsynthetic-key'}):
            with self.assertRaises(SafeError) as e:get_credential()
            self.assertNotIn('synthetic-key',str(e.exception))
    def test_outbound_secret_fails_before_transport(self):
        key='local-only-synthetic-secret'
        with tempfile.TemporaryDirectory() as t,patch.dict(os.environ,{'JEV_PROVIDER':'typesafe','TYPESAFE_API_KEY':key}):
            def transport(*a,**k):self.fail('Transport must not be called')
            with self.assertRaisesRegex(SafeError,'OUTBOUND_DATA_BLOCKED'):
                evaluate(Path(t),{'text':key},{'q':{'type':'noul','instructions':'Is this relevant?'}},False,transport=transport)
    def test_fixture_cannot_judge_real_state(self):
        with self.assertRaisesRegex(SafeError,'FIXTURE_CUSTOM_STATE_FORBIDDEN'):
            run('01-skill-routing',state={'request':'a','skills':[]},persist=False)
    def test_unknown_case_rejected(self):
        with self.assertRaises(SafeError):spec('../../anything')
    def test_custom_data_not_in_viewer(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);r=run('01-skill-routing',persist=False);r['data_classification']='user-approved'
            private_json(root/'artifacts'/'runs'/'r.json',r)
            from jevkit.web_server import records
            self.assertEqual(records(root),[])

class ContractValidation(unittest.TestCase):
    def setUp(self):
        self.s=spec('01-skill-routing');self.f=fixture('01-skill-routing');self.q=questions_for(self.s,self.f['state']);self.r=simulated_response(self.q,self.f['mock_values'])
    def test_choice_outside_schema_rejected(self):
        self.r['answers']['decision']['choice']='invented'
        with self.assertRaises(SafeError):validate_response(self.r,self.q)
    def test_missing_answer_rejected(self):
        self.r['answers']={}
        with self.assertRaises(SafeError):validate_response(self.r,self.q)
    def test_extra_answer_rejected(self):
        self.r['answers']['extra']={'type':'noul','noul':1}
        with self.assertRaises(SafeError):validate_response(self.r,self.q)
    def test_probabilities_must_sum_to_one(self):
        self.r['answers']['decision']['probabilities']['testing']=0.5
        with self.assertRaises(SafeError):validate_response(self.r,self.q)
    def test_nan_confidence_rejected(self):
        self.r['answers']['decision']['confidence']=float('nan')
        with self.assertRaises(SafeError):validate_response(self.r,self.q)
    def test_boolean_usage_rejected(self):
        self.r['usage']['input_tokens']=True
        with self.assertRaises(SafeError):validate_response(self.r,self.q)
    def test_noul_has_no_fabricated_confidence(self):
        q={'q':{'type':'noul','instructions':'Is it supported?'}}
        r={'model':'fixture','answers':{'q':{'type':'noul','noul':0.5}},'usage':{'input_tokens':1,'output_tokens':0}}
        self.assertNotIn('confidence',validate_response(r,q)['answers']['q'])
    def test_score_weighted_mean_validated(self):
        s=spec('04-file-ranking');f=fixture('04-file-ranking');q=questions_for(s,f['state']);r=simulated_response(q,f['mock_values'])
        r['answers']['item_0']['score']=0
        with self.assertRaises(SafeError):validate_response(r,q)
    def test_candidates_have_unique_ids(self):
        s=spec('04-file-ranking');state={'query':'a','items':[{'id':'a','text':'x'},{'id':'a','text':'y'}]}
        with self.assertRaisesRegex(SafeError,'DUPLICATE_CANDIDATE'):questions_for(s,state)
    def test_state_required_fields(self):
        with self.assertRaises(SafeError):questions_for(self.s,{})
    def test_request_size_limit(self):
        with self.assertRaises(SafeError):questions_for(self.s,{'request':'x'*30000,'skills':[]})

class GateBehavior(unittest.TestCase):
    def state_and_answers(self):
        s=spec('08-completion-gate');f=fixture(s['id']);q=questions_for(s,f['state']);a=simulated_response(q,f['mock_values'])['answers'];return s,f['state'],a
    def test_failed_tests_block_even_model_positive(self):
        s,state,a=self.state_and_answers();state['evidence']['test_exit_code']=1;self.assertEqual(policy(s,state,a)['status'],'BLOCK')
    def test_stale_revision_blocks(self):
        s,state,a=self.state_and_answers();state['evidence']['source_hash']='new';self.assertEqual(policy(s,state,a)['status'],'BLOCK')
    def test_old_receipt_blocks(self):
        s,state,a=self.state_and_answers();state['evidence']['age_seconds']=1000;self.assertEqual(policy(s,state,a)['status'],'BLOCK')
    def test_zero_tests_blocks(self):
        s,state,a=self.state_and_answers();state['evidence']['tests_executed']=0;self.assertEqual(policy(s,state,a)['status'],'BLOCK')
    def test_boolean_exit_code_blocks(self):
        s,state,a=self.state_and_answers();state['evidence']['test_exit_code']=False;self.assertEqual(policy(s,state,a)['status'],'BLOCK')
    def test_missing_lint_evidence_blocks(self):
        s,state,a=self.state_and_answers();del state['evidence']['lint_exit_code'];self.assertEqual(policy(s,state,a)['status'],'BLOCK')
    def test_uncertain_gate_goes_to_review(self):
        self.assertEqual(run('08-completion-gate','uncertain',persist=False)['policy']['status'],'REVIEW')

class BudgetsAndHTTP(unittest.TestCase):
    def test_explicit_grant_required(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(SafeError,'LIVE_NOT_AUTHORIZED'):CallBudget(Path(t)).reserve(False)
    def test_budget_caps_attempts(self):
        with tempfile.TemporaryDirectory() as t:
            b=CallBudget(Path(t));b.grant(1,1);b.reserve(False)
            with self.assertRaisesRegex(SafeError,'CALL_BUDGET_EXHAUSTED'):b.reserve(False)
    def test_custom_data_needs_separate_grant(self):
        with tempfile.TemporaryDirectory() as t:
            b=CallBudget(Path(t));b.grant(1,1)
            with self.assertRaisesRegex(SafeError,'CUSTOM_DATA_NOT_AUTHORIZED'):b.reserve(True)
    def test_concurrent_budget_is_shared(self):
        with tempfile.TemporaryDirectory() as t:
            b=CallBudget(Path(t));b.grant(3,1);out=[]
            def work():
                try:b.reserve(False);out.append(True)
                except SafeError:out.append(False)
            threads=[threading.Thread(target=work) for _ in range(8)]
            [x.start() for x in threads];[x.join() for x in threads]
            self.assertEqual(sum(out),3)
    def test_revoke(self):
        with tempfile.TemporaryDirectory() as t:
            b=CallBudget(Path(t));b.grant(1,1);b.revoke();self.assertFalse(b.status()['enabled'])
    def test_retry_after_clamped(self):self.assertEqual(retry_delay('999',0),20)
    def test_redirect_disabled(self):self.assertIsNone(NoRedirect().redirect_request(None,None,None,None,None,None))
    def test_live_wire_contract_with_mock_transport(self):
        f=fixture('01-skill-routing');q=questions_for(spec(f['case_id']),f['state']);response=simulated_response(q,f['mock_values']);response['model']='jev-1.13.0'
        with tempfile.TemporaryDirectory() as t,patch.dict(os.environ,{'JEV_PROVIDER':'typesafe','TYPESAFE_API_KEY':'synthetic-local-credential'}):
            b=provider_budget(Path(t));b.grant(1,1)
            def transport(req,timeout):
                data=json.loads(req.data);self.assertEqual(set(data),{'model','state','questions'});self.assertNotIn('mock_values',str(data));self.assertEqual(timeout,20)
                return io.BytesIO(json.dumps(response).encode())
            result=evaluate(Path(t),f['state'],q,False,transport=transport)
            self.assertEqual(result['_transport']['attempts'],1);self.assertEqual(b.status()['remaining_calls'],0)
    def test_429_retry_consumes_new_budget_slot(self):
        f=fixture('01-skill-routing');q=questions_for(spec(f['case_id']),f['state']);response=simulated_response(q,f['mock_values']);response['model']='jev-1.13.0';n=[0]
        with tempfile.TemporaryDirectory() as t,patch.dict(os.environ,{'JEV_PROVIDER':'typesafe','TYPESAFE_API_KEY':'synthetic-local-credential'}):
            b=provider_budget(Path(t));b.grant(2,1)
            def transport(req,timeout):
                n[0]+=1
                if n[0]==1:raise urllib.error.HTTPError(req.full_url,429,'rate limit',{'Retry-After':'0'},None)
                return io.BytesIO(json.dumps(response).encode())
            result=evaluate(Path(t),f['state'],q,False,transport=transport,sleep=lambda _:None)
            self.assertEqual(result['_transport']['attempts'],2);self.assertEqual(b.status()['remaining_calls'],0)
    def test_401_no_retry_and_no_error_body(self):
        f=fixture('01-skill-routing');q=questions_for(spec(f['case_id']),f['state']);n=[0]
        with tempfile.TemporaryDirectory() as t,patch.dict(os.environ,{'JEV_PROVIDER':'typesafe','TYPESAFE_API_KEY':'synthetic-local-credential'}):
            b=provider_budget(Path(t));b.grant(3,1)
            def transport(req,timeout):
                n[0]+=1;raise urllib.error.HTTPError(req.full_url,401,'raw-private-description',{},io.BytesIO(b'raw-private-body'))
            with self.assertRaises(SafeError) as e:evaluate(Path(t),f['state'],q,False,transport=transport)
            self.assertEqual(n[0],1);self.assertNotIn('raw-private',str(e.exception))
    def test_ambiguous_timeout_not_retried(self):
        f=fixture('01-skill-routing');q=questions_for(spec(f['case_id']),f['state']);n=[0]
        with tempfile.TemporaryDirectory() as t,patch.dict(os.environ,{'JEV_PROVIDER':'typesafe','TYPESAFE_API_KEY':'synthetic-local-credential'}):
            b=provider_budget(Path(t));b.grant(3,1)
            def transport(*a,**k):n[0]+=1;raise TimeoutError()
            with self.assertRaisesRegex(SafeError,'API_TRANSPORT_FAILURE'):evaluate(Path(t),f['state'],q,False,transport=transport)
            self.assertEqual(n[0],1)

class Interfaces(unittest.TestCase):
    def test_mcp_defaults_to_four_offline_tools(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(len(tools(state_root=Path(t) / 'state')),4)
    def test_tool_rejects_unknown_arguments(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(SafeError):call('jev_catalog',{'shell':'not-a-tool'},state_root=Path(t) / 'state')
    def test_mcp_stdio_initialize_and_catalog(self):
        messages=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'test','version':'1'}}},
            {'jsonrpc':'2.0','method':'notifications/initialized'},
            {'jsonrpc':'2.0','id':2,'method':'tools/list'},
            {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'jev_catalog','arguments':{}}}]
        with tempfile.TemporaryDirectory() as t:
            p=subprocess.run([sys.executable,str(ROOT/'jev.py'),'mcp','--state-root',str(Path(t) / 'state')],input='\n'.join(json.dumps(m) for m in messages)+'\n',text=True,capture_output=True,timeout=10)
        self.assertEqual(p.returncode,0);rows=[json.loads(x) for x in p.stdout.splitlines()];self.assertEqual(len(rows),3)
        self.assertEqual(rows[0]['result']['protocolVersion'],'2025-11-25');self.assertEqual(len(rows[1]['result']['tools']),4)
        self.assertEqual(len(json.loads(rows[2]['result']['content'][0]['text'])),20)
    def test_cli_catalog(self):
        with tempfile.TemporaryDirectory() as t:
            p=subprocess.run([sys.executable,str(ROOT/'jev.py'),'catalog','--state-root',str(Path(t) / 'state')],capture_output=True,text=True,timeout=10)
        self.assertEqual(p.returncode,0);self.assertEqual(len(json.loads(p.stdout)),20)
    def test_web_allowlist_and_origin(self):
        try:server=make_server(0)
        except PermissionError:self.skipTest('managed sandbox denies loopback socket binding')
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();url=f'http://127.0.0.1:{server.server_port}'
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(url+'/api/data') as r:self.assertEqual(r.status,200);self.assertIn("frame-ancestors 'none'",r.headers['Content-Security-Policy'])
            for route in ('/.local/live-grants.sqlite3','/../jev.py','/.env'):
                with self.assertRaises(urllib.error.HTTPError) as e:opener.open(url+route)
                self.assertEqual(e.exception.code,404)
            req=urllib.request.Request(url+'/',headers={'Origin':'https://untrusted.invalid'})
            with self.assertRaises(urllib.error.HTTPError) as e:opener.open(req)
            self.assertEqual(e.exception.code,403)
            req=urllib.request.Request(url+'/',data=b'{}')
            with self.assertRaises(urllib.error.HTTPError) as e:opener.open(req)
            self.assertEqual(e.exception.code,405)
        finally:server.shutdown();server.server_close()
    def test_bootstrap_preserves_existing_config_and_is_idempotent(self):
        import importlib.util
        ms=importlib.util.spec_from_file_location('bootstrap',ROOT/'scripts'/'bootstrap.py');module=importlib.util.module_from_spec(ms);ms.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'.codex').mkdir();config=root/'.codex'/'config.toml';before='model = "existing-selected-model"\n';config.write_text(before)
            self.assertEqual(module.configure(root,Path(sys.executable)),'project_mcp_configured')
            self.assertIn(before,config.read_text());self.assertEqual(module.configure(root,Path(sys.executable)),'already_configured')
    def test_bootstrap_refuses_existing_jev_server(self):
        import importlib.util
        ms=importlib.util.spec_from_file_location('bootstrap',ROOT/'scripts'/'bootstrap.py');module=importlib.util.module_from_spec(ms);ms.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'.codex').mkdir();config=root/'.codex'/'config.toml';before='[mcp_servers.jev_control]\ncommand="existing"\n';config.write_text(before)
            with self.assertRaises(SafeError):module.configure(root,Path(sys.executable))
            self.assertEqual(config.read_text(),before)
if __name__=='__main__':unittest.main()
