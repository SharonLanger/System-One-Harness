"""Mechanical checks only; never import the real SDK or run live inference."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import copy
import json
import tempfile
import unittest
from unittest.mock import patch
import run
import reporting

HERE=Path(__file__).resolve().parents[1]
OUTPUT=HERE/'checks'/'output'
OUTPUT.mkdir(exist_ok=True)

class BatchChecks(unittest.TestCase):
    def definition(self,kind='apple-noul'):
        return run.validate(run.load_json(HERE/kind/'experiment.json'))

    def execute(self,d,answers):
        self.loads=0; self.requests=[]
        owner=self
        class Agent:
            def predict(self,text,questions,**kwargs):
                owner.requests.append((text,copy.deepcopy(questions),kwargs))
                v=answers[len(owner.requests)-1]
                if isinstance(v,BaseException): raise v
                if callable(v): return v(questions)
                name=next(iter(questions))
                return {'answers':{name:{'type':'noul','noul':v}}}
        def loader(*args,**kwargs): self.loads+=1; self.load_args=(args,kwargs);return Agent()
        with tempfile.TemporaryDirectory(dir=OUTPUT) as tmp:
            p=Path(tmp)/'demo.json'
            record=run.execute_configuration(d,d['configurations'][0],p,loader=loader)
            self.assertEqual(json.loads(p.read_text())['definition'],d)
            self.assertTrue(p.with_suffix('.md').is_file())
            self.assertFalse(p.with_suffix('.trace.tmp').exists())
            return record

    def test_starter_definitions(self):
        for kind in ('apple-choice','apple-noul'):
            d=self.definition(kind)
            self.assertEqual(len(d['cases']),10); self.assertEqual(len(d['configurations']),3)

    def test_both_directions_and_abstention(self):
        d=self.definition();d['cases']=[{'id':str(i),'input':'fruit','expected':e} for i,e in enumerate(['yes','no','yes','no','yes'])]
        r=self.execute(d,[.9,.1,.1,.9,.5])
        self.assertEqual([c['final_outcome'] for c in r['cases']],['correct','correct','incorrect','incorrect','abstained'])
        self.assertEqual(self.loads,1)
        self.assertEqual(len(self.requests),5)
        for text,q,kwargs in self.requests:
            self.assertEqual(text,'fruit');self.assertEqual(len(q),1)
            self.assertNotIn('expected',json.dumps(q));self.assertNotIn('id',q)
        self.assertEqual(reporting.metrics(r,'final')['accuracy'],.5)
        self.assertEqual(reporting.metrics(r,'final')['coverage'],.8)
        self.assertEqual(reporting.effects(r)['correct_rejected'],['4'])

    def test_invalid_response_error_and_continue(self):
        d=self.definition(); d['cases']=d['cases'][:3]
        r=self.execute(d,[lambda q:{'answers':{}},RuntimeError('bad SDK'),.9])
        self.assertEqual([c['final_outcome'] for c in r['cases']],['error','error','correct'])
        self.assertEqual(r['cases'][0]['raw_response'],{'answers':{}})
        self.assertEqual(r['status'],'completed_with_errors')

    def test_choice_and_threshold_boundary(self):
        d=self.definition('apple-choice'); d['cases']=d['cases'][:2]
        def answer(q):
            return {'answers':{'subject':{'type':'choice','choice':'apple','probabilities':{'apple':.4,'pear':.25,'dog':.2,'other':.15}}}}
        r=self.execute(d,[answer,answer])
        self.assertEqual([c['final_outcome'] for c in r['cases']],['correct','correct'])
        self.assertEqual(r['cases'][0]['diagnostics']['derived_report_conditions'][0]['margin'],0)
        self.assertEqual(r['cases'][0]['enriched_response']['probability_gap'],.15)

    def test_wrong_choice_and_rejected_choice(self):
        d=self.definition('apple-choice');d['cases']=d['cases'][:2]
        def wrong(q):return {'answers':{'subject':{'type':'choice','choice':'pear','probabilities':{'apple':.1,'pear':.7,'dog':.1,'other':.1}}}}
        def unclear(q):return {'answers':{'subject':{'type':'choice','choice':'apple','probabilities':dict.fromkeys(q['subject']['criteria'],.25)}}}
        r=self.execute(d,[wrong,unclear])
        self.assertEqual([c['final_outcome'] for c in r['cases']],['incorrect','abstained'])

    def test_raw_correct_final_processing_error(self):
        d=self.definition();d['cases']=d['cases'][:1]
        with patch('laya_context_router.answers.interpret.interpret',side_effect=ValueError('rule failure')):
            r=self.execute(d,[.9])
        self.assertEqual(r['cases'][0]['recommendation_outcome'],'correct')
        self.assertEqual(r['cases'][0]['final_outcome'],'error')

    def test_interrupt_preserves_partial(self):
        d=self.definition();r=self.execute(d,[.9,KeyboardInterrupt()])
        self.assertEqual(r['status'],'interrupted')
        self.assertEqual(len(r['cases']),2)
        self.assertEqual(reporting.metrics(r,'final')['unattempted'],8)

    def test_load_failure_and_zero_denominators(self):
        d=self.definition()
        with tempfile.TemporaryDirectory(dir=OUTPUT) as tmp:
            def loader(*a,**k):raise RuntimeError('missing SDK')
            r=run.execute_configuration(d,d['configurations'][0],Path(tmp)/'demo.json',loader)
        self.assertEqual(r['status'],'failed');self.assertEqual(len(r['cases']),0)
        self.assertIsNone(reporting.metrics(r,'final')['accuracy'])
        self.assertIsNone(reporting.metrics(r,'final')['coverage'])

    def test_validation_and_collisions(self):
        d=self.definition()
        for mutate in [lambda d:d['cases'].append(d['cases'][0]),lambda d:d['configurations'][0].update(name='../bad'),lambda d:d['cases'][0].update(expected=None),lambda d:d['configurations'][0].update(unknown=True),lambda d:d['question'].update(type='score'),lambda d:d['rule'].update(conditions_by_type={'choice':[{'field':'x','op':'gte','value':'bad'}]}),lambda d:d['configurations'][0].update(lang='he')]:
            bad=copy.deepcopy(d);mutate(bad)
            with self.assertRaises((ValueError,TypeError)):run.validate(bad)
        with self.assertRaises(ValueError):run.unique_pairs([('x',1),('x',2)])
        with tempfile.TemporaryDirectory(dir=OUTPUT) as tmp:
            a=run.allocate(Path(tmp),'2026-10-31_10-00-00');b=run.allocate(Path(tmp),'2026-10-31_10-00-00')
            self.assertNotEqual(a,b);self.assertTrue(b.name.endswith('_001'))

    def test_config_forwarding_and_scope(self):
        d=self.definition();d['cases']=d['cases'][:1];d['configurations']=d['configurations'][1:2]
        root=HERE.parents[1]
        def snapshot():
            return {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file() and '.git' not in p.parts and 'experiments' not in p.relative_to(root).parts}
        before=snapshot();self.execute(d,[.9]);self.assertEqual(snapshot(),before)
        self.assertEqual(self.load_args[1],{'lang_temperatures':{'en':{'temperature':[.2,.2,.2]}}})
        self.assertEqual(self.requests[0][2],{'lang':'en'})
        self.assertFalse((root/'logs').exists())

class OrchestrationChecks(unittest.TestCase):
    def test_main_sequential_snapshots_and_comparison(self):
        calls=[]
        class Child:
            def __init__(self,cmd,env):
                self.name=cmd[cmd.index('--configuration')+1]
                out=Path(cmd[cmd.index('--output')+1]);p=out/(self.name+'.json')
                snap=run.load_json(p)
                calls.append(self.name)
                class Agent:
                    def predict(self,text,questions,**kwargs):
                        return {'answers':{'apple_evidence':{'type':'noul','noul':.5}}}
                r=run.execute_configuration(snap['definition'],snap['configuration'],p,lambda *a,**k:Agent())
                self.returncode=0 if r['status']=='completed' else 1
                assert env['PYTHONDONTWRITEBYTECODE']=='1'
            def wait(self,**kwargs):return self.returncode
        base=HERE/'apple-noul'/'results';base.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as tmp:
            out=Path(tmp)
            with patch.object(run,'allocate',return_value=out),patch.object(run.subprocess,'Popen',Child),patch.object(run.subprocess,'check_output',return_value='test-revision'):
                self.assertEqual(run.main(['--experiment','apple-noul']),0)
            self.assertEqual(calls,['sdk-default','temp-02','temp-07'])
            self.assertTrue((out/'comparison.md').exists())
            self.assertEqual(len(list(out.iterdir())),7)
            for name in calls:
                r=run.load_json(out/(name+'.json'))
                self.assertEqual(r['mode'],'injected')
                self.assertEqual(r['metrics']['final']['abstained'],10)
                self.assertEqual(r['metrics']['recommendation']['attempted'],10)

    def test_nonzero_worker_exit_is_failure_even_after_completed_json(self):
        class Child:
            returncode=1
            def __init__(self,cmd,env):
                out=Path(cmd[cmd.index('--output')+1]);name=cmd[cmd.index('--configuration')+1]
                p=out/(name+'.json');r=run.load_json(p);r['status']='completed';reporting.save(r,p)
            def wait(self):return 1
        base=HERE/'apple-noul'/'results';base.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as tmp:
            out=Path(tmp)
            with patch.object(run,'allocate',return_value=out),patch.object(run.subprocess,'Popen',Child),patch.object(run.subprocess,'check_output',return_value='test-revision'):
                self.assertEqual(run.main(['--experiment','apple-noul','--configuration','sdk-default']),1)
            self.assertEqual(run.load_json(out/'sdk-default.json')['status'],'failed')

    def test_atomic_failure_preserves_previous_checkpoint(self):
        with tempfile.TemporaryDirectory(dir=OUTPUT) as tmp:
            p=Path(tmp)/'record.json';p.write_text('previous')
            with patch.object(Path,'replace',side_effect=OSError('save failed')):
                with self.assertRaises(OSError):reporting.atomic(p,'replacement')
            self.assertEqual(p.read_text(),'previous')

if __name__=='__main__':unittest.main()
