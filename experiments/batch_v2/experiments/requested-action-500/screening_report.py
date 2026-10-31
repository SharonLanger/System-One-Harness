"""Bounded initial report: permitted development cases, exact native rules, no threshold fitting."""
from collections import defaultdict
from pathlib import Path
import json
import sys

BATCH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BATCH))
from research.analyze import summarize
from research.protocol import digest, validate_protocol
from research.records import load, read_run


def group_summaries(rows, labels):
    groups = {'all_development': rows}
    for name in sorted({r['noise_level'] for r in rows}):
        groups['noise:' + name] = [r for r in rows if r['noise_level'] == name]
    for tag in sorted({tag for r in rows for tag in r['tags']}):
        groups['tag:' + tag] = [r for r in rows if tag in r['tags']]
    for label in labels:
        groups['class:' + label] = [r for r in rows if r['expected'] == label]
    output = {}
    for key, value in groups.items():
        summary = summarize(value, labels)
        settled = sum(row['label_status'] == 'settled' for row in value)
        summary['settled_planned'] = settled
        summary['screen_complete'] = (summary['complete'] and summary['classification']['n'] == settled
                                      and summary['probability']['n'] == settled and summary['runner_native']['n'] == settled)
        output[key] = summary
    return output


def write_screening_report(run_root, roles, protocol):
    root = Path(run_root)
    manifest = load(root / 'manifest.json')
    validate_protocol(protocol, manifest['cases'], roles)
    if manifest['suite']['experiment_id'] != protocol['campaign_id']:
        raise ValueError('Report campaign does not match frozen protocol')
    evidence = read_run(root, roles, 'development')
    labels = evidence['labels']
    grouped = defaultdict(list)
    for row in evidence['rows']:
        grouped[(row['question_id'], row['config_id'])].append(row)
    output = {'kind': 'initial-development-screen', 'run_id': evidence['run_id'], 'run_status': evidence['run_status'],
              'identity': evidence['identity'], 'protocol_hash': digest(protocol), 'allowed_case_ids': evidence['allowed_case_ids'],
              'held_out_loaded': False, 'paired_uncertainty': 'Deferred to next-round selection; point estimates are not significance tests.',
              'questions': {}, 'rules': {}}
    for (qid, cid), rows in sorted(grouped.items()):
        output['questions'][qid + '|' + cid] = group_summaries(rows, labels)
        for rule in evidence['suite']['rules']:
            gate_rows = []
            for row in rows:
                # Read only development IDs already authorized by read_run. No summary.csv,
                # results.jsonl, or overall report is opened: they contain other roles.
                path = root / 'batches' / (qid + '__' + rule['id']) / cid / 'cases' / (row['case_id'] + '.json')
                saved = load(path) if path.exists() else {}
                if saved:
                    expected = {'case_id': row['case_id'], 'question_id': qid, 'config_id': cid, 'rule_id': rule['id'],
                                'input_hash': digest(row['frozen_input']), 'question_hash': digest(row['question']),
                                'config_hash': digest(row['config']), 'rule_hash': digest(rule), 'inference_id': row['inference_id']}
                    if any(saved.get(k) != value for k, value in expected.items()):
                        raise ValueError('Rule checkpoint provenance mismatch: ' + str(path))
                    if row['status'] == 'completed' and saved.get('status') == 'completed' and saved.get('raw_label') != row['raw_label']:
                        raise ValueError('Shared prediction mismatch: ' + str(path))
                status = saved.get('status', 'unattempted') if row['status'] == 'completed' else row['status']
                if status == 'completed' and type(saved.get('accepted')) is not bool:
                    status = 'missing_acceptance'
                gate_rows.append({**row, 'status': status, 'native_accepted': saved.get('accepted') if status == 'completed' else None})
            output['rules'][qid + '|' + cid + '|' + rule['id']] = group_summaries(gate_rows, labels)
    destination = root / 'research-development'
    destination.mkdir(exist_ok=True)
    (destination / 'screening.json').write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    def fmt(value):
        return 'N/A' if value is None else f'{value:.4f}'
    lines = ['# Requested-action first results', '',
             'Development cases only. No held-out predictions loaded. This is a screening report, not a selected winner.', '',
             'BA = balanced accuracy; MCC = correlation across the class confusion table. Higher is better. NLL and Brier: lower is better. '
             'Coverage = fraction of settled cases accepted. Accepted error = fraction of accepted settled answers that are wrong. '
             'Unsettled rejection is a separate behavioral goal. N/A means unavailable; no accepted cases is not zero error.', '',
             '| Question / setting | Status | Scored / planned settled | Probability n | BA | MCC | NLL | Brier |', '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for key, groups in output['questions'].items():
        item = groups['all_development']; c = item['classification']; p = item['probability']
        nll = 'infinite (zero p)' if p['strict_nll_status'] == 'infinite_zero_probability' else fmt(p['strict_nll'])
        lines.append('| ' + key.replace('|', ' / ') + ' | ' + ('complete' if item['screen_complete'] else 'PARTIAL') + ' | '
                     + str(c['n']) + ' / ' + str(item['settled_planned']) + ' | ' + str(p['n']) + ' | '
                     + fmt(c['balanced_accuracy_present_classes']) + ' | ' + fmt(c['mcc'])
                     + ' | ' + nll + ' | ' + fmt(p['brier_sum']) + ' |')
    lines += ['', '## Exact rule comparisons', '',
              '| Question / setting / rule | Status | Coverage | Accepted error | Correct yield | AC | AW | RC | RW | Unsettled rejected / planned |',
              '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for key, groups in output['rules'].items():
        item = groups['all_development']; g = item['runner_native']; u = item['unsettled']
        lines.append('| ' + key.replace('|', ' / ') + ' | ' + ('complete' if item['screen_complete'] else 'PARTIAL') + ' | '
                     + ' | '.join(fmt(g[k]) for k in ('coverage', 'accepted_error', 'correct_accepted_yield')) + ' | '
                     + ' | '.join(str(g[k]) for k in ('AC', 'AW', 'RC', 'RW')) + ' | '
                     + str(u['desired_abstention_met']) + ' / ' + str(u['n']) + ' |')
    lines += ['', 'Class, noise, tag, confusion, technical-error and probability-denominator details are in screening.json. '
              'Tags overlap. NLL may be unavailable because of zero true-class probability; inspect its status in JSON. '
              'Use family-paired comparisons before discarding alternatives. Temperature fitting uses only the separate temperature role; '
              'policy threshold selection and DOCTOR comparisons use only the policy role. See the round plan.']
    path = destination / 'START-HERE.md'
    path.write_text('\n'.join(lines) + '\n')
    return path
