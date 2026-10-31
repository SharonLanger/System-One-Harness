"""Golden/scientific contracts and adversarial role-boundary checks, entirely synthetic."""
import sys
sys.dont_write_bytecode=True
import copy
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from research.scores import scores,distribution,transform_temperature
from research.metrics import classification,probability_quality,gate,risk_coverage
from research.protocol import digest,role_ids,allowed_ids,freeze_finalists
from research.records import read_run,load,manifest_identity,compatible,model_identity
from research.temperature import refine,initial_grid
from research.policies import sweep,and_sweep,evaluate,replay_native
from research.analyze import analyze,paired
from research.next_round import retain_questions,propose_suite,decide,write_round,persist_finalists
from research.export import export_evidence,mark_published
from research.probe import assess,run_probe
import engine


class GoldenTests(unittest.TestCase):
    def test_majority_perfect_inverse_multiclass(self):
        m=classification(['no']*90+['yes']*10,['no']*100,['no','yes'])
        self.assertEqual(m['accuracy'],.9);self.assertEqual(m['balanced_accuracy_present_classes'],.5);self.assertEqual(m['mcc'],0);self.assertTrue(m['mcc_degenerate'])
        for predicted,want in [(['a','b'],1),(['b','a'],-1)]: self.assertEqual(classification(['a','b'],predicted,['a','b'])['mcc'],want)
        m=classification(['a','a','b','c'],['a','b','b','c'],['a','b','c'])
        self.assertEqual(m['confusion'],[[1,1,0],[0,1,0],[0,0,1]]);self.assertAlmostEqual(m['accuracy'],.75)
        self.assertIsNone(classification([],[],['a','b'])['mcc'])
        self.assertFalse(classification(['a'],['a'],['a','b'])['comparable_all_classes'])
        with self.assertRaises(ValueError): classification(['a'],['x'],['a','b'])

    def test_probabilities_and_doctor(self):
        self.assertAlmostEqual(scores([.7,.2,.1])['doctor'],.54)
        self.assertAlmostEqual(scores([.25]*4)['doctor'],.25)
        self.assertAlmostEqual(scores([.5,.5])['normalized_entropy'],1)
        self.assertEqual(scores([.7,.3],answer_confidence=.4)['answer_confidence'],.4)
        self.assertEqual(scores([.7,.3],[3,1])['raw_margin'],2)
        p,meta=distribution([.5002,.5002]);self.assertTrue(meta['normalization_correction']);self.assertEqual(sum(p),1)
        for p in ([.9,.9],[float('nan'),0],[0,0],[-.1,1.1]):
            with self.assertRaises(ValueError): scores(p)
        good=probability_quality(['a'],[[.9,.1]],['a','b']);bad=probability_quality(['a'],[[.01,.99]],['a','b'])
        self.assertLess(good['strict_nll'],bad['strict_nll']);self.assertAlmostEqual(good['brier_sum'],.02)
        zero=probability_quality(['a'],[[0,1]],['a','b']);self.assertIsNone(zero['strict_nll']);self.assertEqual(zero['strict_nll_status'],'infinite_zero_probability');self.assertGreater(zero['clipped_nll_diagnostic'],0)

    def test_gate_and_tied_aurc(self):
        c=[True,False]
        for accepted,cells in [([True,True],[1,1,0,0]),([False,False],[0,0,1,1]),([True,False],[1,0,0,1]),([False,True],[0,1,1,0])]:
            g=gate(c,accepted);self.assertEqual([g[k] for k in ('AC','AW','RC','RW')],cells)
        self.assertIsNone(gate(c,[False,False])['accepted_error'])
        curve=risk_coverage(c,[.5,.5]);self.assertEqual(len(curve['points']),2);self.assertEqual(curve['grouped_step_aurc'],.5)
        self.assertEqual(risk_coverage(c,[1,0])['grouped_step_aurc'],.25)
        self.assertEqual(risk_coverage(c,[0,1])['grouped_step_aurc'],.75)
        s=sweep(c,[{'doctor':.5},{'doctor':.5}],'doctor');self.assertIsNone(s['risk_views']['0.01']);self.assertEqual(s['coverage_views']['0.25']['coverage'],1)
        self.assertIsNone(and_sweep(c,[{'confidence':.9,'probability_gap':.5}]*2)['aurc'])
        self.assertFalse(sweep(c,[{},{}],'raw_margin')['available'])
        self.assertEqual(evaluate([{'doctor':.5}],[{'field':'doctor','op':'gt','value':.5}]),[False])

    def test_temperature_curves_and_argmax(self):
        for t in (.5,1,2,5): self.assertEqual(transform_temperature([.7,.2,.1],t,source_temperature=1).index(max(transform_temperature([.7,.2,.1],t,source_temperature=1))),0)
        with self.assertRaises(ValueError):transform_temperature([0,1],2,source_temperature=1)
        curve=lambda ts,fn:[{'temperature':t,'nll':fn(t),'nll_status':'finite'} for t in ts]
        ts=[.5,1,1.5,2,3,5]
        result=refine({'q':curve(ts,lambda t:(t-1)**2)},0,(.5,5));self.assertIn(1.1,result['temperatures']);self.assertNotIn(5,result['temperatures'])
        self.assertEqual(refine({'q':curve(ts,lambda t:1)},0,(.5,5))['questions']['q']['status'],'flat_plateau')
        tied=refine({'q':curve(ts,lambda t:0 if t in (1,3) else 1)},0,(.5,5));self.assertEqual(len(tied['questions']['q']['regions']),2)
        boundary=refine({'q':curve(ts,lambda t:t)},0,(.5,5));self.assertEqual(boundary['questions']['q']['boundary_note'],'best within supported range')
        self.assertTrue(refine({'q':[]},3,(.5,5))['stop'])
        b=refine({'q':[{'temperature':t,'nll_status':'infinite_zero_probability','brier':(t-1)**2} for t in ts]},0,(.5,5));self.assertEqual(b['questions']['q']['objective'],'brier')
        self.assertNotIn(5,initial_grid([.5,1,2])['temperatures'])


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases=load(HERE/'examples/generic-choice/cases.json');cls.suite=load(HERE/'examples/generic-choice/suite.json')
        # Reuse existing three mechanical inputs; no new experiment cases are authored.
        cls.roles={c['source_family_id']:'development' for c in cls.cases['cases']}
        cls.root=engine.create(cls.cases,cls.suite,'fixture','replay',{})
        if engine.run(cls.root):raise RuntimeError('fixture failed')

    def test_reader_native_replay_and_reports(self):
        e=read_run(self.root,self.roles,'development');self.assertEqual(len(e['rows']),12);self.assertEqual(e['inference_count'],12)
        self.assertTrue(all(r['probabilities'] is not None for r in e['rows']))
        report=analyze(e,self.roles);self.assertEqual(len(report['vectors']),4)
        m=load(self.root/'manifest.json');q=m['suite']['questions'][0];cfg=m['suite']['configurations'][0];rule=m['suite']['rules'][0]
        row=next(r for r in e['rows'] if r['question_id']==q['id'] and r['config_id']==cfg['id'])
        raw=load(self.root/'inferences'/f"{row['inference_id']}.json")['raw_response']
        self.assertEqual(replay_native(raw,q,rule,m['suite'],cfg,row['frozen_input'])['decided'],row['native_accepted'])
        payload=load(self.root/'inferences'/f"{row['inference_id']}.json")['payload']
        self.assertEqual(set(payload),{'text','questions','predict_kwargs'});self.assertNotIn('expected',payload['text']);self.assertNotIn('tags',payload['text'])

    def test_filter_before_open_and_finalists(self):
        roles=dict(self.roles);cases=copy.deepcopy(self.cases);held=cases['cases'][-1];held['split']='held_out';roles[held['source_family_id']]='held_out'
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);m=load(self.root/'manifest.json');m['cases']=cases;m['cases_hash']=digest(cases);(root/'manifest.json').write_text(json.dumps(m))
            import research.records as reader
            real=reader.load;opened=[]
            def guarded(path):
                opened.append(str(path));
                if held['id']+'.json' in str(path):raise AssertionError('held-out checkpoint opened')
                return real(path)
            with patch.object(reader,'load',side_effect=guarded): e=read_run(root,roles,'development')
            self.assertNotIn(held['id'],e['allowed_case_ids'])
            with self.assertRaisesRegex(ValueError,'frozen finalists'):read_run(root,roles,'final')
            identity=manifest_identity(m,roles)
            definition={'question':self.suite['questions'][0],'config':self.suite['configurations'][0],'policies':[{'id':'doctor','kind':'experimental','conditions':[{'field':'doctor','op':'gte','value':.5}]}]}
            # Construct frozen metadata to exercise reader gating; full freeze validation is tested separately.
            f={'status':'frozen','candidate_ids':['q-baseline|sdk-default'],'definitions':{'q-baseline|sdk-default':definition},'identity':identity};f['freeze_hash']=digest(f)
            final=read_run(root,roles,'final',f);self.assertEqual(len(final['rows']),1);self.assertEqual(final['rows'][0]['case_id'],held['id'])
            f['definitions']['q-baseline|sdk-default']={}
            with self.assertRaisesRegex(ValueError,'hash mismatch'):read_run(root,roles,'final',f)

    def test_role_exclusivity_and_identity(self):
        c=copy.deepcopy(self.cases);roles=dict(self.roles)
        family=c['cases'][0]['source_family_id']
        for case in c['cases']:
            if case['source_family_id']==family:case['split']='calibration'
        roles[family]='temperature'
        self.assertEqual(allowed_ids(c,roles,'temperature'),{x['id'] for x in c['cases'] if x['source_family_id']==family})
        roles[c['cases'][0]['source_family_id']]='policy';self.assertEqual(allowed_ids(c,roles,'temperature'),set())
        roles[c['cases'][0]['source_family_id']]='held_out'
        with self.assertRaises(ValueError):role_ids(c,roles)
        m=load(self.root/'manifest.json');m['mode']='live';assets={'model.safetensors':{'size':3,'mtime_ns':1,'sha256':'fixed'}};m['model_fingerprint']={cfg['id']:assets for cfg in m['suite']['configurations']}
        a=manifest_identity(m,self.roles);m2=copy.deepcopy(m);m2['suite']['configurations'][0]['id']='new-id';m2['model_fingerprint']['new-id']=m2['model_fingerprint'].pop('sdk-default')
        b=manifest_identity(m2,self.roles);compatible([a,b])
        for key in ('cases_hash','roles_hash','source_hash','mode'):
            bad=copy.deepcopy(b);bad[key]='changed'
            with self.assertRaises(ValueError):compatible([a,bad])
        bad=copy.deepcopy(b);bad['questions']['q-baseline']='changed'
        with self.assertRaises(ValueError):compatible([a,bad])
        bad=copy.deepcopy(b);bad['model_fingerprint']={'changed':1}
        with self.assertRaises(ValueError):compatible([a,bad])

    def test_deterministic_decision_suite_and_round(self):
        e=read_run(self.root,self.roles,'development');d=retain_questions(e,self.roles,'q-baseline',samples=100)
        self.assertIn('q-baseline',d['questions']);self.assertEqual(d,retain_questions(e,self.roles,'q-baseline',samples=100))
        proposed=propose_suite(self.cases,self.suite,d['questions'],[.5,1,2],[.5,1,2]);self.assertEqual(proposed['baseline'],self.suite['baseline'])
        broken=copy.deepcopy(e);broken['rows'][0]['status']='timeout';self.assertIn('q-baseline|sdk-default',retain_questions(broken,self.roles,'q-baseline',samples=100)['ineligible_vectors'])
        protocol={'campaign_id':self.suite['experiment_id'],'cases_hash':digest(self.cases),'roles_hash':digest(self.roles),'case_file_sha256':'synthetic','critical_groups':[],'bootstrap_samples':100}
        record,suite=decide(protocol,self.cases,self.roles,e,self.suite,[],[1],[1])
        self.assertEqual((record,suite),decide(protocol,self.cases,self.roles,e,self.suite,[],[1],[1]))
        with tempfile.TemporaryDirectory() as temp:
            write_round(temp,record,suite);journal=(Path(temp)/'run-journal.md').read_bytes()
            with self.assertRaises(ValueError):write_round(temp,record,suite)
            self.assertEqual(journal,(Path(temp)/'run-journal.md').read_bytes())
        e['run_status']='partial'
        with self.assertRaisesRegex(ValueError,'incomplete'):decide(protocol,self.cases,self.roles,e,self.suite,[],[1],[1])

    def test_export_inventory_reproduce_and_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            compact=Path(temp)/'compact';sealed=Path(temp)/'sealed'
            manifest=export_evidence(self.root,self.roles,'development',compact,sealed,source_commit='synthetic-only')
            from research.protocol import file_hash
            for name,sha in manifest['files'].items():self.assertEqual(file_hash(compact/name),sha)
            self.assertEqual(file_hash(sealed/'full-raw-run.tar.gz'),manifest['sealed_archive']['sha256'])
            self.assertFalse(manifest['held_out_values_included']);self.assertEqual(manifest['handoff_status'],'local_only_pending_publication')
            e=load(compact/'predictions.json');self.assertEqual(analyze(e,self.roles),load(compact/'analysis.json'))
            mark_published(compact,'https://example.invalid/compact','https://example.invalid/sealed')
            self.assertEqual(load(compact/'evidence-manifest.json')['handoff_status'],'published_references_recorded')

    def test_stale_and_missing_evidence_never_selects(self):
        import shutil
        from research.records import extract_answer
        answer={'type':'choice','choice':'fruit','probabilities':{'fruit':.7,'other':.3},'confidence':'bad','logits':{'fruit':'bad','other':0}}
        extracted=extract_answer(answer,['fruit','other']);self.assertEqual(extracted['probabilities'],[.7,.3]);self.assertIn('confidence',extracted['availability']);self.assertIn('logits',extracted['availability'])
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'run';shutil.copytree(self.root,root)
            checkpoint=root/'batches'/'q-baseline__r-baseline'/'sdk-default'/'cases'/'case-01.json';original=load(checkpoint)
            for field in ('input_hash','question_hash','config_hash','rule_hash','inference_id'):
                bad=copy.deepcopy(original);bad[field]='stale';checkpoint.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):read_run(root,self.roles,'development')
            checkpoint.write_text(json.dumps(original));iid=original['inference_id'];ip=root/'inferences'/f'{iid}.json';inference=load(ip)
            inference['requested_config']['temperature']=99;ip.write_text(json.dumps(inference))
            with self.assertRaisesRegex(ValueError,'requested config'):read_run(root,self.roles,'development')
            ip.unlink();e=read_run(root,self.roles,'development');self.assertTrue(any(r['status']=='missing_inference' for r in e['rows']))

    def test_policy_denominators_and_freeze(self):
        e=read_run(self.root,self.roles,'development');roles={family:'policy' for family in self.roles};e['stage']='policy';e['roles']=roles
        for r in e['rows']:r['split']='calibration'
        e['identity']['roles_hash']=digest(roles)
        report=analyze(e,roles);self.assertTrue(report['vectors']['q-baseline|sdk-default']['experimental_policies']['doctor']['available'])
        self.assertIn('class:fruit',report['vectors']['q-baseline|sdk-default']['policy_group_metrics']['doctor:1'])
        cid='q-baseline|sdk-default';row=next(r for r in e['rows'] if r['question_id']+'|'+r['config_id']==cid)
        definition={'question':row['question'],'config':row['config'],'policies':[{'id':'doctor','kind':'experimental','conditions':[{'field':'doctor','op':'gte','value':.6}]}]}
        f=freeze_finalists([cid],{cid:definition},e['identity'],selection_evidence=e,protocol_hash='fixture-protocol')
        final=copy.deepcopy(e);final['stage']='final';final['finalists']=f;final['rows']=[r for r in final['rows'] if r['question_id']+'|'+r['config_id']==cid]
        result=analyze(final,roles);self.assertIn('doctor',result['vectors'][cid]['frozen_policies']);self.assertEqual(result['vectors'][cid]['experimental_policies'],{})
        bad=copy.deepcopy(definition);bad['config']['temperature']=99
        with self.assertRaises(ValueError):freeze_finalists([cid],{cid:bad},e['identity'],selection_evidence=e,protocol_hash='fixture')
        e['rows'][0]['probabilities']=None;e['rows'][0]['scores']=None
        self.assertFalse(analyze(e,roles)['vectors'][cid]['experimental_policies']['available'])
        with self.assertRaises(ValueError):freeze_finalists([cid],{cid:definition},e['identity'],selection_evidence=e,protocol_hash='fixture')

    def test_multi_round_refinement_stop_and_campaign_boundary(self):
        from research.temperature import curves_from_evidence
        e=read_run(self.root,self.roles,'development');cases=copy.deepcopy(self.cases)
        roles={'apple-food':'temperature','apple-company':'development'}
        for case in cases['cases']:
            if case['source_family_id']=='apple-food':case['split']='calibration'
        identity=copy.deepcopy(e['identity']);identity['cases_hash']=digest(cases);identity['roles_hash']=digest(roles)
        dev=copy.deepcopy(e);dev['identity']=identity;dev['rows']=[r for r in dev['rows'] if roles[r['source_family_id']]=='development']
        protocol={'campaign_id':self.suite['experiment_id'],'cases_hash':digest(cases),'roles_hash':digest(roles),'case_file_sha256':'synthetic','critical_groups':[],
                  'bootstrap_samples':50,'supported_range':[.5,5],'refinement_number':0}
        def temperature_round(ts,runid,flat=False):
            out=copy.deepcopy(e);out.update(stage='temperature',identity=copy.deepcopy(identity),run_id=runid)
            out['suite']=copy.deepcopy(self.suite);base=out['suite']['configurations'][0]
            out['suite']['configurations']=[base]+[{**base,'id':'t-'+str(t).replace('.','-'),'temperature':t} for t in ts if t is not None]
            rows=[]
            for q in out['suite']['questions']:
                for cfg in out['suite']['configurations']:
                    for r in e['rows']:
                        if r['question_id']!=q['id'] or r['config_id']!='sdk-default' or roles[r['source_family_id']]!='temperature':continue
                        row=copy.deepcopy(r);row.update(config_id=cfg['id'],config=cfg,requested_config=cfg,inference_id=runid+cfg['id']+r['case_id'])
                        t=cfg['temperature'];p=.8 if flat else math.exp(-(.2+(t-1)**2)) if t is not None else .7
                        row['probabilities']=[p,1-p];row['scores']=scores(row['probabilities'],confidence=.9);rows.append(row)
            out['rows']=rows;return out
        broad=temperature_round([.5,1,1.5,2,3,5],'broad')
        first=curves_from_evidence([broad],roles);proposal=refine(first,0,(.5,5));self.assertIn(1.1,proposal['temperatures'])
        second=temperature_round(proposal['temperatures'],'refined')
        combined=curves_from_evidence([broad,second],roles);self.assertTrue(any(r.get('excluded_repeat_diagnostics') for r in combined['q-baseline']))
        next_proposal=refine(combined,1,(.5,5));self.assertTrue(next_proposal['temperatures'])
        protocol['refinement_number']=1
        record,suite=decide(protocol,cases,roles,dev,self.suite,[],[],[None]+[round(.5+i*.02,2) for i in range(226)],temperature_evidence=[broad,second])
        self.assertTrue(record['temperature_decision']['temperatures'])
        bad=copy.deepcopy(broad);bad['identity']['cases_hash']='another-campaign'
        with self.assertRaisesRegex(ValueError,'incompatible'):decide(protocol,cases,roles,dev,self.suite,[],[],[None,1],temperature_evidence=[bad])
        for cap,flat in ((0,True),(3,False)):
            p=copy.deepcopy(protocol);p['refinement_number']=cap
            evidence=temperature_round([.5,1,1.5,2,3,5],'flat-or-cap',flat=flat)
            rec,suite=decide(p,cases,roles,dev,self.suite,[],[],[None,.5,1,1.5,2,3,5],temperature_evidence=[evidence])
            self.assertTrue(rec['temperature_decision']['stop']);self.assertGreater(len(suite['configurations']),1)
            self.assertIn(1,rec['temperature_decision']['carry_forward_temperatures'])
            numeric_baseline=copy.deepcopy(self.suite);numeric_baseline['baseline']['config_id']='explicit-one'
            carried=propose_suite(cases,numeric_baseline,rec['decision']['questions'],rec['temperature_decision']['carry_forward_temperatures'],[None,.5,1,1.5,2,3,5])
            self.assertTrue(any(c['temperature'] is None for c in carried['configurations']))
        broken=copy.deepcopy(broad);broken['rows'][0]['probabilities']=None
        with self.assertRaisesRegex(ValueError,'incomplete'):curves_from_evidence([broken],roles)

    def test_unsettled_execution_and_missing_final_channel(self):
        e=read_run(self.root,self.roles,'development')
        for row in e['rows']:
            if row['case_id']=='case-01':row['label_status']='insufficient_context';row['expected']=None
        self.assertIn('q-baseline',retain_questions(e,self.roles,'q-baseline',samples=50)['questions'])
        roles={family:'policy' for family in self.roles};e['stage']='policy';e['roles']=roles;e['identity']['roles_hash']=digest(roles)
        cid='q-baseline|sdk-default';row=next(r for r in e['rows'] if r['question_id']+'|'+r['config_id']==cid)
        definition={'question':row['question'],'config':row['config'],'policies':[{'id':'confidence','kind':'experimental','conditions':[{'field':'confidence','op':'gte','value':.5}]}]}
        frozen=freeze_finalists([cid],{cid:definition},e['identity'],selection_evidence=e,protocol_hash='synthetic')
        e.update(stage='final',finalists=frozen);e['rows']=[r for r in e['rows'] if r['question_id']+'|'+r['config_id']==cid]
        for r in e['rows']:r['scores']['confidence']=None
        final=analyze(e,roles);self.assertFalse(final['vectors'][cid]['frozen_policies']['confidence']['available'])

    def test_probe_is_explicit_and_synthetic_assessment(self):
        with self.assertRaises(ValueError):run_probe(self.cases,self.suite,[1],max_calls=1,output='unused')
        with patch('research.probe.platform.system',return_value='Linux'):
            with self.assertRaisesRegex(ValueError,'Mac'):run_probe(self.cases,self.suite,[1],max_calls=1,output='unused',allow_live=True)
        observations=[]
        for t in (1,2):
            p=transform_temperature([.7,.3],t,source_temperature=1)
            observations.append({'status':'completed','requested_temperature':t,'answer':{'type':'choice','choice':'a','probabilities':dict(zip(['a','b'],p))}})
        ordinary=assess(observations,['a','b']);self.assertFalse(ordinary['offline_verified']);self.assertEqual(ordinary['route'],'live_temperature_matrix')
        verified=assess(observations,['a','b'],known_source_temperature=1,precision_verified=True,verification_evidence={'precision_reference':'synthetic-exact','source_temperature_reference':'synthetic-t0'});self.assertTrue(verified['offline_verified'])
        observations[1]['answer']['probabilities']={'a':.9,'b':.1};self.assertFalse(assess(observations,['a','b'],known_source_temperature=1,precision_verified=True,verification_evidence={'precision_reference':'synthetic-exact','source_temperature_reference':'synthetic-t0'})['offline_verified'])

if __name__=='__main__':unittest.main()
