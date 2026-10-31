"""Evidence-based batch reports; no model calls."""
import json
import math
from collections import Counter
from pathlib import Path


def atomic(path, text):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(text, encoding='utf-8')
    tmp.replace(path)


def outcome(answer, expected):
    if answer is None:
        return 'error'
    if answer == 'undecided':
        return 'abstained'
    return 'correct' if answer == expected else 'incorrect'


def metrics(record, layer):
    counts = Counter(c[layer + '_outcome'] for c in record['cases'])
    planned = len(record['definition']['cases'])
    attempted = len(record['cases'])
    c, i = counts['correct'], counts['incorrect']
    ratio = lambda n, d: n / d if d else None
    return {'planned': planned, 'attempted': attempted, 'unattempted': planned-attempted,
            **{k: counts[k] for k in ('correct', 'incorrect', 'abstained', 'error')},
            'accuracy': ratio(c, c+i), 'coverage': ratio(c+i, attempted),
            'rates_among_attempted': {k: ratio(counts[k], attempted) for k in ('correct','incorrect','abstained','error')}}


def effects(record):
    result = {k: [] for k in ('correct_accepted','correct_rejected','incorrect_accepted','incorrect_rejected')}
    for c in record['cases']:
        if c['recommendation_outcome'] in ('correct','incorrect') and c['final_outcome'] != 'error':
            key = c['recommendation_outcome'] + ('_rejected' if c['final_outcome']=='abstained' else '_accepted')
            result[key].append(c['id'])
    return result


def diagnostics(enriched, conditions, expected, recommendation):
    from laya_context_router.answers.conditions import resolve_field, OPS
    result = []
    for condition in conditions:
        value = resolve_field(enriched, condition['field'])
        threshold, op = condition['value'], condition['op']
        margin = None
        if all(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) for x in (value,threshold)):
            if op in ('gt','gte'): margin = value-threshold
            if op in ('lt','lte'): margin = threshold-value
        try:
            check={**condition, 'observed':value,'passed':OPS[op](value,threshold),'margin':margin}
        except (TypeError,ValueError) as exc:
            check={**condition, 'observed':value,'passed':None,'margin':None,'error':str(exc)}
        result.append(check)
    detail = {'derived_report_conditions':result}
    if enriched['type']=='choice':
        probs=enriched['probabilities']
        detail.update(expected_probability=probs[expected], expected_rank=1+sum(v>probs[expected] for v in probs.values()),
                      selected_minus_expected=probs[recommendation]-probs[expected],
                      selected_is_top=probs[recommendation]==max(probs.values()))
    else:
        detail.update(noul=enriched['noul'],side='yes' if enriched['noul']>=0.5 else 'no',distance_from_boundary=enriched.get('distance_from_boundary'))
    return detail


def pct(value):
    return 'N/A' if value is None else f'{100*value:.1f}%'


def cell(value):
    return str(value).replace('|','\\|').replace('\n',' ')


def summary(record):
    lines=[f"# {record['configuration']['name']}", '', f"Mode: {record['mode']}; status: {record['status']}.", '',
           f"Requested settings: `{json.dumps(record['configuration'])}`. Effective SDK settings: not exposed.", '',
           f"Duration: {record.get('duration_seconds',0):.3f}s; load: {record.get('load_seconds',0):.3f}s.", '',
           '| Layer | Planned | Attempted | Unattempted | Correct | Incorrect | Abstained | Errors | Accuracy | Coverage |',
           '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for layer in ('recommendation','final'):
        m=metrics(record,layer)
        lines.append('| '+' | '.join(map(str,[layer,*[m[k] for k in ('planned','attempted','unattempted','correct','incorrect','abstained','error')],pct(m['accuracy']),pct(m['coverage'])]))+' |')
    for layer in ('recommendation','final'):
        m=metrics(record,layer)
        lines += ['', f"{layer} outcome rates (denominator: {m['attempted']} attempted): " + ', '.join(f'{k} {pct(v)}' for k,v in m['rates_among_attempted'].items()), '']
    lines += ['Accuracy uses definitive answers; coverage uses attempted cases. Unattempted cases are not abstentions.', '', '## Rule effects', '']
    for k,ids in effects(record).items(): lines.append(f"- {k}: {len(ids)} — {', '.join(ids) or 'none'}")
    lines += ['', '## Cases', '', '| ID | Expected | LAYA | Raw outcome | Final | Final outcome |', '| --- | --- | --- | --- | --- | --- |']
    for c in record['cases']:
        lines.append('| '+' | '.join(cell(c.get(k)) for k in ('id','expected','recommendation','recommendation_outcome','final','final_outcome'))+' |')
    for c in record['cases']:
        lines += ['',f"### {c['id']}",'',f"Input: {c['input']}",'',f"Decision: `{json.dumps(c.get('decision'))}`",'',f"Diagnostics (derived report calculations): `{json.dumps(c.get('diagnostics'))}`"]
        if c.get('diagnostics_error'): lines += ['',f"Diagnostic error: {c['diagnostics_error']}"]
        if c.get('error'): lines += ['',f"Error: `{json.dumps(c['error'])}`"]
    if record.get('error'): lines += ['',f"Configuration error: `{json.dumps(record['error'])}`"]
    lines += ['', 'Complete definition, raw replies, actual runtime events and timing are in the matching JSON. Missing evidence is not inferred.', '']
    return '\n'.join(lines)


def save(record, path):
    record['metrics']={k:metrics(record,k) for k in ('recommendation','final')}
    record['rule_effects']=effects(record)
    atomic(path,json.dumps(record,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    atomic(Path(path).with_suffix('.md'),summary(record))


def comparison(records, path):
    lines=['# Configuration comparison', '', 'Best observed results on this dataset only. Complete configurations are ranked first, then fewer final mistakes, then fewer abstentions. Incomplete results are not eligible as best.', '',
           '| Configuration | Mode | Status | Raw correct | Raw wrong | Final correct | Final wrong | Abstained | Errors | Unattempted | Accuracy | Coverage | Seconds |',
           '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    def rank(r):
        m=metrics(r,'final')
        return (r['status']!='completed',m['incorrect'],m['abstained'])
    for r in sorted(records,key=rank):
        m=metrics(r,'final'); raw=metrics(r,'recommendation')
        vals=[r['configuration']['name'],r['mode'],r['status'],raw['correct'],raw['incorrect'],m['correct'],m['incorrect'],m['abstained'],m['error'],m['unattempted'],pct(m['accuracy']),pct(m['coverage']),round(r.get('duration_seconds',0),3)]
        lines.append('| '+' | '.join(map(cell,vals))+' |')
    for r in records:
        lines += ['',f"Rule effects for {r['configuration']['name']}: `{json.dumps(effects(r))}`",'']
    lines += ['', '## Cases with changed outcomes', '']
    ids=records[0]['definition']['cases'] if records else []
    for case in ids:
        states=[]
        for r in records:
            c=next((c for c in r['cases'] if c['id']==case['id']),None)
            states.append((r['configuration']['name'],(c['recommendation'],c['final'],c['final_outcome']) if c else ('unattempted',)))
        if len({str(s[1]) for s in states})>1: lines.append(f"- {case['id']}: {states}")
    atomic(path,'\n'.join(lines)+'\n')
