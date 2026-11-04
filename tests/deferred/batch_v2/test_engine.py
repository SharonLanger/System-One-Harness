import unittest as _deferred_unittest
raise _deferred_unittest.SkipTest("Phase two: experiment dependency; see tests/deferred/README.md")

import sys
sys.dont_write_bytecode=True
import unittest, tempfile,json,subprocess, time
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
import engine
from schema import load
from reporting import collect
class EngineTests(unittest.TestCase):
    def setUp(self):
        self.cases=load(HERE/'examples/generic-choice/cases.json'); self.suite=load(HERE/'examples/generic-choice/suite.json')
        self.root=None
    def make(self,rule_mode='replay',limits=None):
        self.root=engine.create(self.cases,self.suite,'fixture',rule_mode,limits or {})
        return self.root
    def test_fixture_and_resume_do_not_repeat_inference(self):
        root=self.make(); self.assertEqual(engine.run(root),0)
        rows=collect(root); self.assertEqual(len(rows),24)
        self.assertEqual(len(list((root/'inferences').glob('*.json'))),12)
        self.assertTrue(all(r['status']=='completed' for r in rows))
        before={p.name:p.read_bytes() for p in (root/'inferences').glob('*.json')}
        self.assertEqual(engine.run(root),0)
        self.assertEqual(load(root/'attempts.json')['count'],12)
        self.assertEqual(before,{p.name:p.read_bytes() for p in (root/'inferences').glob('*.json')})
        states={(r['raw_label']==r['expected'],r['accepted']) for r in rows}; self.assertEqual(len(states),4)
        expected=load(HERE/'examples/generic-choice/expected-summary.json')
        actual=[]
        for p in sorted((root/'batches').rglob('summary.json')):
            row=next(x for x in load(p) if x['group_type']=='overall')
            actual.append({k:row[k] for k in expected[0]})
        self.assertEqual(actual,expected)
    def test_direct_matches_replay_same_fixture(self):
        r=self.make(); engine.run(r); replay=collect(r)
        d=self.make('direct'); engine.run(d); direct=collect(d)
        self.assertEqual(load(d/'attempts.json')['count'],24)
        fields=['raw_label','final_label','accepted','reason','enriched']
        self.assertEqual([[x.get(k) for k in fields] for x in replay],[[x.get(k) for k in fields] for x in direct])
    def test_resume_raw_checkpoint_without_case_checkpoint(self):
        r=self.make();engine.run(r)
        p=next((r/'batches').rglob('case-01.json'));p.unlink()
        engine.run(r);self.assertTrue(p.exists());self.assertEqual(load(r/'attempts.json')['count'],12)
    def test_cap_and_exclusions(self):
        self.suite['exclusions']=[{'question_id':'q-baseline','rule_id':'r-baseline','config_id':'sdk-default','reason':'test exclusion'}]
        r=self.make(limits={'max_calls':2});engine.run(r)
        self.assertEqual(load(r/'attempts.json')['count'],2)
        rows=collect(r);self.assertEqual(len(rows),21)
        self.assertTrue(any(x['status']=='unattempted' for x in rows))
    def test_changed_frozen_config_rejected(self):
        r=self.make(); m=load(r/'manifest.json');m['suite']['configurations'][0]['temperature']=.99;engine.save(r/'manifest.json',m)
        with self.assertRaisesRegex(ValueError,'suite_hash'): engine.resume_check(r)
    def test_empty_is_not_live_accuracy(self):
        self.cases['cases']=[]
        with tempfile.TemporaryDirectory(dir=HERE/'checks/output') as t:
            c=Path(t)/'cases.json';s=Path(t)/'suite.json';engine.save(c,self.cases);engine.save(s,self.suite)
            cmd=[sys.executable,'-B',str(HERE/'run.py'),'--cases',str(c),'--suite',str(s)]
            self.assertEqual(subprocess.run(cmd+['--dry-run'],capture_output=True).returncode,0)
            self.assertEqual(subprocess.run(cmd+['--mode','fixture'],capture_output=True).returncode,2)
    def test_real_hard_worker_timeout(self):
        r=self.make(limits={'worker_timeout':.05})
        real=engine.subprocess.Popen
        with patch.object(engine.subprocess,'Popen',side_effect=lambda *a,**kw:real([sys.executable,'-c','import time;time.sleep(60)'],**kw)):
            start=time.monotonic();self.assertEqual(engine.run(r),1);self.assertLess(time.monotonic()-start,5)
        self.assertEqual(load(r/'worker-sdk-default-status.json')['status'],'timeout')
    def test_block_adapters_and_metadata_isolation(self):
        from laya.config import RunConfig
        for adapter,module,key,expected in [('requested-action','requested_action','action','explain'),('context-scope','context_scope','scope','method_only')]:
            q=load(engine.ROOT/'src/defaults/questions'/f'{module}.json'); s=deepcopy(self.suite);s['adapter']=adapter;s['question_type']='choice'
            raw={'answers':{module:{'type':'choice','choice':expected,'probabilities':{l:(1 if l==expected else 0) for l in q['criteria']},'answer_confidence':1}}}
            boundary=engine.Boundary(engine.RecordedAgent(raw));result=engine.execute({'prompt':'Explain this method.'},{'id':'q','definition':q},self.suite['rules'][0],s,RunConfig(),boundary)
            self.assertEqual(result.data[key],expected)
            self.assertEqual(boundary.payload['text'],'Explain this method.')
            self.assertNotIn('expected',boundary.payload)
    def test_malformed_and_rounding_replay_parity(self):
        from laya.config import RunConfig
        q=self.suite['questions'][0];r=self.suite['rules'][0]
        for raw in [None,{'answers':{}},{'answers':{'subject':{'type':'choice','choice':'fruit','probabilities':{'fruit':.574999,'other':.425001}}}}]:
            def call():return engine.execute('apple',q,r,self.suite,RunConfig(),engine.Boundary(engine.RecordedAgent(raw)))
            try:
                a=call();self.assertEqual(a,call())
            except Exception as exc:
                with self.assertRaises(type(exc)):call()
if __name__=='__main__':
    (HERE/'checks/output').mkdir(exist_ok=True)
    unittest.main()

class ExtraPipelineChecks(unittest.TestCase):
    def test_generic_noul_accept_and_reject(self):
        from laya.config import RunConfig
        q={'id':'q','definition':{'name':'flag','type':'noul','instructions':'Is this an apple?'}}
        suite={'adapter':'generic-question','question_type':'noul'}
        raw={'answers':{'flag':{'type':'noul','noul':.7,'confidence':.9,'answer_confidence':.7}}}
        for threshold,answer in [(.1,'yes'),(.3,'undecided')]:
            rule={'definition':{'name':'boundary','conditions':[{'field':'distance_from_boundary','op':'gte','value':threshold}]}}
            result=engine.execute('apple',q,rule,suite,RunConfig(),engine.Boundary(engine.RecordedAgent(raw)))
            self.assertEqual(result.data['label'],answer)
