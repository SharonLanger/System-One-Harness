import json
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
