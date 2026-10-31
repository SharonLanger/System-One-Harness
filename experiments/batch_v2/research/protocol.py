"""Frozen source-family roles and selection boundaries. Sidecars never change RV2 inputs."""
import hashlib
import json
from pathlib import Path

ROLES = ('development','temperature','policy','held_out')


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def role_ids(cases, family_roles):
    out={role:set() for role in ROLES}; seen=set(); assignments={}
    for case in cases['cases']:
        cid=case['id']; family=case.get('source_family_id')
        if cid in seen or not family: raise ValueError('unique IDs and explicit source families required')
        seen.add(cid)
        if family not in family_roles: raise ValueError('family missing role: '+family)
        role=family_roles[family]; split=case.get('split')
        if role not in ROLES or split != ({'temperature':'calibration','policy':'calibration'}.get(role,role)):
            raise ValueError('role/split mismatch')
        if family in assignments and assignments[family]!=role: raise ValueError('family crosses roles')
        assignments[family]=role; out[role].add(cid)
    if set(family_roles)!=set(assignments): raise ValueError('role map contains unknown families')
    return out


def allowed_ids(cases, family_roles, stage, finalists=None, identity=None):
    roles=role_ids(cases,family_roles)
    if stage=='development': return roles['development']
    if stage in ('temperature','policy'): return roles[stage]
    if stage=='final':
        if not finalists or finalists.get('status')!='frozen' or not finalists.get('candidate_ids'):
            raise ValueError('frozen finalists required before held-out access')
        payload={k:v for k,v in finalists.items() if k!='freeze_hash'}
        if finalists.get('freeze_hash')!=digest(payload): raise ValueError('finalists hash mismatch')
        if identity is None or finalists.get('identity')!=identity: raise ValueError('finalists identity mismatch')
        return roles['held_out']
    raise ValueError('unknown analysis stage')


def freeze_finalists(candidate_ids, definitions, identity, *, selection_evidence, protocol_hash):
    if not candidate_ids or set(candidate_ids)!=set(definitions): raise ValueError('complete finalist definitions required')
    if selection_evidence['identity']!=identity or selection_evidence['stage']!='policy' or selection_evidence['run_status']!='completed':
        raise ValueError('final freeze requires complete policy-calibration evidence')
    q0=selection_evidence['suite']['baseline']['question_id']
    if not any(cid.split('|')[0]==q0 for cid in candidate_ids): raise ValueError('protected Q0 required')
    from .policies import evaluate, replay_native
    for cid,definition in definitions.items():
        rows=[r for r in selection_evidence['rows'] if r['question_id']+'|'+r['config_id']==cid]
        if not rows or any(r['status']!='completed' or r['label_status']=='settled' and (r['probabilities'] is None or r['raw_label'] is None) for r in rows):
            raise ValueError('incomplete finalist evidence')
        if definition.get('question')!=rows[0]['question'] or definition.get('config')!=rows[0]['config'] or not definition.get('policies'):
            raise ValueError('frozen definitions do not match evidence')
        for policy in definition['policies']:
            if policy.get('kind')=='native':
                if policy.get('rule') not in selection_evidence['suite']['rules']: raise ValueError('unknown frozen native rule')
                for row in rows:
                    replay_native(row['raw_response'],row['question'],policy['rule'],selection_evidence['suite'],row['config'],row['frozen_input'])
            elif policy.get('kind')=='experimental':
                evaluate([r['scores'] for r in rows if r['label_status']=='settled'],policy['conditions'])
            else: raise ValueError('unknown frozen policy kind')
    out={'status':'frozen','candidate_ids':sorted(candidate_ids),'definitions':definitions,'identity':identity,
         'selection_stage':selection_evidence['stage'],'selection_evidence_hash':digest(selection_evidence),'protocol_hash':protocol_hash}
    return {**out,'freeze_hash':digest(out)}


def validate_protocol(protocol, cases, roles, cases_path=None):
    role_ids(cases,roles)
    if protocol['cases_hash']!=digest(cases) or protocol['roles_hash']!=digest(roles): raise ValueError('frozen dataset/roles mismatch')
    if cases_path is not None and protocol['case_file_sha256']!=file_hash(cases_path): raise ValueError('case file bytes changed')
    if not protocol.get('campaign_id') or not protocol.get('critical_groups',[]) == list(dict.fromkeys(protocol.get('critical_groups',[]))):
        raise ValueError('invalid campaign protocol')
    return protocol
