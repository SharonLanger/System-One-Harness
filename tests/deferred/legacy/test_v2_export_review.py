import unittest as _deferred_unittest
raise _deferred_unittest.SkipTest("Phase two: experiment dependency; see tests/deferred/README.md")

import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'experiments/tools'))
import export_v2_results as e
import analyze_v2_export as a
from research.records import manifest_identity
from research.protocol import digest


class ExportReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = self.base/'source'
        self.source.mkdir(); (self.source/'inferences').mkdir()
        self.roles = {'dev':'development', 'held':'held_out'}
        cases = {'schema_version':1, 'dataset_id':'demo', 'dataset_version':'1', 'cases':[
            {'id':cid, 'input':'Explain this', 'expected':label, 'label_status':'settled',
             'noise_level':'regular', 'tags':[], 'source_family_id':family, 'split':split}
            for cid,label,family,split in [('c0','unclear','dev','development'),
                                          ('c1','explain','dev','development'),
                                          ('c2','unclear','held','held_out')]]}
        suite = {'schema_version':1, 'experiment_id':'demo', 'dataset_id':'demo', 'dataset_version':'1',
            'adapter':'generic-question', 'question_type':'choice', 'labels':['explain','unclear'],
            'questions':[{'id':q, 'variant_kind':'baseline' if q=='q0' else 'wording',
                'definition':{'name':'action','type':'choice','instructions':'Choose',
                              'criteria':{'explain':'Explain','unclear':'Unclear'}}} for q in ['q0','q1']],
            'configurations':[{'id':'t0','temperature':None,'lang':'en','model':'fake'}],
            'rules':[{'id':r,'definition':{'name':r,'conditions':[]}} for r in ['r0','r1']],
            'baseline':{'question_id':'q0','config_id':'t0','rule_id':'r0'}}
        self.m = {'schema_version':1,'run_id':'test','mode':'fixture','rule_mode':'replay',
            'status':'completed','suite':suite,'cases':cases,'source_hash':a.source_fingerprint(),
            'model_fingerprint':{'fixture':'test'},'runtime_versions':{},'adapter_hash':'test'}
        self.save_manifest()
        for q in suite['questions']:
            for case in cases['cases']:
                iid=e.legacy_hash([q['id'],None,'t0',case['id']])[:32]
                # Reconstruct the actual boundary format independently of exporter helpers.
                body={k:v for k,v in q['definition'].items() if k!='name'}
                raw={'id':iid,'status':'completed','error':None,'requested_config':suite['configurations'][0],
                    'payload':{'text':case['input'],'questions':{'action':body},'predict_kwargs':{}},
                    'raw_response':{'answers':{'action':{'type':'choice','choice':case['expected'],
                                       'probabilities':{'explain':0.6,'unclear':0.4}}}}}
                e.write(self.source/'inferences'/f'{iid}.json',raw)
        self.rolefile=self.base/'roles.json'; e.write(self.rolefile,self.roles)

    def save_manifest(self):
        for key in ('suite','cases'): self.m[key+'_hash']=e.legacy_hash(self.m[key])
        e.write(self.source/'manifest.json',self.m)

    def export(self):
        return e.export_run(self.source,self.base/'exports',source_stopped=True,roles_file=self.rolefile)

    def frozen(self):
        suite=self.m['suite']
        definitions={q['id']+'|t0':{'question':deepcopy(q),'config':deepcopy(suite['configurations'][0]),
            'policies':[{'kind':'native','rule':deepcopy(r)} for r in suite['rules']]} for q in suite['questions']}
        return {'status':'frozen','candidate_ids':list(definitions),'definitions':definitions,
                'identity':manifest_identity(self.m,self.roles)}

    def analyze_final(self, root, frozen):
        frozen['freeze_hash']=digest({k:v for k,v in frozen.items() if k!='freeze_hash'})
        return a.analyze_export(root,self.base/'report',stage='final',finalists=frozen)

    def test_structural_failures_precede_evaluation(self):
        for scenario in ('config','partition','duplicate_partition','excluded','all_excluded',
                         'definition','order','unsupported','empty','keys','duplicate_rule'):
            with self.subTest(scenario=scenario):
                root=self.export(); frozen=self.frozen()
                definition=frozen['definitions']['q1|t0']
                if scenario=='config':
                    frozen['definitions']['q1|new']=frozen['definitions'].pop('q1|t0')
                    frozen['candidate_ids']=['q0|t0','q1|new']
                    definition['config']['id']='new'
                elif scenario in ('partition','duplicate_partition'):
                    info=e.read(root/'export.json',False)
                    if scenario=='partition': info['partitions'].pop()
                    else: info['partitions'].append(deepcopy(info['partitions'][-1]))
                    e.write(root/'export.json',info)
                elif scenario in ('excluded','all_excluded'):
                    definitions=e.read(root/'definitions.json',False)
                    definitions['source_manifest']['suite']['exclusions']=[
                        {'question_id':'q1','config_id':'t0','rule_id':r,'reason':'test'}
                        for r in (['r1'] if scenario=='excluded' else ['r0','r1'])]
                    e.write(root/'definitions.json',definitions)
                    info=e.read(root/'export.json',False);info['definitions_sha256']=e.digest(root/'definitions.json');e.write(root/'export.json',info)
                elif scenario=='definition': definition['question']['definition']['instructions']='Changed'
                elif scenario=='order': definition['question']['definition']['criteria']=dict(reversed(list(definition['question']['definition']['criteria'].items())))
                elif scenario=='unsupported': definition['policies'][0]['kind']='experimental'
                elif scenario=='empty': definition['policies']=[]
                elif scenario=='keys': frozen['definitions'].pop('q1|t0')
                elif scenario=='duplicate_rule': definition['policies'].append(deepcopy(definition['policies'][0]))
                with patch.object(a,'native_decision',side_effect=AssertionError('evaluated')) as evaluate:
                    with self.assertRaises(ValueError): self.analyze_final(root,frozen)
                    evaluate.assert_not_called()
                self.assertFalse((self.base/'report').exists())

    def test_valid_scope_and_partial_records(self):
        iid=e.legacy_hash(['q1',None,'t0','c2'])[:32]
        (self.source/'inferences'/f'{iid}.json').unlink()
        summary=self.analyze_final(self.export(),self.frozen())
        self.assertEqual({(v['question_id'],v['rule_id']) for v in summary['vectors']},
                         {('q0','r0'),('q0','r1'),('q1','r0'),('q1','r1')})
        self.assertTrue(all(v['missing']==1 and v['partial'] for v in summary['vectors'] if v['question_id']=='q1'))

    def test_class_support(self):
        for scenario in ('complete','missing','error','unsettled','empty'):
            with self.subTest(scenario=scenario):
                root=self.export(); info=e.read(root/'export.json',False)
                for part in info['partitions']:
                    path=root/part['path']; records=[json.loads(line) for line in path.read_text().splitlines()]
                    if scenario=='missing': records=[r for r in records if r['case_id']!='c1']
                    if scenario=='empty': records=[]
                    if scenario=='error':
                        for r in records:
                            if r['case_id']=='c1': r['status']='error'
                    path.write_text(''.join(json.dumps(r)+'\n' for r in records))
                    part['found']=len(records);part['sha256']=e.digest(path)
                e.write(root/'export.json',info)
                if scenario=='unsettled':
                    definitions=e.read(root/'definitions.json',False)
                    definitions['source_manifest']['cases']['cases'][1].update(label_status='taxonomy_pending',expected=None)
                    e.write(root/'definitions.json',definitions)
                    info['definitions_sha256']=e.digest(root/'definitions.json');e.write(root/'export.json',info)
                row=a.analyze_export(root,self.base/('metrics-'+scenario))['vectors'][0]
                self.assertEqual(row['balanced_accuracy'],row['balanced_accuracy_present_classes'])
                self.assertEqual(row['comparable_all_classes'],scenario=='complete')
                self.assertEqual(row['support'],{'explain':int(scenario=='complete'),'unclear':int(scenario!='empty')})
                self.assertEqual(row['missing_classes'],[] if scenario=='complete' else ['explain','unclear'] if scenario=='empty' else ['explain'])
                self.assertEqual(row['balanced_accuracy_present_classes'],None if scenario=='empty' else 1.0)

    def test_real_fixture_worker_to_analyzer(self):
        import engine
        from laya_context_router import log_utils
        worker_home=self.base/'worker';worker_home.mkdir()
        fixture_folder=worker_home/'examples/generic-choice';fixture_folder.mkdir(parents=True)
        responses={}
        for q in self.m['suite']['questions']:
            for case in self.m['cases']['cases']:
                responses['|'.join([q['id'],'t0',case['id']])]={'answers':{'action':{
                    'type':'choice','choice':case['expected'],'probabilities':{'explain':0.6,'unclear':0.4}}}}
        e.write(fixture_folder/'responses.json',{'responses':responses})
        e.write(worker_home/'source-snapshot.json',{'revision':'offline-test'})
        with patch.object(engine,'HERE',worker_home), patch.object(log_utils,'LOG_PATH',worker_home/'debug.jsonl'), \
             patch.dict(sys.modules,{'laya_mlx':None,'mlx':None}), \
             patch('laya_context_router.laya.predict.real_loader',side_effect=AssertionError('loader called')), \
             patch('laya_context_router.laya.registry.AgentRegistry.get_agent',side_effect=AssertionError('registry called')):
            source=engine.create(self.m['cases'],self.m['suite'],'fixture','replay',{})
            engine.worker(source,'t0')
            before={p.relative_to(source):p.read_bytes() for p in source.rglob('*') if p.is_file()}
            with patch.object(e,'expected_payload',wraps=e.expected_payload):
                root=e.export_run(source,self.base/'worker-exports',source_stopped=True,roles_file=self.rolefile)
            info=e.read(root/'export.json',False)
            self.assertEqual((info['planned'],info['found'],info['success'],info['error']),(6,6,6,0))
            for part in info['partitions']:
                records=[json.loads(line) for line in (root/part['path']).read_text().splitlines()]
                self.assertEqual({r['inference_id'] for r in records},
                    {e.legacy_hash([part['question_id'],None,'t0',c['id']])[:32] for c in self.m['cases']['cases']})
            summary=a.analyze_export(root,self.base/'worker-report')
            self.assertEqual(len(summary['vectors']),4)
            self.assertTrue(all(v['found']==2 and v['accuracy']==1.0 for v in summary['vectors']))
            self.assertEqual(before,{p.relative_to(source):p.read_bytes() for p in source.rglob('*') if p.is_file()})
