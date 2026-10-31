"""Rebuildable offline reports from authoritative outcome checkpoints."""
import csv
import html
import io
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from schema import NOISE, load, vectors

KEYS = ('question_id', 'rule_id', 'config_id')
METRICS = {'raw_accuracy': ('raw_correct', 'scored'), 'accepted_accuracy': ('AC', 'accepted_scored'), 'coverage': ('accepted_scored', 'scored'), 'correct_per_scored': ('AC', 'scored'), 'missed_correct_rate': ('RC', 'raw_correct'), 'wrong_filtering_rate': ('RW', 'raw_wrong')}


def atomic(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp-' + str(os.getpid()))
    try:
        with temporary.open('w', encoding='utf-8', newline='') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _public(row):
    return {key: value for key, value in row.items() if not key.startswith('_')}


def _aggregate(rows, vector, kind, value):
    result = dict(zip(KEYS, vector))
    result.update(group_type=kind, group_value=value, planned=len(rows))
    counts = Counter(r.get('status', 'unattempted') for r in rows)
    result.update(attempted=len(rows)-counts['unattempted'], valid_completed=counts['completed'], errors=counts['error']+counts['configuration_error'], timeouts=counts['timeout'], skipped=counts['skipped'], unattempted=counts['unattempted'])
    cells = Counter()
    operational = Counter()
    confusion = Counter()
    for row in rows:
        if row.get('status') != 'completed':
            continue
        accepted = row.get('accepted')
        if type(accepted) is bool:
            operational['operational_accepted' if accepted else 'operational_abstained'] += 1
        raw = row.get('raw_label')
        valid_raw = isinstance(raw, str) and bool(raw) and ('_labels' not in row or raw in row['_labels'])
        if row.get('label_status') != 'settled' or row.get('expected') is None or not valid_raw or type(accepted) is not bool:
            continue
        correct = raw == row['expected']
        cells[('A' if accepted else 'R') + ('C' if correct else 'W')] += 1
        confusion[(row['expected'], raw)] += 1
    for name in ('AC', 'AW', 'RC', 'RW'):
        result[name] = cells[name]
    for name in ('operational_accepted', 'operational_abstained'):
        result[name] = operational[name]
    result.update(scored=sum(cells.values()), accepted_scored=cells['AC']+cells['AW'], abstained=cells['RC']+cells['RW'], raw_correct=cells['AC']+cells['RC'], raw_wrong=cells['AW']+cells['RW'])
    result['unscored'] = result['planned'] - result['scored']
    for name, (numerator, denominator) in METRICS.items():
        result[name] = result[numerator]/result[denominator] if result[denominator] else None
        result[name+'_numerator'] = result[numerator]
        result[name+'_denominator'] = result[denominator]
    # Each vector references shared inference latency; run totals deduplicate inference IDs.
    result['referenced_prediction_seconds'] = sum(r.get('inference_seconds') or 0 for r in rows)
    result['rule_seconds'] = sum(r.get('rule_seconds') or 0 for r in rows)
    result['prediction_time_shared'] = any((r.get('inference_shared') or r.get('evaluation_kind') == 'rule-replay') for r in rows)
    result['confusion'] = [{'expected': a, 'raw_label': b, 'count': n} for (a,b), n in sorted(confusion.items())]
    return result


def summaries(rows):
    grouped = defaultdict(list)
    seen = set()
    for row in rows:
        key = tuple(row[k] for k in KEYS)
        identity = key + (row['case_id'],)
        if identity in seen:
            raise ValueError('duplicate vector/case checkpoint: ' + str(identity))
        seen.add(identity)
        grouped[key].append(row)
    result = []
    tags = sorted({t for row in rows for t in row.get('tags', [])})
    splits = sorted({row.get('split', 'unspecified') for row in rows})
    for vector, vector_rows in grouped.items():
        result.append(_aggregate(vector_rows, vector, 'overall', 'all'))
        for noise in NOISE:
            result.append(_aggregate([r for r in vector_rows if r.get('noise_level','unspecified') == noise], vector, 'noise_level', noise))
        for tag in tags:
            result.append(_aggregate([r for r in vector_rows if tag in r.get('tags',[])], vector, 'tag', tag))
        result.append(_aggregate([r for r in vector_rows if not r.get('tags')], vector, 'untagged', 'untagged'))
        for split in splits:
            result.append(_aggregate([r for r in vector_rows if r.get('split','unspecified') == split], vector, 'split', split))
    return result


def _display(value):
    if value is None:
        return 'N/A'
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float):
        return f'{value:.4f}'
    return str(value)


def _table(summary):
    columns = list(KEYS) + ['group_type', 'group_value', 'planned', 'scored', 'unscored', 'AC', 'AW', 'abstained', 'RC', 'RW', 'raw_accuracy', 'accepted_accuracy', 'coverage', 'errors', 'timeouts', 'skipped', 'unattempted', 'referenced_prediction_seconds', 'rule_seconds']
    def cell(row, key):
        if key in METRICS:
            value = row[key]
            return ('N/A' if value is None else f'{100*value:.1f}%') + f" ({row[key+'_numerator']}/{row[key+'_denominator']})"
        return _display(row[key])
    return columns, [[cell(row, key) for key in columns] for row in summary]


def write_reports(run_dir, rows):
    root = Path(run_dir)
    summary = summaries(rows)
    atomic(root/'results.jsonl', ''.join(json.dumps(_public(row), ensure_ascii=False, allow_nan=False)+'\n' for row in rows))
    if summary:
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fieldnames=list(summary[0]))
        writer.writeheader()
        for record in summary:
            writer.writerow({**record, 'confusion': json.dumps(record['confusion'], ensure_ascii=False)})
        atomic(root/'summary.csv', stream.getvalue())
    else:
        atomic(root/'summary.csv', ','.join(KEYS)+',group_type,group_value,planned,scored\n')
    for vector in dict.fromkeys(tuple(r[k] for k in KEYS) for r in summary):
        path = root/'batches'/f'{vector[0]}__{vector[1]}'/vector[2]/'summary.json'
        atomic(path, json.dumps([r for r in summary if tuple(r[k] for k in KEYS) == vector], indent=2, ensure_ascii=False)+'\n')
    columns, cells = _table(summary)
    note = ('AC = correct accepted; AW = wrong accepted; RC = correct rejected; RW = wrong filtered. '
            'Abstained = RC + RW among scored inputs. N/A means zero denominator. '
            'Noise groups partition inputs. Tags overlap and must not be summed. '
            'Prediction latency is referenced per vector and shared for rule replay. '
            'Incomplete vectors are partial and are not ranked. Split groups keep held-out results separate.')
    md = '# Runner V2 comparison\n\n' + note + '\n\n'
    def safe_md(value):
        return html.escape(value).replace('|', '&#124;').replace('\n', ' ')
    md += '| '+' | '.join(columns)+' |\n| '+' | '.join(['---']*len(columns))+' |\n'
    md += ''.join('| '+' | '.join(safe_md(c) for c in row)+' |\n' for row in cells)
    atomic(root/'comparison.md', md)
    # Escape every dynamic string before embedding; filters use only DOM text and attributes.
    esc = lambda s: html.escape(str(s), quote=True)
    vector_names = sorted({' / '.join(str(r[k]) for k in KEYS) for r in summary})
    group_names = sorted({r['group_type']+':'+r['group_value'] for r in summary})
    options = lambda values: '<option value="">All</option>'+''.join('<option>'+esc(v)+'</option>' for v in values)
    body_rows = ''.join('<tr data-vector="'+esc(' / '.join(str(r[k]) for k in KEYS))+'" data-group="'+esc(r['group_type']+':'+r['group_value'])+'">'+''.join('<td>'+esc(v)+'</td>' for v in row)+'</tr>' for r,row in zip(summary,cells))
    report = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Runner V2 report</title><style>body{font:15px system-ui;margin:24px;color:#172b3a;background:#f7f9fb}h1{font-size:26px}label{display:inline-block;margin:8px 20px 16px 0}select{padding:8px;max-width:85vw}.scroll{overflow-x:auto;background:white;border:1px solid #ccd4dc}table{border-collapse:collapse;white-space:nowrap}th,td{padding:9px;border-bottom:1px solid #dde3e8;text-align:right}th{background:#e8eef4}td:first-child,th:first-child{text-align:left}tr[hidden]{display:none}p{max-width:1000px;line-height:1.5}</style><h1>Runner V2 report</h1><p>'''+esc(note)+'''</p><label>Vector <select id="vector">'''+options(vector_names)+'''</select></label><label>Group <select id="group">'''+options(group_names)+'''</select></label><p id="shown" aria-live="polite"></p><div class="scroll"><table><thead><tr>'''+''.join('<th>'+esc(c)+'</th>' for c in columns)+'''</tr></thead><tbody>'''+body_rows+'''</tbody></table></div><script>const v=document.getElementById('vector'),g=document.getElementById('group');function filter(){let n=0;document.querySelectorAll('tr[data-vector]').forEach(r=>{r.hidden=!!((v.value&&r.dataset.vector!==v.value)||(g.value&&r.dataset.group!==g.value));if(!r.hidden)n++;});document.getElementById('shown').textContent=n+' group rows shown';}v.addEventListener('change',filter);g.addEventListener('change',filter);g.value='overall:all';filter();</script></html>'''
    details = '<details><summary>Inspect case inputs and authoritative evidence</summary><div class="scroll"><table><tr><th>Vector</th><th>Case</th><th>Input</th><th>Status</th><th>Raw label</th><th>Final label</th><th>Evidence</th></tr>'
    for row in rows:
        vector = ' / '.join(str(row[k]) for k in KEYS)
        checkpoint = f"batches/{row['question_id']}__{row['rule_id']}/{row['config_id']}/cases/{row['case_id']}.json"
        evidence = '<a href="'+esc(checkpoint)+'">checkpoint</a>' if (root/checkpoint).exists() else 'unattempted'
        iid = row.get('inference_id')
        if isinstance(iid, str) and iid.isalnum() and (root/'inferences'/f'{iid}.json').exists():
            evidence += ' · <a href="inferences/'+esc(iid)+'.json">inference</a>'
        details += '<tr>'+''.join('<td>'+esc(value)+'</td>' for value in (vector,row['case_id'],json.dumps(row.get('input'),ensure_ascii=False),row.get('status'),row.get('raw_label'),row.get('final_label')))+'<td>'+evidence+'</td></tr>'
    details += '</table></div></details>'
    report = report.replace('<script>', details+'<script>')
    atomic(root/'report.html', report)
    return summary


def collect(run_dir):
    root = Path(run_dir)
    manifest = load(root/'manifest.json')
    cases = manifest['cases']
    suite = manifest['suite']
    rows = []
    for q,r,c in vectors(suite):
        for case in cases['cases']:
            row = {**case, 'case_id':case['id'], 'question_id':q, 'rule_id':r, 'config_id':c, 'experiment_id':suite['experiment_id'], 'dataset_version':cases['dataset_version'], 'split':case.get('split','unspecified'), 'source_family_id':case.get('source_family_id',case['id']), 'status':'unattempted', 'raw_label':None, 'final_label':None, 'accepted':None}
            checkpoint = root/'batches'/f'{q}__{r}'/c/'cases'/f"{case['id']}.json"
            if checkpoint.exists():
                saved = load(checkpoint)
                for key, expected in (('case_id',case['id']),('question_id',q),('rule_id',r),('config_id',c)):
                    if saved.get(key) != expected:
                        raise ValueError('checkpoint identity mismatch: '+str(checkpoint))
                row.update(saved)
            else:
                worker_status = root / f'worker-{c}-status.json'
                if worker_status.exists():
                    state = load(worker_status)
                    if state.get('status') in ('configuration_error', 'error'):
                        row.update(status=state['status'], error=state.get('error'))
            # Frozen annotations are authoritative, regardless of accidental checkpoint edits.
            for key in ('input','expected','label_status','noise_level','tags'):
                row[key] = case[key]
            row['_labels'] = suite['labels']
            rows.append(row)
    write_reports(root, rows)
    return rows
