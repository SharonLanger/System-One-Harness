import unittest as _deferred_unittest
raise _deferred_unittest.SkipTest("Phase two: experiment dependency; see tests/deferred/README.md")

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from test_export_v2_results import fixture
import export_v2_results as e
import analyze_v2_export as a


class AnalyzeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name); self.source = self.base/'source'
        m = fixture(self.source,n=3,nq=2,nc=1)
        m.update(run_id='fixture',source_hash=a.source_fingerprint(),
                 model_fingerprint={'fixture':'test'},runtime_versions={},adapter_hash='fixture')
        # One development and two distinct calibration/held-out families.
        self.roles = {'family-0':'development','family-1':'temperature','family-2':'held_out'}
        m['cases']['cases'][1]['split']='calibration'
        m['cases']['cases'][2]['split']='held_out'
        m['cases_hash']=e.legacy_hash(m['cases'])
        e.write(self.source/'manifest.json',m)
        self.rolefile=self.base/'roles.json'; e.write(self.rolefile,self.roles)

    def export(self):
        return e.export_run(self.source,self.base/'exports',source_stopped=True,roles_file=self.rolefile)

    def test_development_only_and_unclear_nonactionable(self):
        root=self.export()
        with patch.dict(sys.modules,{'laya_mlx':None,'mlx':None}), \
             patch('laya_context_router.laya.predict.real_loader',side_effect=AssertionError('model loader called')), \
             patch('laya_context_router.laya.registry.AgentRegistry.get_agent',side_effect=AssertionError('registry called')):
            summary=a.analyze_export(root,self.base/'report')
        row=summary['vectors'][0]
        self.assertEqual((row['planned'],row['found'],row['accepted_unclear'],row['actionable']),(1,1,1,0))
        self.assertIsNone(row['actionable_error'])
        self.assertEqual(row['accuracy'],1)
        self.assertTrue((self.base/'report/report.md').is_file())

    def test_errors_and_missing_are_not_rejections(self):
        path=next(p for p in (self.source/'inferences').glob('*.json')
                  if p.stem==e.legacy_hash(['q-0',None,'t-0','case-000'])[:32])
        raw=e.read(path); raw.update(status='error',error={'message':'failed','type':'Error'})
        e.write(path,raw)
        row=a.analyze_export(self.export(),self.base/'report')['vectors'][0]
        self.assertEqual((row['errors'],row['rejected'],row['evaluated']),(1,0,0))
        self.assertIsNone(row['accuracy'])

    def test_source_mismatch_and_final_stage_refused(self):
        root=self.export()
        with patch.object(a,'source_fingerprint',return_value='wrong'):
            with self.assertRaisesRegex(ValueError,'source mismatch'):
                a.analyze_export(root,self.base/'bad')
        with self.assertRaisesRegex(ValueError,'frozen finalists'):
            a.analyze_export(root,self.base/'bad',stage='final')
        self.assertFalse((self.base/'bad').exists())

    def test_unsettled_and_missing_denominators(self):
        m=e.read(self.source/'manifest.json',lossless=False)
        case=m['cases']['cases'][0];case.update(label_status='taxonomy_pending',expected=None)
        m['cases_hash']=e.legacy_hash(m['cases']);e.write(self.source/'manifest.json',m)
        row=a.analyze_export(self.export(),self.base/'unscored')['vectors'][0]
        self.assertEqual((row['unscored'],row['scored'],row['accepted']),(1,0,1))
        self.assertIsNone(row['accuracy']);self.assertIsNone(row['accepted_error'])
        path=self.source/'inferences'/(e.legacy_hash(['q-0',None,'t-0','case-000'])[:32]+'.json')
        path.unlink()
        row=a.analyze_export(self.export(),self.base/'partial')['vectors'][0]
        self.assertEqual((row['missing'],row['errors'],row['evaluated']),(1,0,0))
        self.assertTrue(row['partial'])

    def test_partition_tampering_refused(self):
        root=self.export(); info=e.read(root/'export.json')
        path=root/info['partitions'][0]['path'];path.write_text(path.read_text()+'\n')
        with self.assertRaisesRegex(ValueError,'checksum'):
            a.analyze_export(root,self.base/'bad')

    def test_frozen_finalist_and_choice_order(self):
        from copy import deepcopy
        from research.records import manifest_identity
        from research.protocol import digest
        root=self.export();m=e.read(root/'definitions.json',lossless=False)['source_manifest']
        q,c,r=m['suite']['questions'][0],m['suite']['configurations'][0],m['suite']['rules'][0]
        frozen={'status':'frozen','candidate_ids':['q-0|t-0'],
                'identity':manifest_identity(m,self.roles),
                'definitions':{'q-0|t-0':{'question':q,'config':c,'policies':[{'kind':'native','rule':r}]}}}
        frozen['freeze_hash']=digest(frozen)
        with patch.object(a,'native_decision',wraps=a.native_decision) as evaluation:
            summary=a.analyze_export(root,self.base/'final',stage='final',finalists=frozen)
        self.assertEqual(len(summary['vectors']),1)
        self.assertEqual(evaluation.call_count,1)  # no q-1 or unauthorized case evaluation
        self.assertEqual(summary['vectors'][0]['planned'],1)
        changed=deepcopy(frozen)
        criteria=changed['definitions']['q-0|t-0']['question']['definition']['criteria']
        changed['definitions']['q-0|t-0']['question']['definition']['criteria']=dict(reversed(list(criteria.items())))
        changed['freeze_hash']=digest({k:v for k,v in changed.items() if k!='freeze_hash'})
        with self.assertRaisesRegex(ValueError,'choice order'):
            a.analyze_export(root,self.base/'bad',stage='final',finalists=changed)

    def test_native_decision_parity_rounding_rejection_unclear(self):
        from laya_context_router.answers.interpret import interpret
        from laya_context_router.block_runtime.catalog import TypedRule
        from laya_context_router.block_runtime import Block, PreparedInput
        q={'definition':{'name':'action','type':'choice','instructions':'choose',
                         'criteria':{'explain':'Explain','unclear':'Unclear'}}}
        for gate in ([],[{'field':'probability_gap','op':'gte','value':0.2}],
                     [{'field':'answer_confidence','op':'gte','value':0.9}]):
            rule={'definition':{'name':'test','conditions':gate}}
            for label in ('explain','unclear'):
                raw={'answers':{'action':{'type':'choice','choice':label,
                     'probabilities':{'explain':0.60001,'unclear':0.39999}}}}
                body={k:v for k,v in q['definition'].items() if k!='name'}
                policy=TypedRule.from_dict({**rule['definition'],'question_type':'choice'})
                with patch('laya_context_router.answers.interpret.log'):
                    expected=interpret(raw,{'action':body},{'action':policy})['action']
                actual=a.native_decision(raw,q,rule)
                self.assertEqual({k:actual[k] for k in expected},expected)
                class Catalog:
                    def rule(self, reference): return policy
                block=Block({'name':'test','questions':{'action':{'definition':q['definition'],'rule_ref':'test'}}},
                    validate_input=lambda v:v,prepare_input=lambda v,qs:PreparedInput(v,qs,{}),
                    reduce=lambda decisions,state:decisions,validate_output=lambda v:v,catalog=Catalog())
                with patch('laya_context_router.block_runtime.runtime.predict',return_value=raw), patch('laya_context_router.block_runtime.runtime.log'):
                    native=block.run('input',config=None,registry=None).decisions['action']
                self.assertEqual({k:actual[k] for k in native},native)
        with self.assertRaises(ValueError):a.native_decision({'answers':{}},q,rule)

if __name__=='__main__':unittest.main()
