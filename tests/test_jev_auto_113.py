"""Offline tests for the delivered implementation; no credentials or model calls.
These test code contracts, not the accuracy of either decision model.
"""
from __future__ import annotations
import copy, importlib.util, json, os, socket, subprocess, sys, tempfile, threading, time, unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from jev_auto.common import AutoError, canonical, decode, digest, number, private_dir, read_private, write_private, workspace, workspace_id, state_dir, screen, require_clean
from jev_auto.settings import make_policy,save_policy,load_policy,revoke,validate_policy
from jev_auto.protocol import validate_questions,validate_response,compact_receipt
from jev_auto.store import Store,SingleFlight
from jev_auto.engine import Engine
from jev_auto.sieve import bounded_blocks,reduce_text,render
from jev_auto.hooks import handle,plain_output
from jev_auto.mlx_preflight import preflight
from jev_auto.measure import compare,extract_codex_usage

NOUL={'q':{'type':'noul','instructions':'Is the evidence relevant?'}}
CHOICE={'q':{'type':'choice','instructions':'Choose a route.','criteria':{'a':'First','b':'Second'}}}
SCORE={'q':{'type':'score','instructions':'Evaluate relevance.','criteria':['None','Partial','Direct']}}

def fake_response(qs,kind='normal'):
    answers={}
    for k,q in qs.items():
        if q['type']=='noul':
            value=0.0 if k=='error' else (0.5 if kind=='uncertain' else (0.01 if k.startswith('b') or k=='needed' else .9))
            answers[k]={'type':'noul','noul':value}
        elif q['type']=='choice':
            names=list(q['criteria']);p={n:0.0 for n in names};p[names[0]]=1.0
            answers[k]={'type':'choice','choice':names[0],'confidence':1.0,'probabilities':p}
        else:
            n=len(q['criteria']);p={str(i):float(i==n-1) for i in range(n)}
            answers[k]={'type':'score','score':float(n-1),'confidence':1.0,'probabilities':p,'legend':{str(i):x for i,x in enumerate(q['criteria'])}}
    return {'model':'offline-test-double','answers':answers,'usage':{'input_tokens':100,'output_tokens':0}}

class FakeProvider:
    def __init__(self,delay=0,kind='normal'):self.calls=0;self.delay=delay;self.kind=kind;self.fail=False;self.on_call=None;self.lock=threading.Lock()
    def evaluate(self,p,state,qs):
        with self.lock:self.calls+=1
        time.sleep(self.delay)
        if self.on_call:self.on_call()
        if self.fail:raise AutoError('TEST_PROVIDER_FAILURE')
        return fake_response(qs,self.kind)
    def close(self):pass

class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.repo=self.root/'repo';self.repo.mkdir();self.base=self.root/'state'
        self.p=make_policy(self.repo,'typesafe',browser_origins=['https://example.org'])
        save_policy(self.repo,self.p,self.base)
        self.provider=FakeProvider();self.engine=Engine(self.repo,self.base,self.provider)
    def change(self,**values):
        self.p={**self.p,**values};save_policy(self.repo,self.p,self.base);return self.p

class CommonTests(unittest.TestCase):
    def test_canonical_key_order(self):self.assertEqual(canonical({'b':2,'a':1}),canonical({'a':1,'b':2}))
    def test_digest_changes_for_evidence(self):self.assertNotEqual(digest('before'),digest('after'))
    def test_nonfinite_rejected(self):
        for v in (float('nan'),float('inf'),-float('inf')):
            with self.subTest(v=v),self.assertRaises(AutoError):canonical({'x':v})
    def test_decode_rejects_constants(self):
        for text in ('NaN','Infinity','-Infinity'):
            with self.subTest(text=text),self.assertRaises(AutoError):decode(text)
    def test_decode_size_limit(self):
        with self.assertRaises(AutoError):decode('"long"',3)
    def test_number_rejects_bool(self):self.assertFalse(number(True));self.assertTrue(number(.5))
    def test_screen_does_not_echo(self):
        text='Bearer '+'x'*40
        self.assertIn('BEARER',screen(text));self.assertNotIn(text,str(screen(text)))
    def test_newline_token_detected_before_json_escaping(self):
        self.assertIn('BEARER',screen({'text':'line\nBearer '+'x'*30}))
    def test_sensitive_dictionary_key(self):
        self.assertIn('CREDENTIAL',screen({'api_key':'synthetic-value'}))
    def test_key_is_blocked(self):
        with self.assertRaisesRegex(AutoError,'SENSITIVE'):require_clean({'example':'abc-secret-value'},('abc-secret-value',))
    def test_private_file_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'config.json';write_private(f,{'yes':True});self.assertEqual(read_private(f),{'yes':True});self.assertEqual(f.stat().st_mode&0o777,0o600)
    def test_world_readable_file_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'config.json';write_private(f,{});f.chmod(0o644)
            with self.assertRaises(AutoError):read_private(f)
    def test_symlink_private_file_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'real';write_private(f,{});l=Path(d)/'link';l.symlink_to(f)
            with self.assertRaises(AutoError):read_private(l)

class PermissionTests(WorkspaceTest):
    def test_edit_does_not_expire_standing_permission(self):
        (self.repo/'file').write_text('first');a=load_policy(self.repo,self.base)
        (self.repo/'file').write_text('second');self.assertEqual(a,load_policy(self.repo,self.base))
    def test_policy_scoped_to_workspace(self):
        other=self.root/'other';other.mkdir()
        with self.assertRaises(AutoError):validate_policy(self.p,other)
    def test_expired_policy(self):
        with self.assertRaisesRegex(AutoError,'EXPIRED'):validate_policy({**self.p,'expires_at':0},self.repo)
    def test_revocation(self):
        revoke(self.repo,self.base)
        with self.assertRaises(AutoError):self.engine.judge('probe',{},NOUL)
        self.assertEqual(self.provider.calls,0)
    def test_invalid_provider(self):
        with self.assertRaises(AutoError):make_policy(self.repo,'unknown')
    def test_bool_budget_rejected(self):
        with self.assertRaises(AutoError):validate_policy({**self.p,'max_calls_per_day':True},self.repo)
    def test_exact_origin_validation(self):
        with self.assertRaises(AutoError):validate_policy({**self.p,'browser_origins':['https://example.org/path']},self.repo)
    def test_budget_atomic_across_threads(self):
        p=self.change(max_calls_per_day=7)
        def reserve(_):
            try:self.engine.store.reserve(p,100);return True
            except AutoError:return False
        with ThreadPoolExecutor(max_workers=12) as ex:results=list(ex.map(reserve,range(35)))
        self.assertEqual(sum(results),7)
    def test_bytes_budget(self):
        p=self.change(max_bytes_per_day=1000)
        self.engine.store.reserve(p,900)
        with self.assertRaisesRegex(AutoError,'DAILY'):self.engine.store.reserve(p,101)
    def test_request_budget(self):
        with self.assertRaisesRegex(AutoError,'REQUEST'):self.engine.store.reserve(self.p,1000000)
    def test_permission_reuse_across_requests(self):
        for n in range(3):self.engine.judge('probe',{'value':n},NOUL)
        self.assertEqual(self.provider.calls,3)
    def test_unauthorized_recipe(self):
        with self.assertRaisesRegex(AutoError,'RECIPE'):self.engine.judge('unapproved',{},NOUL)
        self.assertEqual(self.provider.calls,0)

class ProtocolTests(unittest.TestCase):
    def test_three_primitives(self):
        for q in (NOUL,CHOICE,SCORE):self.assertEqual(set(validate_response(fake_response(q),q)['answers']),set(q))
    def test_missing_answer(self):
        with self.assertRaises(AutoError):validate_response({'model':'x','answers':{}},NOUL)
    def test_wrong_type(self):
        r=fake_response(NOUL);r['answers']['q']['type']='choice'
        with self.assertRaises(AutoError):validate_response(r,NOUL)
    def test_probability_sum(self):
        r=fake_response(CHOICE);r['answers']['q']['probabilities']={'a':.6,'b':.6}
        with self.assertRaises(AutoError):validate_response(r,CHOICE)
    def test_wrong_argmax(self):
        r=fake_response(CHOICE);r['answers']['q']['choice']='b'
        with self.assertRaises(AutoError):validate_response(r,CHOICE)
    def test_nonfinite_noul(self):
        r=fake_response(NOUL);r['answers']['q']['noul']=float('nan')
        with self.assertRaises(AutoError):validate_response(r,NOUL)
    def test_score_expectation(self):
        r=fake_response(SCORE);r['answers']['q']['score']=.5
        with self.assertRaises(AutoError):validate_response(r,SCORE)
    def test_optional_usage_stays_unknown(self):
        r=fake_response(NOUL);r.pop('usage');self.assertIsNone(validate_response(r,NOUL)['usage']['input_tokens'])
    def test_boolean_usage_rejected(self):
        r=fake_response(NOUL);r['usage']['input_tokens']=True
        with self.assertRaises(AutoError):validate_response(r,NOUL)
    def test_noul_extra_confidence_not_fabricated(self):
        r=fake_response(NOUL);r['answers']['q']['confidence']=.99
        self.assertNotIn('confidence',validate_response(r,NOUL)['answers']['q'])
    def test_response_model_pin(self):
        with self.assertRaisesRegex(AutoError,'MODEL'):validate_response(fake_response(NOUL),NOUL,'jev-1.13.0')
    def test_invalid_question_count(self):
        with self.assertRaises(AutoError):validate_questions({})
    def test_compact_result_hides_input(self):
        r={'state':'private source','questions':'long rubric','record_sha256':'a'*64,'policy':{'status':'RECOMMEND','recommendation':'a'},'mode':'live'}
        out=compact_receipt(r);self.assertNotIn('state',out);self.assertNotIn('questions',out);self.assertFalse(out['execution_authorized'])
    def test_compact_large_items(self):
        r={'record_sha256':'a'*64,'policy':{'items':['x'*100]*100,'recommendation':'a','status':'RECOMMEND'}}
        self.assertLess(len(canonical(compact_receipt(r))),5000)

class EngineTests(WorkspaceTest):
    def test_cache_avoids_second_call(self):
        first=self.engine.judge('probe',{'value':'a'},NOUL);second=self.engine.judge('probe',{'value':'a'},NOUL)
        self.assertFalse(first['cache_hit']);self.assertTrue(second['cache_hit']);self.assertIsNone(second['provider_usage_this_call']);self.assertEqual(self.provider.calls,1)
    def test_evidence_change_reruns(self):
        self.engine.judge('probe',{'value':'a'},NOUL);self.engine.judge('probe',{'value':'b'},NOUL);self.assertEqual(self.provider.calls,2)
    def test_question_change_reruns(self):
        self.engine.judge('probe',{},NOUL);q=copy.deepcopy(NOUL);q['q']['instructions']='Different question';self.engine.judge('probe',{},q);self.assertEqual(self.provider.calls,2)
    def test_policy_change_invalidates_cache(self):
        self.engine.judge('probe',{},NOUL);self.change(drop_probability=.11);self.engine.judge('probe',{},NOUL);self.assertEqual(self.provider.calls,2)
    def test_concurrent_request_coalescing(self):
        self.provider.delay=.15
        with ThreadPoolExecutor(max_workers=8) as ex:rows=list(ex.map(lambda _:self.engine.judge('probe',{},NOUL),range(8)))
        self.assertEqual(self.provider.calls,1);self.assertEqual(sum(r['provider_usage_this_call'] is not None for r in rows),1)
    def test_failures_not_cached(self):
        self.provider.fail=True
        for _ in range(2):
            with self.assertRaises(AutoError):self.engine.judge('probe',{},NOUL)
        self.assertEqual(self.provider.calls,2)
    def test_revoked_during_inference_does_not_return(self):
        self.provider.on_call=lambda:revoke(self.repo,self.base)
        with self.assertRaises(AutoError):self.engine.judge('probe',{},NOUL)
    def test_screen_before_provider(self):
        with self.assertRaises(AutoError):self.engine.judge('probe',{'text':'Bearer '+'x'*30},NOUL)
        self.assertEqual(self.provider.calls,0)
    def test_cached_evidence_is_exact(self):
        key=self.engine.store.put({'kind':'source','text':'one\ntwo\nthree'})
        self.assertEqual(self.engine.recall(key,2,3)['text'],'two\nthree')
    def test_recall_range_cap(self):
        with self.assertRaises(AutoError):self.engine.recall('a'*64,1,400)
    def test_cross_workspace_evidence_not_visible(self):
        key=self.engine.store.put({'text':'one'});other=Store(self.root/'other')
        with self.assertRaisesRegex(AutoError,'NOT_FOUND'):other.get(key)
    def test_unknown_host_savings(self):
        stats=self.engine.store.stats();self.assertIsNone(stats['host_tokens_saved']);self.assertIsNone(stats['host_cost_saved'])
    def test_provider_route_explicit(self):
        self.change(routes={'probe':'laya-mlx'});self.assertEqual(self.engine.effective_policy(self.p,'probe')['provider'],'laya-mlx');self.assertEqual(self.engine.effective_policy(self.p,'sieve')['provider'],'typesafe')
    def test_probe_observes_model_not_expected_label(self):
        r=self.engine.dispatch({'op':'probe'});self.assertEqual(r['mode'],'actual_model_inference');self.assertIn('department',r['answers'])
    def test_browser_origin_rejected_before_call(self):
        with self.assertRaises(AutoError):self.engine.browser({'origin':'https://other.example','actions':[]})
        self.assertEqual(self.provider.calls,0)
    def test_browser_choice_advisory(self):
        req={'origin':'https://example.org','goal':'View next page','state':'Next page link','actions':[{'id':'a0','op':'click','description':'Next'}]}
        self.assertFalse(self.engine.browser(req)['execution_authorized'])
    def test_browser_unknown_operation_rejected(self):
        req={'origin':'https://example.org','actions':[{'id':'a0','op':'shell','description':'not allowed'}]}
        with self.assertRaises(AutoError):self.engine.browser(req)

class SieveTests(WorkspaceTest):
    def text(self):return '\n'.join('Routine information item %03d '%n+'x'*60 for n in range(160))
    def reduce(self,text=None,**kw):return reduce_text(self.engine,self.p,'Fix the cache expiry boundary',self.text() if text is None else text,**kw)
    def test_chunk_exact_roundtrip(self):
        for text in ('','a','a\nb\n','a\n\n\nb',self.text()):
            self.assertEqual('\n'.join(b.text for b in bounded_blocks(text)),text)
    def test_block_cap_with_many_blank_lines(self):self.assertLessEqual(len(bounded_blocks('a\n\n'*10000,2,48)),48)
    def test_reduction_recoverable(self):
        r=self.reduce();self.assertTrue(r['changed']);source=self.engine.store.get(r['receipt_id']);self.assertEqual(source['text'],self.text());self.assertIn('jev_recall',r['text'])
    def test_keep_first_last(self):
        r=self.reduce();self.assertIn('item 000',r['text']);self.assertIn('item 159',r['text'])
    def test_small_output_bypass(self):self.assertFalse(self.reduce('few lines')['changed']);self.assertEqual(self.provider.calls,0)
    def test_errors_preserved(self):
        r=self.reduce(self.text()+'\nERROR: broken');self.assertFalse(r['changed']);self.assertEqual(self.provider.calls,0)
    def test_uncertain_kept(self):
        self.provider.kind='uncertain';self.assertFalse(self.reduce()['changed'])
    def test_unavailable_keeps_original(self):
        self.provider.fail=True;r=self.reduce();self.assertEqual(r['text'],self.text());self.assertFalse(r['changed'])
    def test_protect_slm(self):self.assertFalse(self.reduce(tool='mcp__slm__recall')['changed']);self.assertEqual(self.provider.calls,0)
    def test_protect_mandatory_instructions(self):
        self.assertFalse(self.reduce(tool='Read',tool_input={'file_path':'AGENTS.md'})['changed']);self.assertEqual(self.provider.calls,0)
    def test_constraints_pinned_even_when_judge_wrong(self):
        rows=self.text().split('\n');rows[70]='MUST preserve this exact requirement';r=self.reduce('\n'.join(rows));self.assertIn(rows[70],r['text'])
    def test_sensitive_output_not_sent(self):
        self.assertFalse(self.reduce(self.text()+'\nBearer '+'x'*30)['changed']);self.assertEqual(self.provider.calls,0)
    def test_missing_goal(self):
        r=reduce_text(self.engine,self.p,'',self.text());self.assertFalse(r['changed'])
    def test_net_savings_threshold(self):
        self.change(min_reduction=1.0);self.assertFalse(self.reduce()['changed'])
    def test_no_token_claim_from_chars(self):self.assertIsNone(self.reduce()['host_tokens_saved'])

class HookTests(WorkspaceTest):
    def event(self,name,**kw):return {'hook_event_name':name,'cwd':str(self.repo),'session_id':'test-session',**kw}
    def runhook(self,e,caller):return handle(e,self.base,caller=caller,starter=lambda *_:None)
    def test_session_note(self):self.assertIn('standing',self.runhook(self.event('SessionStart'),lambda *_:{})['hookSpecificOutput']['additionalContext'])
    def test_pretool_does_not_call_broker(self):
        def boom(*a):raise AssertionError('must not call')
        self.assertIsNone(handle(self.event('PreToolUse'),self.base,caller=boom,starter=boom))
    def test_posttool_contract(self):
        out=self.runhook(self.event('PostToolUse',tool_name='Bash',tool_response='long output'),lambda *a:{'changed':True,'text':'compact'})
        self.assertEqual(out,{'continue':False,'stopReason':'compact'})
    def test_nonzero_exit_preserved(self):self.assertIsNone(plain_output({'tool_response':{'exit_code':1,'stdout':'failure'}}))
    def test_mcp_slm_object_not_rewritten(self):
        def boom(*a):raise AssertionError('must not call')
        self.assertIsNone(self.runhook(self.event('PostToolUse',tool_name='mcp__slm__recall',tool_response={'text':'memory'}),boom))
    def test_computer_use_result_not_rewritten(self):
        self.assertIsNone(self.runhook(self.event('PostToolUse',tool_name='cua_repl',tool_response='picture'),lambda *_:{}))
    def test_failure_passes_through(self):
        def fail(*a):raise AutoError('NO_SERVICE')
        self.assertIsNone(self.runhook(self.event('PostToolUse',tool_name='Bash',tool_response='text'),fail))
    def test_prompt_prepares_once(self):
        calls=[]
        def call(_,req):calls.append(req['op']);return {'packet':'chosen source'}
        result=self.runhook(self.event('UserPromptSubmit',prompt='fix cache'),call)
        self.assertEqual(calls,['set_goal','prepare']);self.assertEqual(result['hookSpecificOutput']['additionalContext'],'chosen source')
    def test_child_gets_no_separate_grant(self):
        result=self.runhook(self.event('SubagentStart'),lambda *_:{})
        self.assertIn('shared budget',result['hookSpecificOutput']['additionalContext'])
    def test_unenrolled_no_hook_effect(self):
        other=self.root/'outside';other.mkdir();self.assertIsNone(handle({'hook_event_name':'SessionStart','cwd':str(other)},self.base))

class FakeTokenizer:
    mask_token='[MASK]'
    def __call__(self,text,**_):return {'input_ids':list(range(len(text.split())))}

class MLXTests(unittest.TestCase):
    def test_short_preflight(self):self.assertLess(preflight(FakeTokenizer(),{'max_len':512,'head_max_len':192},'short',NOUL)['q'],512)
    def test_long_state_rejected(self):
        with self.assertRaisesRegex(AutoError,'STATE'):preflight(FakeTokenizer(),{'max_len':60,'head_max_len':40},'word '*100,NOUL)
    def test_long_option_rejected(self):
        q=copy.deepcopy(CHOICE);q['q']['criteria']['a']='word '*60
        with self.assertRaisesRegex(AutoError,'OPTION'):preflight(FakeTokenizer(),{},'state',q)
    def test_long_instructions_rejected(self):
        q=copy.deepcopy(NOUL);q['q']['instructions']='word '*500
        with self.assertRaisesRegex(AutoError,'INSTRUCTIONS'):preflight(FakeTokenizer(),{},'state',q)
    def test_question_count_affects_each_frame_not_shared_encoding(self):
        qs={str(i):copy.deepcopy(NOUL['q']) for i in range(5)};counts=preflight(FakeTokenizer(),{},'state',qs);self.assertEqual(len(counts),5)
    def test_zero_fabricated_mlx_accuracy_claims(self):
        r=fake_response(NOUL);self.assertEqual(validate_response(r,NOUL)['usage']['output_tokens'],0)

class MeasurementTests(unittest.TestCase):
    def row(self,**kw):return {'task_id':'one','task_fingerprint':'abc','host':'codex','model':'chosen','effort':'fixed','accepted':True,'input_tokens':1000,'cached_input_tokens':800,'output_tokens':200,'elapsed_seconds':10,'total_cost_usd':None,**kw}
    def test_cached_subset_not_double_counted(self):self.assertEqual(compare(self.row(),self.row())['host_tokens_baseline'],1200)
    def test_negative_savings_retained(self):self.assertLess(compare(self.row(),self.row(input_tokens=2000))['host_token_reduction_percent'],0)
    def test_missing_usage_unknown(self):self.assertIsNone(compare(self.row(),self.row(input_tokens=None))['host_token_reduction_percent'])
    def test_failed_task_not_savings(self):self.assertIsNone(compare(self.row(),self.row(accepted=False))['host_token_reduction_percent'])
    def test_zero_baseline_no_division(self):self.assertIsNone(compare(self.row(input_tokens=0,output_tokens=0,cached_input_tokens=0),self.row())['host_token_reduction_percent'])
    def test_different_model_invalid(self):
        with self.assertRaises(AutoError):compare(self.row(),self.row(model='different'))
    def test_unknown_invoice_not_zero(self):self.assertIsNone(compare(self.row(),self.row())['total_cost_reduction_percent'])
    def test_aggregation_must_be_declared(self):
        r=[{'type':'turn.completed','usage':{'input_tokens':10,'output_tokens':2}}]*2
        with self.assertRaises(AutoError):extract_codex_usage(r)
        self.assertEqual(extract_codex_usage(r,'per-turn')['input_tokens'],20);self.assertEqual(extract_codex_usage(r,'last-cumulative')['input_tokens'],10)
    def test_quota_never_inferred(self):self.assertIsNone(compare(self.row(),self.row(input_tokens=100,cached_input_tokens=0))['subscription_quota_saving_percent'])

if __name__=='__main__':unittest.main()
