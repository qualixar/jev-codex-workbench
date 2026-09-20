"""Delivery regressions: every stock request must be safe before enabling API use."""
import importlib.util,json,shutil,sys,tempfile,unittest
from pathlib import Path
from jevkit.engine import ROOT,catalog,fixture,spec,questions_for,run
from jevkit.security import screen
from jevkit.web_server import records

def module(name):
    ms=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    m=importlib.util.module_from_spec(ms);ms.loader.exec_module(m);return m

class DeliveryTests(unittest.TestCase):
    def test_all_sixty_full_requests_screen_cleanly(self):
        for c in catalog():
            for v in ('nominal','adversarial','uncertain'):
                f=fixture(c['id'],v);s=spec(c['id']);q=questions_for(s,f['state'])
                _,issues=screen({'state':f['state'],'questions':q})
                self.assertEqual(issues,[],(c['id'],v,issues))
    def test_all_sixty_full_receipts_screen_cleanly(self):
        for c in catalog():
            for v in ('nominal','adversarial','uncertain'):
                r=run(c['id'],v,persist=False);_,issues=screen(r)
                self.assertEqual(issues,[],(c['id'],v,issues))
    def test_every_case_has_three_fixtures_and_playbook(self):
        self.assertEqual(len(catalog()),20)
        for c in catalog():
            self.assertTrue((ROOT/'docs'/'use_cases'/(c['id']+'.md')).is_file())
            self.assertEqual(len(list((ROOT/'fixtures'/c['id']).glob('*.json'))),3)
    def test_custom_data_and_secret_bearing_records_not_served(self):
        from jevkit.security import private_json
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);r=run('01-skill-routing',persist=False)
            private_json(root/'artifacts'/'runs'/'a.json',r)
            self.assertEqual(len(records(root)),1)
            r['data_classification']='user-approved';private_json(root/'artifacts'/'runs'/'a.json',r)
            self.assertEqual(records(root),[])
            r['data_classification']='synthetic';r['state']['password']='synthetic-secret-value';private_json(root/'artifacts'/'runs'/'a.json',r)
            self.assertEqual(records(root),[])
    def test_real_demo_baseline_and_fix_in_temporary_copy(self):
        collector=module('collect_demo')
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);shutil.copytree(ROOT/'demo_project',root/'demo_project',ignore=shutil.ignore_patterns('__pycache__'))
            path=root/'demo_project'/'cache.py';code=path.read_text()
            # Be independent of whether the owner has already completed the demo in place.
            path.write_text(code.replace('self.clock() >= expires_at','self.clock() > expires_at'))
            before=collector.collect(root)
            self.assertEqual(before['test_exit_code'],1);self.assertEqual(before['tests_executed'],4)
            tests=(root/'demo_project'/'test_cache.py').read_bytes()
            path.write_text(path.read_text().replace('self.clock() > expires_at','self.clock() >= expires_at'))
            after=collector.collect(root)
            self.assertEqual(after['test_exit_code'],0);self.assertTrue(after['source_unchanged_during_tests'])
            self.assertNotEqual(before['source_hash'],after['source_hash'])
            self.assertEqual(tests,(root/'demo_project'/'test_cache.py').read_bytes())
    def test_snapshot_is_offline_and_escapes_script_boundary(self):
        from jevkit.security import private_json
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);shutil.copytree(ROOT/'web',root/'web');shutil.copytree(ROOT/'use_cases',root/'use_cases')
            r=run('01-skill-routing',persist=False);r['state']['task']='</script><script>globalThis.PWNED=true</script>'
            private_json(root/'artifacts'/'runs'/'a.json',r)
            result=module('export_viewer').build(root).read_text()
            self.assertIn("connect-src 'none'",result)
            self.assertIn(r'\u003c/script>',result)
            self.assertNotIn('</script><script>globalThis.PWNED=true</script>',result)
            self.assertIn('window.__WORKBENCH_SNAPSHOT__',result)
    def test_captured_reels_not_required_for_core_install(self):
        for script in ('bootstrap.py','preflight.py','set_credential.py','enable_live.py'):
            self.assertNotIn('import playwright',(ROOT/'scripts'/script).read_text())

if __name__=='__main__':unittest.main()
