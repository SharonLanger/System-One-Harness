"""Read frozen RV2 evidence, filtering case IDs before opening predictions."""
import json
from pathlib import Path
from .protocol import digest, allowed_ids
from .scores import distribution, scores


def load(path):
    return json.loads(Path(path).read_text(),parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def model_identity(m):
    if m['mode']=='fixture': return m['model_fingerprint']
    assets={}
    for config in m['suite']['configurations']:
        signature=m['model_fingerprint'].get(config['id']) if m['model_fingerprint'] else None
        if signature is None: raise ValueError('model assets unavailable')
        # mtimes are transport metadata; actual content+size establishes asset identity.
        signature={name:{k:v for k,v in value.items() if k!='mtime_ns'} for name,value in signature.items()}
        name=config['model']
        if name in assets and assets[name]!=signature: raise ValueError('inconsistent assets for model identity')
        assets[name]=signature
    return assets


def manifest_identity(m, roles):
    return {'campaign_id':m['suite']['experiment_id'],'cases_hash':m['cases_hash'],'roles_hash':digest(roles),
            'labels':m['suite']['labels'],'source_hash':m['source_hash'],'model_fingerprint':model_identity(m),
            'mode':m['mode'],'runtime_versions':m['runtime_versions'],'adapter_hash':m['adapter_hash'],'rule_mode':m['rule_mode'],
            'questions':{q['id']:digest(q) for q in m['suite']['questions']}}


def compatible(identities):
    if not identities: raise ValueError('no round identities')
    base=identities[0]
    questions=dict(base['questions'])
    for current in identities[1:]:
        for key in ('campaign_id','cases_hash','roles_hash','labels','source_hash','model_fingerprint','mode','runtime_versions','adapter_hash','rule_mode'):
            # Model fingerprints may be keyed by configuration IDs; callers must preserve exact IDs across combined rounds.
            if current[key]!=base[key]: raise ValueError('incompatible rounds: '+key)
        for q in current['questions'].keys() & questions.keys():
            if current['questions'][q]!=questions[q]: raise ValueError('question definition changed')
        questions.update(current['questions'])
    return {**base,'questions':questions}


def extract_answer(answer, labels):
    available={}; p=None; raw=None; logits=None
    if not isinstance(answer,dict): return {'raw_label':None,'probabilities':None,'scores':None,'availability':{'answer':'missing or malformed'}}
    if answer.get('type')=='choice':
        raw=answer.get('choice'); values=answer.get('probabilities')
        if isinstance(values,dict) and set(values)==set(labels): p=[values[l] for l in labels]
        else: available['probabilities']='missing or noncanonical full class mapping'
    elif answer.get('type')=='noul' and labels==['yes','no']:
        v=answer.get('noul')
        if type(v) in (int,float): p=[v,1-v]; raw='yes' if v>=.5 else 'no'
        else: available['probabilities']='missing noul'
    else: available['probabilities']='unsupported answer type'
    z=answer.get('logits')
    if isinstance(z,dict) and set(z)==set(labels): logits=[z[l] for l in labels]
    else: available['logits']='not supplied as canonical raw class scores'
    if raw not in labels: available['raw_label']='missing or noncanonical'; raw=None
    calculated=None
    if p is not None:
        try: calculated=scores(p)
        except (TypeError,ValueError) as exc: available['probabilities']=str(exc); p=None
        if calculated:
            if logits is not None:
                try: calculated['raw_margin']=scores(p,logits)['raw_margin']
                except (TypeError,ValueError) as exc: available['logits']=str(exc);logits=None
            for channel in ('answer_confidence','confidence'):
                try: calculated[channel]=scores(p,**{channel:answer.get(channel)})[channel]
                except (TypeError,ValueError) as exc: available[channel]=str(exc)
    return {'raw_label':raw,'probabilities':p,'logits':logits,'scores':calculated,'availability':available,
            'answer_confidence':answer.get('answer_confidence'),'confidence':answer.get('confidence')}


def read_run(root, roles, stage, finalists=None):
    root=Path(root); m=load(root/'manifest.json')
    if m['cases_hash']!=digest(m['cases']) or m['suite_hash']!=digest(m['suite']): raise ValueError('manifest frozen hashes mismatch')
    identity=manifest_identity(m,roles)
    ids=allowed_ids(m['cases'],roles,stage,finalists,identity)
    if stage=='final':
        for cid,definition in finalists['definitions'].items():
            qid,cid_config=cid.split('|')
            q=next((q for q in m['suite']['questions'] if q['id']==qid),None)
            cfg=next((c for c in m['suite']['configurations'] if c['id']==cid_config),None)
            if q!=definition.get('question') or cfg!=definition.get('config'): raise ValueError('frozen finalist settings changed')
    cases=[c for c in m['cases']['cases'] if c['id'] in ids]  # before inference/checkpoint files are opened
    qmap={q['id']:q for q in m['suite']['questions']}; rows=[]
    excluded={(e['question_id'],e['rule_id'],e['config_id']) for e in m['suite'].get('exclusions',[])}
    for q in m['suite']['questions']:
        for cfg in m['suite']['configurations']:
            if stage=='final' and q['id']+'|'+cfg['id'] not in finalists['candidate_ids']: continue
            for case in cases:
                # Replay resolves through the native baseline checkpoint, never through a summary.
                r=m['suite']['baseline']['rule_id']
                checkpoint=root/'batches'/f"{q['id']}__{r}"/cfg['id']/'cases'/f"{case['id']}.json"
                if (q['id'],r,cfg['id']) in excluded: raise ValueError('analysis requires an included reference-rule checkpoint')
                saved=load(checkpoint) if checkpoint.exists() else {}
                for key,value in (('case_id',case['id']),('question_id',q['id']),('config_id',cfg['id'])):
                    if saved and saved.get(key)!=value: raise ValueError('checkpoint identity mismatch')
                rule=next(item for item in m['suite']['rules'] if item['id']==r)
                expected_iid=digest([q['id'],r if m['rule_mode']=='direct' else None,cfg['id'],case['id']])[:32]
                for key,value in (('input_hash',digest(case['input'])),('question_hash',digest(q)),('config_hash',digest(cfg)),('rule_hash',digest(rule)),('inference_id',expected_iid)):
                    if saved and saved.get(key)!=value: raise ValueError('stale checkpoint provenance: '+key)
                iid=saved.get('inference_id'); record={} 
                if iid:
                    if not isinstance(iid,str) or not iid.isalnum(): raise ValueError('unsafe inference ID')
                    ip=root/'inferences'/f'{iid}.json'
                    if ip.exists(): record=load(ip)
                    if record and record.get('id')!=iid: raise ValueError('inference identity mismatch')
                if record and record.get('requested_config')!=cfg: raise ValueError('inference requested config mismatch')
                usable=saved.get('status')=='completed' and record.get('status')=='completed' and not record.get('error')
                answer=(record.get('raw_response') or {}).get('answers',{}).get(q['definition']['name']) if usable else None
                extracted=extract_answer(answer,m['suite']['labels'])
                rows.append({**{k:case.get(k) for k in ('id','expected','label_status','split','source_family_id','noise_level','tags','desired_abstention')},
                    'case_id':case['id'],'question_id':q['id'],'config_id':cfg['id'],'inference_id':iid,
                    'status':saved.get('status','unattempted') if usable else ('missing_inference' if saved.get('status')=='completed' else saved.get('status','unattempted')),'native_accepted':saved.get('accepted'),
                    'requested_config':cfg,'effective_temperature':record.get('effective_temperature'),
                    'raw_response':record.get('raw_response') if usable else None,'frozen_input':case['input'],'question':q,'config':cfg,'native_rule':rule,'setting_availability':record.get('availability',{'inference':'missing'}),**extracted})
    return {'identity':identity,'stage':stage,'run_id':m['run_id'],'run_status':m['status'],
            'labels':m['suite']['labels'],'rows':rows,'allowed_case_ids':sorted(ids),
            'suite':m['suite'],'roles':roles,'cases_hash':m['cases_hash'],'finalists':finalists,'held_out_loaded':stage=='final','inference_count':len({r['inference_id'] for r in rows if r['inference_id']}),
            'logical_outcomes_planned':m['planned_counts']['logical_outcomes']}
