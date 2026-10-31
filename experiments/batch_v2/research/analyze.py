"""Role-filtered reports, paired family uncertainty, and a compact HTML reader."""
import html
import json
import random
from collections import Counter
from pathlib import Path
from .metrics import classification, probability_quality, gate
from .policies import sweep, and_sweep, SCALARS, evaluate, replay_native
from .protocol import digest


def summarize(rows, labels):
    valid=[r for r in rows if r['status']=='completed' and r['label_status']=='settled' and r['raw_label'] in labels]
    actual=[r['expected'] for r in valid]; predicted=[r['raw_label'] for r in valid]
    prob=[r for r in valid if r['probabilities'] is not None]
    native=[r for r in valid if type(r.get('native_accepted')) is bool]
    return {'planned':len(rows),'technical_statuses':dict(Counter(r['status'] for r in rows)),
        'complete':bool(rows) and all(r['status']=='completed' for r in rows),'scored_ids':[r['case_id'] for r in valid],
        'classification':classification(actual,predicted,labels),
        'probability':probability_quality([r['expected'] for r in prob],[r['probabilities'] for r in prob],labels),
        'missing_probability_count':len(valid)-len(prob),
        'runner_native':gate([r['raw_label']==r['expected'] for r in native],[r['native_accepted'] for r in native]),
        'unsettled':{'n':sum(r['label_status']!='settled' for r in rows),
            'accepted':sum(r['label_status']!='settled' and r.get('native_accepted') is True for r in rows),
            'desired_abstention_met':sum(r.get('desired_abstention') is True and r.get('native_accepted') is False for r in rows)}}


def analyze(evidence, roles):
    labels=evidence['labels']; vectors={}
    for row in evidence['rows']:
        key=row['question_id']+'|'+row['config_id']; vectors.setdefault(key,[]).append(row)
    results={}
    for key,rows in sorted(vectors.items()):
        groups={'all_permitted':rows}
        for role in sorted({roles[r['source_family_id']] for r in rows}): groups['role:'+role]=[r for r in rows if roles[r['source_family_id']]==role]
        for tag in sorted({t for r in rows for t in r.get('tags',[])}): groups['tag:'+tag]=[r for r in rows if tag in r.get('tags',[])]
        for level in sorted({r.get('noise_level') for r in rows}): groups['noise:'+level]=[r for r in rows if r.get('noise_level')==level]
        for label in labels: groups['class:'+label]=[r for r in rows if r['expected']==label]
        result={'groups':{name:summarize(rs,labels) for name,rs in groups.items()},'experimental_policies':{}}
        # Policy tuning only on policy calibration; development views do not choose thresholds.
        eligible=[r for r in rows if roles[r['source_family_id']]=='policy' and r['status']=='completed' and r['label_status']=='settled' and r['scores'] is not None and r['raw_label'] in labels]
        intended=[r for r in rows if roles[r['source_family_id']]=='policy' and r['label_status']=='settled']
        if evidence['stage']=='policy' and (not intended or len(eligible)!=len(intended)):
            result['experimental_policies']={'available':False,'reason':'missing/failed probability evidence; no reduced-denominator selection'}
        elif evidence['stage']=='policy':
            correct=[r['raw_label']==r['expected'] for r in eligible]; s=[r['scores'] for r in eligible]
            result['experimental_policies']={f:sweep(correct,s,f) for f in SCALARS}
            result['experimental_policies']['confidence_and_gap']=and_sweep(correct,s)
            result['policy_case_ids']=[r['case_id'] for r in eligible]
            result['policy_group_metrics']={}
            for field,curve in result['experimental_policies'].items():
                if not curve.get('available'): continue
                for i,point in enumerate(curve['points']):
                    if point.get('endpoint')=='all_reject': mask=[False]*len(eligible)
                    elif field=='confidence_and_gap': mask=[r['scores']['confidence']>=point['thresholds'][0] and r['scores']['probability_gap']>=point['thresholds'][1] for r in eligible]
                    else: mask=evaluate([r['scores'] for r in eligible],[{'field':field,'op':curve['op'],'value':point['threshold']}])
                    result['policy_group_metrics'][field+':'+str(i)]=gate_groups(eligible,mask,labels)
        if evidence['stage']=='final':
            definition=evidence['finalists']['definitions'][key]; result['frozen_policies']={}
            complete=all(r['status']=='completed' and (r['label_status']!='settled' or r['raw_label'] in labels and r['scores'] is not None) for r in rows)
            for policy in definition['policies']:
                if not complete:
                    result['frozen_policies'][policy['id']]={'available':False,'reason':'incomplete frozen final vector'};continue
                if policy['kind']=='experimental':
                    settled=[r for r in rows if r['label_status']=='settled']
                    try:mask=evaluate([r['scores'] for r in settled],policy['conditions'])
                    except ValueError as exc:
                        result['frozen_policies'][policy['id']]={'available':False,'reason':str(exc)};continue
                else:
                    settled=[r for r in rows if r['label_status']=='settled'];mask=[replay_native(r['raw_response'],r['question'],policy['rule'],evidence['suite'],r['config'],r['frozen_input'])['decided'] for r in settled]
                result['frozen_policies'][policy['id']]={'definition':policy,'groups':gate_groups(settled,mask,labels)}
        results[key]=result
    return {'schema_version':1,'kind':'research-role-filtered','analysis_version':'research-v1',
            **{k:evidence[k] for k in ('identity','stage','run_id','run_status','allowed_case_ids','inference_count','logical_outcomes_planned')},
            'evidence_hash':digest(evidence),'paired':paired_vectors(vectors,labels,evidence['stage']),'vectors':results,'annotations_note':'tags overlap; class/noise/role denominators shown separately'}


def paired(left, right, labels, *, seed=1729, samples=2000):
    a={r['case_id']:r for r in left}; b={r['case_id']:r for r in right}
    if len(a)!=len(left) or len(b)!=len(right) or set(a)!=set(b): raise ValueError('paired comparisons need identical unique case IDs')
    ids=sorted(a)
    if not ids or any(a[i]['source_family_id']!=b[i]['source_family_id'] or a[i]['expected']!=b[i]['expected'] for i in ids): raise ValueError('paired truth/family mismatch or empty')
    if any(r['status']!='completed' or r['label_status']!='settled' or r['raw_label'] not in labels for r in left+right):
        return {'available':False,'reason':'incomplete or unsettled paired support'}
    families=sorted({r['source_family_id'] for r in left}); rng=random.Random(seed)
    grouped={f:[i for i in ids if a[i]['source_family_id']==f] for f in families}
    keys=('balanced_accuracy_present_classes','mcc'); differences={k:[] for k in keys}; recalls={l:[] for l in labels}
    def calc(mapping, selected): return classification([mapping[i]['expected'] for i in selected],[mapping[i]['raw_label'] for i in selected],labels)
    fulla=calc(a,ids); fullb=calc(b,ids)
    for _ in range(samples):
        selected=[i for family in rng.choices(families,k=len(families)) for i in grouped[family]]
        x,y=calc(a,selected),calc(b,selected)
        for k in keys: differences[k].append(y[k]-x[k])
        for label in labels:
            if x['recall'][label] is not None: recalls[label].append(y['recall'][label]-x['recall'][label])
    def interval(values):
        if not values: return None
        values=sorted(values); return [values[int(.025*(len(values)-1))],values[int(.975*(len(values)-1))]]
    return {'available':True,'seed':seed,'samples':samples,'family_count':len(families),'case_ids':ids,
        'descriptive_multiple_comparisons':True,'comparable_all_classes':fulla['comparable_all_classes'],
        'delta':{k:fullb[k]-fulla[k] for k in keys},'intervals':{k:interval(v) for k,v in differences.items()},
        'recall_intervals':{l:interval(v) for l,v in recalls.items()}}


def write_report(report, destination):
    destination=Path(destination); destination.mkdir(parents=True,exist_ok=True)
    (destination/'analysis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    cards=[]
    for vector,result in report['vectors'].items():
        for group,value in result['groups'].items():
            cards.append('<details><summary>'+html.escape(vector+' / '+group)+'</summary><pre>'+html.escape(json.dumps(value,indent=2))+'</pre></details>')
        for section in ('experimental_policies','policy_group_metrics','frozen_policies'):
            if result.get(section): cards.append('<details><summary>'+html.escape(vector+' / '+section)+'</summary><pre>'+html.escape(json.dumps(result[section],indent=2))+'</pre></details>')
    cards.append('<details><summary>Paired family uncertainty</summary><pre>'+html.escape(json.dumps(report.get('paired',{}),indent=2))+'</pre></details>')
    page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Research evidence</title><style>body{font:16px system-ui;margin:16px;max-width:960px}summary{padding:12px;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eef2f7;padding:12px}details{border:1px solid #ccd;margin:8px 0}</style><h1>Research evidence</h1><p>'+html.escape(report['stage'])+'; role-filtered; N/A = unavailable. Experimental policies are separate from native runner rules.</p>'+''.join(cards)+'</html>'
    (destination/'research.html').write_text(page)


def gate_groups(rows, accepted, labels):
    groups={'overall':list(range(len(rows)))}
    for label in labels: groups['class:'+label]=[i for i,r in enumerate(rows) if r['expected']==label]
    for tag in sorted({t for r in rows for t in r.get('tags',[])}): groups['tag:'+tag]=[i for i,r in enumerate(rows) if tag in r.get('tags',[])]
    for noise in sorted({r['noise_level'] for r in rows}): groups['noise:'+noise]=[i for i,r in enumerate(rows) if r['noise_level']==noise]
    return {group:gate([rows[i]['raw_label']==rows[i]['expected'] for i in ids],[accepted[i] for i in ids]) for group,ids in groups.items()}


def paired_vectors(vectors,labels,stage):
    keys=sorted(vectors);out={}
    for i,left in enumerate(keys):
        for right in keys[i+1:]:
            # Same role and frozen cases; paired reports never use summary aggregates.
            a=[r for r in vectors[left] if r['label_status']=='settled'];b=[r for r in vectors[right] if r['label_status']=='settled']
            try: out[left+' -> '+right]=paired(a,b,labels)
            except ValueError as exc: out[left+' -> '+right]={'available':False,'reason':str(exc)}
    return out
