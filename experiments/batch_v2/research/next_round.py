"""Conservative decisions and append-only round records; never launches inference."""
import copy
import json
from pathlib import Path
from .protocol import digest, validate_protocol, freeze_finalists
from .analyze import summarize, paired
from .temperature import refine


def retain_questions(evidence, roles, baseline, critical_groups=(), tolerance=.02, seed=1729, samples=2000, min_families=5):
    if evidence['stage']!='development': raise ValueError('question decisions require development-only evidence')
    grouped={}
    for row in evidence['rows']:
        if roles[row['source_family_id']]!='development': raise ValueError('forbidden role in question selection')
        grouped.setdefault(row['question_id']+'|'+row['config_id'],[]).append(row)
    valid={k:rs for k,rs in grouped.items() if summarize(rs,evidence['labels'])['complete'] and all(r['label_status']!='settled' or r['raw_label'] in evidence['labels'] for r in rs)}
    if not valid: raise ValueError('no complete development vectors')
    valid={k:rs for k,rs in valid.items() if any(r['label_status']=='settled' for r in rs)}
    if not valid: raise ValueError('no settled development support')
    metrics={k:summarize(rs,evidence['labels'])['classification'] for k,rs in valid.items()}
    protected={k for k in valid if k.split('|')[0]==baseline}
    if not protected: raise ValueError('complete protected Q0 evidence missing')
    for metric in ('balanced_accuracy_present_classes','mcc'):
        best=max(m[metric] for m in metrics.values()); protected.update(k for k,m in metrics.items() if m[metric]>=best-tolerance)
    # Gate trade-offs remain visible; any native empirical frontier candidate is protected.
    gates={k:summarize(rs,evidence['labels'])['runner_native'] for k,rs in valid.items()}
    for k,g in gates.items():
        if g['accepted_error'] is not None and not any(h['accepted_error'] is not None and h['coverage']>=g['coverage'] and h['accepted_error']<g['accepted_error'] for h in gates.values()): protected.add(k)
    for tag in critical_groups:
        stats={k:summarize([r for r in rs if tag in r.get('tags',[])],evidence['labels']) for k,rs in valid.items()}
        if any(s['classification']['n']==0 for s in stats.values()): protected.update(valid); continue
        best=max(s['classification']['accuracy'] for s in stats.values())
        protected.update(k for k,s in stats.items() if s['classification']['accuracy']>=best-tolerance)
    retained=set(protected); comparisons={}; discarded={}
    for key,rs in valid.items():
        if key in protected: continue
        worse=False
        for winner in sorted(protected):
            try: p=paired([r for r in valid[winner] if r['label_status']=='settled'],[r for r in rs if r['label_status']=='settled'],evidence['labels'],seed=seed,samples=samples)
            except ValueError: continue
            comparisons[winner+' -> '+key]=p
            enough=p.get('available') and p['family_count']>=min_families and p['comparable_all_classes']
            bad=enough and all(p['intervals'][metric][1]<-tolerance for metric in ('balanced_accuracy_present_classes','mcc'))
            # Any possible class benefit, absent class, or sparse critical group prevents pruning.
            bad=bad and all(v is not None and v[1]<=tolerance for v in p.get('recall_intervals',{}).values())
            for tag in critical_groups:
                a=[r for r in valid[winner] if tag in r.get('tags',[])]; b=[r for r in rs if tag in r.get('tags',[])]
                try: subgroup=paired(a,b,evidence['labels'],seed=seed,samples=samples)
                except ValueError: bad=False; continue
                if not subgroup.get('available') or subgroup['family_count']<min_families or not subgroup['comparable_all_classes'] or any(v is None or v[1]>tolerance for v in subgroup['recall_intervals'].values()): bad=False
            if bad: worse=True; discarded[key]='paired consistently worse; no demonstrated class/critical benefit'; break
        if not worse: retained.add(key)
    return {'questions':sorted({k.split('|')[0] for k in retained}|{baseline}),
        'retained_vectors':sorted(retained),'protected_vectors':sorted(protected),'discarded_vectors':discarded,
        'ineligible_vectors':sorted(set(grouped)-set(valid)), 'comparisons':comparisons,
        'reason':'keep both unless paired family evidence resolves comparison', 'seed':seed,'samples':samples,'tolerance':tolerance,'min_families':min_families}


def propose_suite(cases, suite, questions, temperatures, supported, baseline_config=None):
    from schema import validate
    out=copy.deepcopy(suite); q0=suite['baseline']['question_id']; wanted=set(questions)|{q0}
    if not wanted <= {q['id'] for q in suite['questions']}: raise ValueError('unknown question')
    out['questions']=[q for q in out['questions'] if q['id'] in wanted]
    base=next(c for c in suite['configurations'] if c['id']==(baseline_config or suite['baseline']['config_id']))
    configs=[copy.deepcopy(base)]  # preserve authored baseline exactly
    for t in temperatures:
        if t not in supported: raise ValueError('temperature not verified supported')
        if t==base['temperature']: continue
        cid='sdk-default' if t is None else 't-'+str(t).replace('.','-')
        cfg={**base,'id':cid,'temperature':t}
        if any(c['id']==cid and c!=cfg for c in configs): raise ValueError('configuration ID collision')
        if cfg not in configs: configs.append(cfg)
    out['configurations']=configs
    qids={q['id'] for q in out['questions']}; cids={c['id'] for c in configs}
    out['exclusions']=[e for e in out.get('exclusions',[]) if e['question_id'] in qids and e['config_id'] in cids]
    validate(cases,out)  # actual strict RV2 + production runtime validator
    return out


def decide(protocol, cases, roles, evidence, suite, history, temperatures, supported, *, temperature_evidence=None, previous_best=None):
    validate_protocol(protocol,cases,roles)
    if evidence['identity']['campaign_id']!=protocol['campaign_id'] or evidence['identity']['cases_hash']!=protocol['cases_hash'] or evidence['identity']['roles_hash']!=protocol['roles_hash']: raise ValueError('decision identity mismatch')
    from .records import compatible
    if {q['id']:digest(q) for q in suite['questions']}!=evidence['identity']['questions']: raise ValueError('suite question definitions differ from evidence')
    for row in evidence['rows']:
        if row['config'] not in suite['configurations'] or row['question'] not in suite['questions']: raise ValueError('suite settings differ from evidence')
    if evidence['run_status']!='completed': raise ValueError('incomplete run cannot select winners')
    decision=retain_questions(evidence,roles,suite['baseline']['question_id'],protocol.get('critical_groups',[]),
        tolerance=protocol.get('question_tolerance',.02),seed=protocol.get('bootstrap_seed',1729),samples=protocol.get('bootstrap_samples',2000))
    temperature_decision=None
    if temperature_evidence is not None:
        from .temperature import curves_from_evidence
        compatible([evidence['identity']]+[item['identity'] for item in temperature_evidence])
        curves=curves_from_evidence(temperature_evidence,roles)
        curves={q:records for q,records in curves.items() if q in decision['questions']}
        if set(curves)!=set(decision['questions']): raise ValueError('missing retained-question temperature curve')
        temperature_decision=refine(curves,protocol.get('refinement_number',0),protocol['supported_range'],protocol.get('temperature_settings'),previous_best)
        temperatures=temperature_decision['temperatures']
        if temperature_decision['stop']:
            tested={r['temperature'] for records in curves.values() for r in records}
            temperatures=([None] if None in tested else [])+sorted(t for t in tested if t is not None)
            temperature_decision['carry_forward_temperatures']=temperatures
            temperature_decision['carry_forward_source_records']=curves
    next_suite=propose_suite(cases,suite,decision['questions'],temperatures,supported)
    record={'campaign_id':protocol['campaign_id'],'round_number':len(history)+1,'parent_hash':digest(history[-1]) if history else None,
        'protocol_hash':digest(protocol),'cases_hash':digest(cases),'roles_hash':digest(roles),'evidence_hash':digest(evidence),
        'run_id':evidence['run_id'],'status':'planned','decision':decision,'next_suite_hash':digest(next_suite),
        'temperature_decision':temperature_decision,'next_action':'stop_temperature_refinement' if temperature_decision and temperature_decision['stop'] else 'retain/refine','not_run':True,'case_file_sha256':protocol['case_file_sha256']}
    return record,next_suite


def write_round(destination, record, suite):
    destination=Path(destination); number=record['round_number']; round_dir=destination/'rounds'/f'{number:03d}-next'
    if round_dir.exists(): raise ValueError('immutable round ID already exists')
    round_dir.mkdir(parents=True)
    template=(Path(__file__).resolve().parents[1]/'docs/templates/run-record.md').read_text()
    record_text=template.replace('<NNN>',f'{number:03d}').replace('<purpose>','next proposal')
    record_text+='\n## Completed next-run decision (machine-reproducible)\n\n```json\n'+json.dumps(record,indent=2)+'\n```\n'
    (round_dir/'record.md').write_text(record_text)
    (round_dir/'decision.json').write_text(json.dumps(record,indent=2)+'\n')
    (round_dir/'suite.json').write_text(json.dumps(suite,indent=2)+'\n')
    journal=destination/'run-journal.md'
    if not journal.exists(): journal.write_text((Path(__file__).resolve().parents[1]/'docs/templates/run-journal.md').read_text().replace('<campaign-id>',record['campaign_id']))
    with journal.open('a') as stream: stream.write(f"\n### Round {number:03d} — proposed next run\n\nStatus: planned; not run. Parent: {record['parent_hash']}. Evidence: {record['evidence_hash']}. Decision and exact suite: rounds/{number:03d}-next/.\n")
    readme=destination/'README.md'
    if not readme.exists(): readme.write_text((Path(__file__).resolve().parents[1]/'docs/templates/campaign-readme.md').read_text().replace('<campaign-id>',record['campaign_id']))
    with readme.open('a') as stream: stream.write(f'\nLatest proposed round: {number:03d}; not run. See run-journal.md.\n')
    return round_dir


def persist_finalists(path, candidate_ids, definitions, identity, *, selection_evidence, protocol_hash):
    path=Path(path)
    if path.exists(): raise ValueError('finalists already frozen')
    frozen=freeze_finalists(candidate_ids,definitions,identity,selection_evidence=selection_evidence,protocol_hash=protocol_hash)
    path.write_text(json.dumps(frozen,indent=2)+'\n'); return frozen
