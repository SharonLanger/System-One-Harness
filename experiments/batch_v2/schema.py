"""Strict, dependency-free authored input checks; runtime contracts are also checked by adapters."""
import hashlib
import json
import math
import re
import sys
from pathlib import Path

ID = re.compile(r'^[a-z0-9][a-z0-9-]*$')
NOISE = ('regular', 'noisy', 'heavy', 'unspecified')
STATUSES = ('settled', 'taxonomy_pending', 'insufficient_context', 'out_of_scope')


def hash_value(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def load(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key: ' + key)
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('nonfinite JSON number: ' + value)
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=pairs, parse_constant=invalid)


def _check(ok, message):
    if not ok:
        raise ValueError(message)


def _object(obj, required, optional=(), where='object'):
    _check(isinstance(obj, dict), where + ' must be an object')
    _check(set(required) <= set(obj), where + ' missing required fields: ' + str(set(required) - set(obj)))
    _check(set(obj) <= set(required) | set(optional), where + ' unknown fields: ' + str(set(obj) - set(required) - set(optional)))


def _id(value, where):
    _check(isinstance(value, str) and bool(ID.fullmatch(value)), where + ' must be a safe lowercase ID')


def _string(value, where):
    _check(isinstance(value, str) and bool(value.strip()), where + ' must be a nonempty string')


def _entries(entries, where):
    _check(isinstance(entries, list) and len(entries) > 0, where + ' must be a nonempty array')
    ids = []
    for entry in entries:
        _check(isinstance(entry, dict), where + ' entries must be objects')
        _id(entry.get('id'), where + '.id')
        ids.append(entry['id'])
    _check(len(ids) == len(set(ids)), where + ' duplicate IDs')
    return set(ids)


def validate(cases, suite):
    if suite.get("adapter") == "method-selection":
        from method_adapter import validate as validate_method
        return validate_method(cases, suite)
    _object(cases, ('schema_version', 'dataset_id', 'dataset_version', 'cases'), where='cases')
    _object(suite, ('schema_version', 'experiment_id', 'dataset_id', 'dataset_version', 'adapter', 'question_type', 'labels', 'questions', 'rules', 'configurations', 'baseline'), ('exclusions',), 'suite')
    for obj in (cases, suite):
        _check(type(obj['schema_version']) is int and obj['schema_version'] == 1, 'unsupported schema_version')
        _id(obj['dataset_id'], 'dataset_id')
        _string(obj['dataset_version'], 'dataset_version')
    _id(suite['experiment_id'], 'experiment_id')
    _check(all(cases[k] == suite[k] for k in ('dataset_id', 'dataset_version')), 'dataset identity/version mismatch')
    _check(suite['adapter'] in ('generic-question', 'requested-action', 'context-scope'), 'unsupported adapter')
    _check(suite['question_type'] in ('choice', 'noul'), 'unsupported question_type')
    labels = suite['labels']
    _check(isinstance(labels, list) and len(labels) >= 2, 'labels must contain at least two labels')
    for label in labels:
        _string(label, 'label')
        _check(label != 'undecided', 'undecided is reserved for rejection')
    _check(len(labels) == len(set(labels)), 'duplicate labels')
    if suite['question_type'] == 'noul':
        _check(labels == ['yes', 'no'], 'noul preserves runtime yes/no order')
    _check(isinstance(cases['cases'], list), 'cases must be an array')
    ids = set()
    for case in cases['cases']:
        _object(case, ('id', 'input', 'expected', 'label_status', 'noise_level', 'tags'), ('source_family_id', 'split', 'desired_abstention', 'notes'), 'case')
        _id(case['id'], 'case.id')
        _check(case['id'] not in ids, 'duplicate case ID')
        ids.add(case['id'])
        _check(case['label_status'] in STATUSES, 'invalid label_status')
        _check(case['expected'] in labels if case['label_status'] == 'settled' else case['expected'] is None, 'settled expected must be canonical; unsettled expected must be null')
        _check(case['noise_level'] in NOISE, 'invalid noise_level')
        _check(isinstance(case['tags'], list), 'tags must be array')
        for tag in case['tags']:
            _check(isinstance(tag, str) and bool(tag.strip()) and tag == tag.lower(), 'tags must be nonempty lowercase strings')
        _check(len(set(case['tags'])) == len(case['tags']), 'duplicate tags')
        if 'source_family_id' in case:
            _id(case['source_family_id'], 'source_family_id')
        if 'split' in case:
            _check(case['split'] in ('development', 'calibration', 'held_out'), 'invalid split')
        if 'desired_abstention' in case:
            _check(type(case['desired_abstention']) is bool, 'desired_abstention must be boolean')
        if 'notes' in case:
            _check(isinstance(case['notes'], str), 'notes must be a string')
        if suite['adapter'] == 'generic-question':
            _check(isinstance(case['input'], str) and bool(case['input'].strip()), 'generic input must be nonblank string')
        else:
            _check(isinstance(case['input'], dict), 'block input must be object')
    qids = _entries(suite['questions'], 'questions')
    rids = _entries(suite['rules'], 'rules')
    cids = _entries(suite['configurations'], 'configurations')
    _object(suite['baseline'], ('question_id', 'rule_id', 'config_id'), where='baseline')
    for key, valid in zip(('question_id', 'rule_id', 'config_id'), (qids, rids, cids)):
        _check(suite['baseline'][key] in valid, 'unresolved baseline ' + key)
    base = next(q for q in suite['questions'] if q['id'] == suite['baseline']['question_id'])
    _check(base.get('variant_kind') == 'baseline', 'baseline question must have baseline variant_kind')
    for q in suite['questions']:
        _object(q, ('id', 'variant_kind', 'definition'), where='question entry')
        _check(q['variant_kind'] in ('baseline', 'wording', 'choice-description'), 'invalid variant_kind')
        _check(q['variant_kind'] != 'baseline' or q is base, 'only selected baseline may have baseline kind')
        definition = q['definition']
        required = ('name', 'type', 'instructions', 'criteria') if suite['question_type'] == 'choice' else ('name', 'type', 'instructions')
        _object(definition, required, where='question definition')
        _string(definition['name'], 'question.name')
        _string(definition['instructions'], 'question.instructions')
        _check(definition['type'] == suite['question_type'], 'question type mismatch')
        _check(definition['name'] == base['definition']['name'], 'question name mismatch')
        if suite['question_type'] == 'choice':
            criteria = definition['criteria']
            _check(isinstance(criteria, dict) and list(criteria) == labels, 'criteria label/order mismatch')
            for description in criteria.values():
                _string(description, 'choice description')
        if q['variant_kind'] == 'wording':
            _check(definition.get('criteria') == base['definition'].get('criteria'), 'wording must preserve criteria')
        if q['variant_kind'] == 'choice-description':
            _check(suite['question_type'] == 'choice', 'choice-description requires choice type')
            _check(definition['instructions'] == base['definition']['instructions'], 'choice-description must preserve instructions')
    for rule in suite['rules']:
        _object(rule, ('id', 'definition'), where='rule entry')
        _object(rule['definition'], ('name', 'conditions'), where='rule definition')
        _string(rule['definition']['name'], 'rule.name')
        _check(isinstance(rule['definition']['conditions'], list), 'conditions must be array')
        for condition in rule['definition']['conditions']:
            _object(condition, ('field', 'op', 'value'), where='condition')
            _string(condition['field'], 'condition.field')
            allowed = {'confidence', 'answer_confidence', 'action.act_probability'} | ({'probability_gap', 'normalized_entropy'} if suite['question_type'] == 'choice' else {'distance_from_boundary'})
            _check(condition['field'] in allowed, 'condition field incompatible with question type')
            _check(type(condition['value']) in (int, float) and math.isfinite(condition['value']), 'condition value must be finite numeric threshold')
            _check(condition['op'] in ('eq', 'gt', 'gte', 'lt', 'lte'), 'unsupported condition operator')
    for cfg in suite['configurations']:
        _object(cfg, ('id', 'model', 'temperature', 'lang'), where='configuration')
        _string(cfg['model'], 'model')
        _string(cfg['lang'], 'lang')
        t = cfg['temperature']
        _check(t is None or (type(t) in (float, int) and math.isfinite(t) and t >= 0), 'invalid temperature')
        _check(t is not None or cfg['lang'] == 'en', 'null temperature only supports en')
    exclusions = suite.get('exclusions', [])
    _check(isinstance(exclusions, list), 'exclusions must be array')
    seen = set()
    for ex in exclusions:
        _object(ex, ('question_id', 'rule_id', 'config_id', 'reason'), where='exclusion')
        _string(ex['reason'], 'exclusion.reason')
        for key, valid in zip(('question_id', 'rule_id', 'config_id'), (qids, rids, cids)):
            _check(ex[key] in valid, 'unresolved exclusion ' + key)
        triple = tuple(ex[k] for k in ('question_id', 'rule_id', 'config_id'))
        _check(triple not in seen, 'duplicate exclusion')
        seen.add(triple)
    validate_runtime(cases, suite)


def vectors(suite):
    excluded = {(e['question_id'], e['rule_id'], e['config_id']) for e in suite.get('exclusions', [])}
    return [(q['id'], r['id'], c['id']) for q in suite['questions'] for r in suite['rules'] for c in suite['configurations'] if (q['id'], r['id'], c['id']) not in excluded]


def validate_runtime(cases, suite):
    """Use production contracts without loading the SDK or a model."""
    import importlib
    source = Path(__file__).resolve().parents[2] / 'src'
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))
    from questions.models import Question
    from block_runtime.catalog import TypedRule
    from laya.config import RunConfig
    for question in suite['questions']:
        Question.from_dict(question['definition'])
    for rule in suite['rules']:
        TypedRule.from_dict({**rule['definition'], 'question_type': suite['question_type']})
    for config in suite['configurations']:
        RunConfig.from_dict({k:v for k,v in config.items() if k != 'id'})
    if suite['adapter'] != 'generic-question':
        module = importlib.import_module('building_blocks.questions.' + suite['adapter'].replace('-', '_') + '.block')
        expected_name = suite['adapter'].replace('-', '_')
        expected_labels = module.ACTIONS if suite['adapter'] == 'requested-action' else module.SCOPES
        _check(suite['question_type'] == 'choice' and set(suite['labels']) == set(expected_labels), 'block labels/type mismatch')
        _check(all(q['definition']['name'] == expected_name for q in suite['questions']), 'block question name mismatch')
        for case in cases['cases']:
            module.validate_input(case['input'])

