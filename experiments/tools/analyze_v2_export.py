"""Stream compact exports through pinned native rules; never load a model."""
from __future__ import annotations
import json
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
sys.path.insert(0, str(ROOT/'experiments/batch_v2'))
from export_v2_results import read, digest, legacy_hash, require, catalog

# PyCharm: select a verified export and a NEW report directory, then Run.
EXPORT_FOLDER = None
REPORT_FOLDER = None
STAGE = 'development'
FINALISTS_FILE = None


def source_fingerprint():
    return legacy_hash({str(p.relative_to(ROOT)): digest(p)
        for p in sorted((ROOT/'src').rglob('*')) if p.is_file()
        and '__pycache__' not in p.parts and p.suffix in ('.py','.json')})


def native_decision(raw, question, rule):
    """Same validation, enrichment, extraction and gate as the native interpreter."""
    from laya_context_router.laya.predict import validate_response
    from laya_context_router.questions.models import Question
    from laya_context_router.answers.enrich import enrich_prediction
    from laya_context_router.answers.interpret import extract_answer
    from laya_context_router.answers.rules import accepts
    from laya_context_router.block_runtime.catalog import TypedRule
    definition = question['definition']
    name = definition['name']
    body = Question.from_dict(definition).to_predict_dict()
    policy = TypedRule.from_dict({**rule['definition'], 'question_type':definition['type']})
    validate_response(raw, {name:body})
    enriched = enrich_prediction(raw['answers'][name])
    accepted, reason = accepts(enriched, policy)
    label = extract_answer(enriched)
    return {'raw_label':label, 'answer':label if accepted else 'undecided',
            'decided':accepted, 'reason':reason}


def analyze_export(export_folder, report_folder, *, stage='development', finalists=None):
    from research.protocol import allowed_ids
    from research.records import manifest_identity
    root, destination = Path(export_folder).resolve(), Path(report_folder).resolve()
    require(not destination.exists(), 'Report destination already exists')
    require(destination != root and root not in destination.parents,
            'Report destination must be outside the sealed export')
    export = read(root/'export.json', lossless=False)
    require(export['export_status']=='complete', 'Export is not verified complete')
    require(digest(root/'definitions.json')==export['definitions_sha256'], 'Definitions checksum mismatch')
    definitions = read(root/'definitions.json', lossless=False)
    m, roles = definitions['source_manifest'], definitions.get('roles')
    require(isinstance(roles, dict), 'Matching family-role map is required for analysis')
    require(m['source_hash']==source_fingerprint(),
            'Evaluator source mismatch: run from the source checkout matching the original experiment')
    suite = m['suite']
    require(suite['adapter']=='generic-question', 'Unsupported analyzer adapter')
    require(m['rule_mode']=='replay', 'Only shared-inference replay exports are supported')
    identity = manifest_identity(m, roles)
    permitted = allowed_ids(m['cases'], roles, stage, finalists, identity)
    cases, questions, configs, rules = (catalog(items) for items in
        (m['cases']['cases'], suite['questions'], suite['configurations'], suite['rules']))
    exclusions = {(e['question_id'],e['rule_id'],e['config_id']) for e in suite.get('exclusions',[])}
    vectors = []
    for part in export['partitions']:
        qid, cfgid = part['question_id'], part['config_id']
        require(qid in questions and cfgid in configs, 'Unknown partition definitions')
        selected_rules = list(rules.values())
        if stage=='final':
            candidate = qid+'|'+cfgid
            if candidate not in finalists['candidate_ids']:
                continue
            frozen = finalists['definitions'][candidate]
            require(frozen['question']==questions[qid] and frozen['config']==configs[cfgid],
                    'Frozen finalist settings changed')
            if questions[qid]['definition']['type']=='choice':
                require(list(frozen['question']['definition']['criteria'])==list(questions[qid]['definition']['criteria']),
                        'Frozen finalist choice order changed')
            policies = frozen['policies']
            require(all(p.get('kind')=='native' for p in policies), 'Only frozen native policies supported')
            selected_rules = [p['rule'] for p in policies]
            require(all(rules.get(r['id'])==r for r in selected_rules), 'Frozen native rule changed')
        selected_rules = [r for r in selected_rules if (qid,r['id'],cfgid) not in exclusions]
        path = (root/part['path']).resolve()
        require(root in path.parents and path.is_file() and not (root/part['path']).is_symlink(), 'Unsafe partition path')
        require(digest(path)==part['sha256'], 'Partition checksum mismatch')
        counters = {r['id']:{'question_id':qid,'config_id':cfgid,'rule_id':r['id'],
            'planned':len(permitted),'found':0,'errors':0,'evaluated':0,'scored':0,'unscored':0,'correct':0,
            'accepted':0,'scored_accepted':0,'accepted_correct':0,'accepted_unclear':0,'actionable':0,'scored_actionable':0,
            'wrong_actionable':0,'rejected':0,'confusion':{}} for r in selected_rules}
        seen = set()
        with path.open(encoding='utf-8') as stream:
            for line in stream:
                record = json.loads(line)
                cid = record['case_id']
                require(cid in cases and cid not in seen, 'Unknown/duplicate case in partition')
                require(record['question_id']==qid and record['config_id']==cfgid, 'Partition identity mismatch')
                seen.add(cid)
                if cid not in permitted:
                    continue  # no scoring/evaluation of unauthorized roles
                case = cases[cid]
                for rule in selected_rules:
                    c = counters[rule['id']]; c['found'] += 1
                    if record['status']!='success':
                        c['errors'] += 1; continue
                    try:
                        decision = native_decision(record['raw_response'],questions[qid],rule)
                    except (ValueError,KeyError,TypeError):
                        c['errors'] += 1; continue
                    c['evaluated'] += 1
                    expected, predicted = case.get('expected'), decision['raw_label']
                    scored = case.get('label_status','settled')=='settled'
                    if scored:
                        require(expected in suite['labels'], 'Settled case needs canonical expected label')
                        c['scored'] += 1; c['correct'] += predicted==expected
                        row = c['confusion'].setdefault(expected,{})
                        row[predicted] = row.get(predicted,0)+1
                    else: c['unscored'] += 1
                    if decision['decided']:
                        c['accepted'] += 1
                        if scored:
                            c['scored_accepted'] += 1; c['accepted_correct'] += predicted==expected
                        if predicted=='unclear': c['accepted_unclear'] += 1
                        else:
                            c['actionable'] += 1
                            if scored:
                                c['scored_actionable'] += 1; c['wrong_actionable'] += predicted!=expected
                    else: c['rejected'] += 1
        require(len(seen)==part['found'], 'Partition count mismatch')
        for c in counters.values():
            c['missing'] = c['planned']-c['found']
            c['partial'] = bool(c['missing'])
            c['accuracy'] = c['correct']/c['scored'] if c['scored'] else None
            c['coverage'] = c['accepted']/c['planned'] if c['planned'] else None
            c['accepted_error'] = 1-c['accepted_correct']/c['scored_accepted'] if c['scored_accepted'] else None
            c['actionable_coverage'] = c['actionable']/c['planned'] if c['planned'] else None
            c['actionable_error'] = c['wrong_actionable']/c['scored_actionable'] if c['scored_actionable'] else None
            recalls = [row.get(label,0)/sum(row.values()) for label,row in c['confusion'].items() if sum(row.values())]
            c['balanced_accuracy'] = sum(recalls)/len(recalls) if recalls else None
            vectors.append(c)
    summary = {'stage':stage,'source_run_id':m['run_id'],'evaluator_source_hash':m['source_hash'],
        'export_manifest_sha256':digest(root/'export.json'),'vectors':vectors,
        'denominators':'coverage uses planned authorized cases; accuracy and errors of accepted/actionable predictions use settled labels only; unscored cases, technical errors and missing are separate'}
    destination.mkdir(parents=True)
    (destination/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    lines = ['# Offline experiment results', '', 'Stage: '+stage,
             'Coverage uses planned authorized cases; missing predictions keep results partial.', '',
             '| Question | Temperature config | Rule | Evaluated | Errors | Missing | Accuracy | Actionable coverage | Actionable error |',
             '| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for c in vectors:
        values = [c[k] for k in ('question_id','config_id','rule_id','evaluated','errors','missing','accuracy','actionable_coverage','actionable_error')]
        lines.append('| '+' | '.join('N/A' if v is None else str(round(v,4)) if isinstance(v,float) else str(v) for v in values)+' |')
    (destination/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return summary


if __name__=='__main__':
    if EXPORT_FOLDER is None or REPORT_FOLDER is None:
        raise SystemExit('Set EXPORT_FOLDER and REPORT_FOLDER in this file before Run.')
    analyze_export(EXPORT_FOLDER, REPORT_FOLDER, stage=STAGE,
                   finalists=read(FINALISTS_FILE,lossless=False) if FINALISTS_FILE else None)
