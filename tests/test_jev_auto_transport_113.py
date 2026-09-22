"""Real local IPC and mocked provider/legacy-host compatibility tests."""
from __future__ import annotations
import copy, importlib, os, socket, sys, tempfile, threading, time, unittest
from pathlib import Path
from unittest.mock import patch
from jev_auto.common import AutoError,canonical
from jev_auto.engine import Engine
from jev_auto.settings import make_policy,save_policy
from jev_auto.ipc import address,read_message,request,ensure
from jev_auto.server import Server
from jev_auto.mcp import dispatch,definitions
from jev_auto.providers import Providers
from jev_auto.mlx_process import MLXProcess

class FakeProvider:
    def __init__(self):self.calls=0
    def evaluate(self,p,state,questions):
        self.calls+=1
        return {'model':'test-double','answers':{k:{'type':'noul','noul':.9} for k in questions},'usage':{'input_tokens':11,'output_tokens':0}}
    def close(self):pass

class IPCIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.repo=self.root/'repo';self.repo.mkdir();self.base=self.root/'state'
        self.policy=make_policy(self.repo,'typesafe');save_policy(self.repo,self.policy,self.base)
        self.provider=FakeProvider();self.engine=Engine(self.repo,self.base,self.provider)
        self.address=address(self.repo,self.base)
        self.server=Server(self.address,self.engine)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        def close():
            self.server.shutdown();self.server.server_close();self.thread.join(2)
            if self.address.exists():self.address.unlink()
        self.addCleanup(close)
    def test_real_unix_socket_health(self):self.assertEqual(request(self.repo,{'op':'health'},self.base)['version'],'1.1.3')
    def test_same_service_on_repeat_ensure(self):
        ensure(self.repo,self.base);ensure(self.repo,self.base);self.assertEqual(self.provider.calls,0)
    def test_private_socket_permissions(self):self.assertEqual(self.address.stat().st_mode&0o777,0o600)
    def test_no_provider_on_status(self):request(self.repo,{'op':'stats'},self.base);self.assertEqual(self.provider.calls,0)
    def test_unknown_op_safe_code(self):
        with self.assertRaisesRegex(AutoError,'UNKNOWN_OPERATION'):request(self.repo,{'op':'unknown'},self.base)
    def test_state_base_separates_sockets(self):self.assertNotEqual(address(self.repo,self.base),address(self.repo,self.root/'other-state'))
    @unittest.skipUnless(sys.platform=='darwin','macOS socket path')
    def test_macos_default_long_temp_path_uses_short_private_socket_root(self):
        with patch('jev_auto.ipc.tempfile.gettempdir',return_value='/private/var/folders/example/long/per-user/T'):
            addr=address(self.repo,self.base)
        self.assertTrue(str(addr).startswith('/private/tmp/qualixar-jev-auto-'))
        self.assertLessEqual(len(str(addr).encode()),100)
    def test_real_recall_path(self):
        k=self.engine.store.put({'kind':'source','text':'one\ntwo'});r=request(self.repo,{'op':'recall','receipt_id':k,'start':2,'end':2},self.base);self.assertEqual(r['text'],'two')
    def test_multi_request_frame_rejected(self):
        a,b=socket.socketpair()
        try:
            a.sendall(b'{}\n{}\n')
            with self.assertRaisesRegex(AutoError,'ONE_REQUEST'):read_message(b)
        finally:a.close();b.close()
    def test_shutdown_is_local_not_provider_call(self):
        request(self.repo,{'op':'shutdown'},self.base);self.assertTrue(self.server.stopping.is_set());self.assertEqual(self.provider.calls,0)

class FakeLegacy:
    def __init__(self):self.calls=[]
    def tools(self,**_):
        names=('jev_health','jev_policy_status','jev_policy_check','jev_catalog','jev_describe','jev_run_fixture','jev_evaluate')
        result=[]
        for n in names:
            props={'case_id':{'type':'string','enum':['example']},'workspace_path':{'type':'string'},'state':{'type':'object'}} if n=='jev_evaluate' else {}
            result.append({'name':n,'description':'old','inputSchema':{'type':'object','properties':props,'required':['case_id','workspace_path'] if props else [],'additionalProperties':False}})
        return result
    def call(self,name,args,**_):self.calls.append(name);return {'legacy':name}

class MCPCompatibilityTests(unittest.TestCase):
    def setUp(self):self.legacy=FakeLegacy();self.args={'case_id':'example','workspace_path':'/not-read','state':{}}
    def test_original_seven_plus_four(self):self.assertEqual(len(definitions(self.legacy)),11)
    def test_health_delegates_without_auto(self):self.assertEqual(dispatch('jev_health',{},self.legacy),{'legacy':'jev_health'})
    def test_evaluation_goes_to_broker(self):
        seen=[]
        def call(req):seen.append(req);return {'status':'RECOMMEND','receipt_id':'a'*64}
        result=dispatch('jev_evaluate',self.args,self.legacy,caller=call)
        self.assertEqual(result['status'],'RECOMMEND');self.assertEqual(seen[0]['op'],'evaluate');self.assertEqual(self.legacy.calls,[])
    def test_unknown_args_rejected(self):
        with self.assertRaises(AutoError):dispatch('jev_evaluate',{**self.args,'provider':'other'},self.legacy,caller=lambda _: {})
    def test_enrolled_budget_failure_never_asks_legacy_grant(self):
        with patch('jev_auto.mcp.ensure',side_effect=AutoError('AUTO_DAILY_BUDGET')):
            with self.assertRaisesRegex(AutoError,'DAILY'):dispatch('jev_evaluate',self.args,self.legacy)
        self.assertEqual(self.legacy.calls,[])
    def test_unenrolled_keeps_legacy_behavior(self):
        with patch('jev_auto.mcp.ensure',side_effect=AutoError('WORKSPACE_NOT_ENROLLED')):self.assertEqual(dispatch('jev_evaluate',self.args,self.legacy),{'legacy':'jev_evaluate'})
    def test_recall_not_a_new_model_call(self):
        seen=[]
        dispatch('jev_recall',{'workspace_path':'/not-read','receipt_id':'a'*64},self.legacy,caller=lambda r:seen.append(r) or {})
        self.assertEqual(seen[0]['op'],'recall')
    def test_boolean_line_range_rejected(self):
        with self.assertRaises(AutoError):dispatch('jev_recall',{'workspace_path':'/not-read','receipt_id':'a'*64,'start':True},self.legacy,caller=lambda _: {})

class FakeMLX:
    def __init__(self,cfg):self.cfg=cfg;self.loads=0;self.proc=object();self.closed=False
    def warmup(self):self.loads+=1;time.sleep(.025);return {'ready':True}
    def close(self):self.closed=True;self.proc=None
    def predict(self,state,qs,timeout):return {'model':'fake-local','answers':{'q':{'type':'noul','noul':.8}},'usage':{'input_tokens':12,'output_tokens':0}}

class MLXProcessTests(unittest.TestCase):
    def test_runtime_resident_not_loaded_each_prediction(self):
        p=Providers();cfg={'provider':'laya-mlx','timeout_seconds':2,'mlx':{'repository':'fake-local','revision':'pinned','weight_sha256':'x'}}
        with patch('jev_auto.mlx_process.MLXProcess',FakeMLX):
            p.warmup(cfg,wait=True);q={'q':{'type':'noul','instructions':'Relevant?'}}
            p.evaluate(cfg,'first',q);p.evaluate(cfg,'second',q);self.assertEqual(p._mlx.loads,1)
        p.close()
    def test_not_configured_explicit(self):
        with self.assertRaisesRegex(AutoError,'NOT_CONFIGURED'):Providers().warmup({'provider':'laya-mlx'})
    def test_truncation_rejection_preserves_worker(self):
        p=MLXProcess({});p.proc=object()
        with patch.object(p,'_exchange',side_effect=AutoError('MLX_STATE_WOULD_TRUNCATE')),patch.object(p,'close') as close:
            with self.assertRaises(AutoError):p.predict('long',{},1)
            close.assert_not_called()
    def test_transport_error_discards_broken_worker(self):
        p=MLXProcess({});p.proc=object()
        with patch.object(p,'_exchange',side_effect=AutoError('MLX_WORKER_TIMEOUT')),patch.object(p,'close') as close:
            with self.assertRaises(AutoError):p.predict('data',{},1)
            close.assert_called_once()
    def test_missing_worker_not_silent_cloud_fallback(self):
        p=MLXProcess({})
        with self.assertRaisesRegex(AutoError,'WARMUP'):p.predict('data',{},1)


class RemoteTransportTests(unittest.TestCase):
    """Exercise the real transport code using a controlled HTTP object, never the network."""
    def setUp(self):
        import types
        self.key='synthetic-test-credential';self.requests=[];self.status=200;self.body=None
        providers=types.ModuleType('jevkit.providers')
        providers.provider_profile=lambda name:types.SimpleNamespace(endpoint='https://api.typesafe.ai/v1/systemone',model='jev-1.13.0')
        providers.get_provider_credential=lambda _:self.key
        parent=types.ModuleType('jevkit');parent.providers=providers
        self.modules=patch.dict('sys.modules',{'jevkit':parent,'jevkit.providers':providers});self.modules.start();self.addCleanup(self.modules.stop)
        owner=self
        class Response:
            def __init__(self):self.status=owner.status;self.data=owner.body
            def read1(self,n):part,self.data=self.data[:n],self.data[n:];return part
            def close(self):pass
        class Connection:
            def __init__(self,*a,**k):self.sock=None
            def request(self,method,path,body,headers):owner.requests.append((method,path,body,headers))
            def getresponse(self):return Response()
            def close(self):pass
        self.conn=patch('jev_auto.providers.http.client.HTTPSConnection',Connection);self.conn.start();self.addCleanup(self.conn.stop)
        self.q={'q':{'type':'noul','instructions':'Is this relevant?'}};self.policy={'provider':'typesafe','timeout_seconds':2}
        self.body=canonical({'model':'jev-1.13.0','answers':{'q':{'type':'noul','noul':.9}},'usage':{'input_tokens':20,'output_tokens':0}})
    def test_fixed_endpoint_and_auth_header(self):
        out=Providers().remote(self.policy,{'text':'public content'},self.q)
        method,path,body,headers=self.requests[0]
        self.assertEqual((method,path),('POST','/v1/systemone'));self.assertNotIn(self.key,body.decode());self.assertEqual(headers['Authorization'],'Bearer '+self.key);self.assertEqual(out['model'],'jev-1.13.0')
    def test_no_automatic_retry_or_error_body_echo(self):
        self.status=503;self.body=self.key.encode()
        with self.assertRaisesRegex(AutoError,'PROVIDER_HTTP_503') as caught:Providers().remote(self.policy,{'text':'public'},self.q)
        self.assertNotIn(self.key,str(caught.exception));self.assertEqual(len(self.requests),1)
    def test_redirect_not_followed(self):
        self.status=302
        with self.assertRaisesRegex(AutoError,'HTTP_302'):Providers().remote(self.policy,{'text':'public'},self.q)
        self.assertEqual(len(self.requests),1)
    def test_model_mismatch_refused(self):
        self.body=self.body.replace(b'jev-1.13.0',b'wrong-model')
        with self.assertRaisesRegex(AutoError,'MODEL_MISMATCH'):Providers().remote(self.policy,{'text':'public'},self.q)
    def test_active_credential_in_payload_blocked(self):
        with self.assertRaisesRegex(AutoError,'SENSITIVE'):Providers().remote(self.policy,{'text':self.key},self.q)
        self.assertEqual(self.requests,[])
    def test_malformed_json_rejected(self):
        self.body=b'not json'
        with self.assertRaises(AutoError):Providers().remote(self.policy,{'text':'public'},self.q)
    def test_inbound_sensitive_material_refused(self):
        self.body=canonical({'model':'jev-1.13.0','answers':{'q':{'type':'noul','noul':.9}},'note':self.key})
        with self.assertRaisesRegex(AutoError,'SENSITIVE'):Providers().remote(self.policy,{'text':'public'},self.q)

if __name__=='__main__':unittest.main()
