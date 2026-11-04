import unittest as _deferred_unittest
raise _deferred_unittest.SkipTest("Phase two: experiment dependency; see tests/deferred/README.md")

import copy
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from schema import load, validate
from reporting import collect, summaries, write_reports
ROOT = Path(__file__).resolve().parents[1]

class SchemaReportingChecks(unittest.TestCase):
    def setUp(self):
        text = (ROOT/'input-authoring.md').read_text()
        self.cases, self.suite = [json.loads(s) for s in re.findall(r'```json\n(.*?)\n```', text, re.S)]

    def test_authoring_and_invalid_mutations(self):
        validate(self.cases, self.suite)
        changes = [lambda c,s:s.update(repetitions=2), lambda c,s:s['labels'].reverse(), lambda c,s:s['baseline'].update(config_id='missing'), lambda c,s:c['cases'][0]['tags'].append('simple'), lambda c,s:c['cases'][0].update(id='../escape'), lambda c,s:c['cases'][0].update(label_status='out_of_scope'), lambda c,s:s['rules'][0]['definition']['conditions'][0].update(field='distance_from_boundary'), lambda c,s:s['configurations'][0].update(lang='he'), lambda c,s:s['questions'][1]['definition']['criteria'].update(fruit='changed')]
        for change in changes:
            c,s = copy.deepcopy(self.cases),copy.deepcopy(self.suite)
            change(c,s)
            with self.assertRaises(ValueError):
                validate(c,s)

    def test_noul_and_real_block_contracts(self):
        c,s=copy.deepcopy(self.cases),copy.deepcopy(self.suite)
        s['question_type']='noul';s['labels']=['yes','no']
        s['questions']=s['questions'][:1]
        s['questions'][0]['definition']={'name':'subject','type':'noul','instructions':'Is fruit present?'}
        for rule in s['rules']:
            rule['definition']['conditions'][0]['field']='distance_from_boundary'
        for case in c['cases']: case['expected']='yes'
        validate(c,s)
        for adapter,labels in [('requested-action',['explain','generate_tests','modify_code']),('context-scope',['method_only','called_methods','calling_methods','both_directions'])]:
            c,s=copy.deepcopy(self.cases),copy.deepcopy(self.suite)
            s['adapter']=adapter;s['labels']=labels;s['questions']=s['questions'][:1]
            s['questions'][0]['definition'].update(name=adapter.replace('-','_'),criteria={label:label for label in labels})
            for case in c['cases']: case.update(input={'prompt':'Explain this'},expected=labels[0])
            validate(c,s)
            c['cases'][0]['input']['unexpected']=True
            with self.assertRaises(ValueError): validate(c,s)

    def test_duplicate_json(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            p=Path(tmp)/'bad.json'; p.write_text('{"x":1,"x":2}')
            with self.assertRaises(ValueError): load(p)

    def test_four_cells_and_unscored(self):
        rows=[]
        for i,(raw,accepted) in enumerate([('fruit',True),('other',True),('fruit',False),('other',False)]):
            rows.append(dict(case_id=str(i),question_id='q',rule_id='r',config_id='c',status='completed',raw_label=raw,accepted=accepted,expected='fruit',label_status='settled',noise_level='regular',tags=['a','b'],split='held_out'))
        rows.append({**rows[0], 'case_id':'4','expected':None,'label_status':'taxonomy_pending'})
        result=summaries(rows)
        overall=result[0]
        self.assertEqual([overall[x] for x in ('AC','AW','RC','RW')],[1,1,1,1])
        self.assertEqual(overall['scored'],4)
        self.assertEqual(overall['unscored'],1)
        self.assertEqual(overall['coverage'],.5)
        self.assertEqual(sum(r['planned'] for r in result if r['group_type']=='noise_level'),5)
        self.assertEqual(sum(r['planned'] for r in result if r['group_type']=='tag'),10)
        self.assertIsNone(next(r for r in result if r['group_type']=='untagged')['raw_accuracy'])
        with self.assertRaises(ValueError): summaries(rows+[rows[0]])

    def test_partial_offline_collection_and_escaping(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            root=Path(tmp)
            (root/'manifest.json').write_text(json.dumps({'cases':self.cases,'suite':self.suite}))
            rows=collect(root)
            self.assertEqual(len(rows),24)
            self.assertTrue(all(r['status']=='unattempted' for r in rows))
            before=(root/'results.jsonl').read_bytes()
            collect(root)
            self.assertEqual(before,(root/'results.jsonl').read_bytes())
            rows[0]['tags']=['</script><img src=x onerror=alert(1)>']
            write_reports(root,rows)
            report=(root/'report.html').read_text()
            self.assertNotIn('<img src=x',report)
            self.assertIn('&lt;img',report)

if __name__ == '__main__': unittest.main()
