import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
import export_v2_results as e


def fixture(root,n=3,nq=2,nc=2):
    cases={'schema_version':1,'dataset_id':'demo','dataset_version':'2','cases':[{'id':f'case-{i:03}','input':f'Explain input {i}','expected':'unclear','label_status':'settled','noise_level':'regular','tags':[],'source_family_id':f'family-{i}','split':'development'} for i in range(n)]}
    suite={'schema_version':1,'dataset_id':'demo','dataset_version':'2','question_type':'choice','experiment_id':'demo','adapter':'generic-question','questions':[{'id':f'q-{i}','variant_kind':'baseline' if i==0 else 'wording','definition':{'name':'action','type':'choice','instructions':'Choose','criteria':{'explain':'Explain','unclear':'Cannot decide'}}} for i in range(nq)],'rules':[{'id':'r0','definition':{'name':'free','conditions':[]}}], 'configurations':[{'id':f't-{i}','temperature':None if i==0 else float(i),'lang':'en','model':'fake'} for i in range(nc)],'labels':['explain','unclear'],'baseline':{'question_id':'q-0','rule_id':'r0','config_id':'t-0'}}
    m={'schema_version':1,'suite':suite,'cases':cases,'suite_hash':e.legacy_hash(suite),'cases_hash':e.legacy_hash(cases),'rule_mode':'replay','mode':'fixture','status':'completed','source_revision':{'revision':'fixture'}}
    root.mkdir(); (root/'inferences').mkdir(); e.write(root/'manifest.json',m)
    for q in suite['questions']:
        for c in suite['configurations']:
            for case in cases['cases']:
                iid=e.legacy_hash([q['id'],None,c['id'],case['id']])[:32]
                raw={'id':iid,'status':'completed','error':None,'raw_response':{'answers':{'action':{'type':'choice','choice':'unclear','probabilities':{'explain':e.Decimal('0.123456789012345678901'),'unclear':e.Decimal('0.876543210987654321099')}}},'logs':'SDK field retained'},'payload':e.expected_payload(case,q,c),'requested_config':c,'inference_seconds':0.3,'load_seconds':1,'baseline_rule_seconds':0.1,'availability':{'tokens':'unknown'},'effective_temperature':None,'logs':['debug removal'],'baseline_result':{'duplicate':'removed'},'new_sdk_metadata':{'keep':True}}
                e.write(root/'inferences'/f'{iid}.json',raw)
    return m


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name);self.source=self.base/'source';fixture(self.source)
    def run_export(self,**kw):
        return e.export_run(self.source,self.base/'exports',source_stopped=True,**kw)
    def test_round_trip_partitions_precision_source_unchanged(self):
        before=e.source_snapshot(self.source,None);dest=self.run_export(); info=e.read(dest/'export.json')
        self.assertEqual((info['found'],info['planned'],len(info['partitions'])),(12,12,4))
        self.assertEqual(before,e.source_snapshot(self.source,None))
        self.assertEqual(info['found'],info['success']+info['error'])
        self.assertEqual(info['planned'],info['found']+info['missing'])
        self.assertEqual(info['export_bytes'],sum(p.stat().st_size for p in dest.rglob('*') if p.is_file()))
        part=info['partitions'][0];record=json.loads((dest/part['path']).read_text().splitlines()[0],parse_float=e.Decimal)
        self.assertEqual(record['raw_response']['answers']['action']['probabilities']['explain'],e.Decimal('0.123456789012345678901'))
        self.assertEqual(record['raw_response']['logs'],'SDK field retained');self.assertNotIn('logs',record['source_metadata'])
        self.assertTrue(record['source_metadata']['new_sdk_metadata']['keep'])
        self.assertNotEqual(info['config_folders']['t-0'],info['config_folders']['t-1'])
    def test_long_response_and_empty_export_directory_collision(self):
        path=next((self.source/'inferences').glob('*.json'));raw=e.read(path)
        raw['raw_response']['long']='x'*200000;e.write(path,raw)
        first=self.run_export();second=self.run_export()
        self.assertNotEqual(first,second)
        self.assertTrue(any('x'*200000 in p.read_text() for p in second.rglob('*.jsonl')))
    def test_excluded_whole_pair(self):
        m=e.read(self.source/'manifest.json',False)
        m['suite']['exclusions']=[{'question_id':'q-1','rule_id':'r0','config_id':'t-1','reason':'excluded'}]
        m['suite_hash']=e.legacy_hash(m['suite']);e.write(self.source/'manifest.json',m)
        for case in m['cases']['cases']:
            iid=e.legacy_hash(['q-1',None,'t-1',case['id']])[:32]
            (self.source/'inferences'/f'{iid}.json').unlink()
        info=e.read(self.run_export()/'export.json')
        self.assertEqual((info['found'],info['planned'],len(info['partitions'])),(9,9,3))
    def test_errors_partial_and_stale_status(self):
        paths=list((self.source/'inferences').glob('*.json'));paths[0].unlink();raw=e.read(paths[1]);raw.update(status='error',error={'type':'Oops','message':'failed'},payload=None,raw_response=None);e.write(paths[1],raw)
        m=e.read(self.source/'manifest.json');m['status']='running';e.write(self.source/'manifest.json',m)
        info=e.read(self.run_export()/'export.json');self.assertEqual((info['missing'],info['error']),(1,1));self.assertEqual(info['export_status'],'complete');self.assertEqual(info['collection_status'],'partial');self.assertEqual(info['source_execution_status'],'running')
    def test_requires_stopped_and_external_destination(self):
        with self.assertRaises(ValueError):e.export_run(self.source,self.base/'exports')
        with self.assertRaises(ValueError):e.export_run(self.source,self.source/'bad',source_stopped=True)
    def test_payload_conflict_no_publication(self):
        path=next((self.source/'inferences').glob('*.json'));raw=e.read(path);raw['payload']['text']='wrong';e.write(path,raw)
        with self.assertRaisesRegex(ValueError,'request differs'):self.run_export()
        self.assertEqual(list((self.base/'exports').iterdir()),[])
    def test_choice_order_conflict(self):
        path=next((self.source/'inferences').glob('*.json'));raw=e.read(path)
        criteria=raw['payload']['questions']['action']['criteria']
        raw['payload']['questions']['action']['criteria']=dict(reversed(list(criteria.items())))
        e.write(path,raw)
        with self.assertRaisesRegex(ValueError,'Choice order'):self.run_export()
    def test_hash_conflict(self):
        m=e.read(self.source/'manifest.json');m['suite_hash']='bad';e.write(self.source/'manifest.json',m)
        with self.assertRaisesRegex(ValueError,'hash mismatch'):self.run_export()
    def test_unknown_inference(self):
        e.write(self.source/'inferences'/'unknown.json',{})
        with self.assertRaisesRegex(ValueError,'Unknown'):self.run_export()
    def test_disk_failure_no_publication(self):
        with patch.object(e,'write',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.run_export()
        self.assertEqual(list((self.base/'exports').iterdir()),[])
    def test_concurrent_change_rejected(self):
        original=e.source_snapshot;count=0
        def snapshot(*args):
            nonlocal count
            count+=1
            return original(*args) if count==1 else 'changed'
        with patch.object(e,'source_snapshot',side_effect=snapshot):
            with self.assertRaisesRegex(ValueError,'changed'):self.run_export()
    def test_lossless_numbers_and_duplicate_keys(self):
        p=self.base/'decimal.json';p.write_text('{"v":0.10000000000000000000001}')
        self.assertEqual(e.encode(e.read(p)),'{"v":0.10000000000000000000001}')
        p.write_text('{"a":1,"a":2}')
        with self.assertRaises(ValueError):e.read(p)
    def test_unsupported_direct(self):
        m=e.read(self.source/'manifest.json');m['rule_mode']='direct';e.write(self.source/'manifest.json',m)
        with self.assertRaisesRegex(ValueError,'replay only'):self.run_export()
    def test_duplicate_temperature_folder(self):
        m=e.read(self.source/'manifest.json',False);m['suite']['configurations'][1]['temperature']=None;m['suite_hash']=e.legacy_hash(m['suite']);e.write(self.source/'manifest.json',m)
        with self.assertRaisesRegex(ValueError,'Ambiguous'):self.run_export()

if __name__=='__main__':unittest.main()
