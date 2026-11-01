import copy,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parents[1];sys.path[:0]=[str(HERE),str(HERE.parents[1]/'src')]
from schema import load,validate,hash_value
from engine import execute,Boundary,RecordedAgent,create,run,save
from method_adapter import prepared
from method_reporting import outcome,metrics,aggregate,summarize,COUNTS
CAM=HERE/'experiments/method-selection-200'

class CampaignTests(unittest.TestCase):
 def setUp(self):
    self.cases=load(CAM/'cases.json');self.suite=load(CAM/'rounds/001-small/suite.json')
 def response(self,case,q):
    qs=prepared(case['input'],q,self.suite).questions
    label=case['expected']['method_label'];labels=list(qs['method']['criteria'])
    return {'answers':{'method':{'type':'choice','choice':label,'probabilities':{k:.95 if k==label else .05/(len(labels)-1) for k in labels},'answer_confidence':.95},'multiple_relevant':{'type':'noul','noul':.9 if case['expected']['multiple_relevant']=='yes' else .1,'answer_confidence':.9}}}
 def test_schema_and_counts(self):
    validate(self.cases,self.suite)
    self.assertEqual(self.suite['rules'],load(HERE/'experiments/requested-action-500/versions/1/suite.json')['rules'])
    from collections import Counter
    self.assertEqual(Counter(c['split'] for c in self.cases['cases']),{'development':120,'held_out':80})
    self.assertEqual(Counter(c['noise_level'] for c in self.cases['cases']),{'regular':160,'noisy':30,'heavy':10})
    bad=copy.deepcopy(self.cases);bad['cases'][0]['expected']['selected_id']='bad'
    with self.assertRaises(ValueError):validate(bad,self.suite)
 def test_golden_and_weighting(self):
    r={k:0 for k in COUNTS};r.update(planned=10,evaluated=10,selectable_evaluated=6,refusal_evaluated=4,correct_selection=4,wrong_selection=1,missed_selection=1,correct_refusal=3,unsafe_selection=1);metrics(r)
    self.assertEqual(r['selection_precision'],4/6);self.assertEqual(r['end_to_end_correctness'],.7)
    empty=metrics({k:0 for k in COUNTS});self.assertIsNone(empty['selection_precision'])
    a={k:0 for k in COUNTS};a.update(correct_selection=1)
    b={k:0 for k in COUNTS};b.update(correct_selection=1,wrong_selection=8)
    self.assertEqual(aggregate([a,b])['selection_precision'],.2)
 def test_engine_replay_and_reports(self):
    from laya.config import RunConfig
    cases=copy.deepcopy(self.cases);cases['cases']=[cases['cases'][0],next(c for c in cases['cases'] if 'multiple' in c['tags'])]
    for c in cases['cases']:c['split']='development'
    suite=copy.deepcopy(self.suite);suite['experiment_id']='method-fixture-check'
    with tempfile.TemporaryDirectory() as td:
      fixture=Path(td)/'responses.json';responses={}
      for q in suite['questions']:
       for cfg in suite['configurations']:
        for c in cases['cases']:responses['|'.join([q['id'],cfg['id'],c['id']])]=self.response(c,q)
      fixture.write_text(json.dumps({'responses':responses}));suite['fixture_responses']=str(fixture)
      root=create(cases,suite,'fixture','replay',{'max_calls':16,'max_seconds':30,'worker_timeout':30})
      try:
        self.assertEqual(run(root),0)
        m=load(root/'manifest.json');self.assertEqual(m['inference_attempts'],16)
        totals=summarize(root);self.assertEqual(totals['unique_evidence'],16);self.assertEqual(totals['logical_outcomes']['planned'],160)
        before=(root/'analysis/development/vectors.csv').read_bytes();summarize(root);self.assertEqual(before,(root/'analysis/development/vectors.csv').read_bytes())
        self.assertEqual(run(root),0);self.assertEqual(load(root/'attempts.json')['count'],16)
        with self.assertRaises(ValueError):summarize(root,'held_out')
        # Replay uses the exact production reducer and keeps the multiple guard.
        c=cases['cases'][1];q=suite['questions'][0];raw=self.response(c,q);raw['answers']['method']['choice']=next(k for k in prepared(c['input'],q,suite).questions['method']['criteria'] if k!='none_or_unclear')
        result=execute(c['input'],q,suite['rules'][1],suite,RunConfig(),Boundary(RecordedAgent(raw)))
        self.assertIsNone(result.data['selected_id'])
      finally:
        import shutil;shutil.rmtree(root)
if __name__=='__main__':unittest.main()
