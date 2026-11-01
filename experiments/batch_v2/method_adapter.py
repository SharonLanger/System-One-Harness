"""Experiment-only dynamic method-selection adapter; no model load on validation."""
from copy import deepcopy
from pathlib import Path
import json
from block_runtime import PreparedInput
from block_runtime.catalog import Catalog, TypedRule
from building_blocks.questions.method_selection_v2 import block
from laya.config import RunConfig
from questions.models import Question


def execute(value, question, rule, suite, config, registry):
    class ExperimentCatalog(Catalog):
        def rule(self, reference):
            if reference == 'experiment_method':
                return TypedRule.from_dict({**rule['definition'], 'question_type': 'choice'})
            if reference == 'experiment_multiple':
                return TypedRule.from_dict(suite['fixed_rules']['multiple_relevant'])
            return super().rule(reference)
    return block.run(value, config=config, registry=registry, catalog=ExperimentCatalog(),
        question_overrides={'method': question['definition'],
                            'multiple_relevant': suite['fixed_questions']['multiple_relevant']},
        rule_overrides={'method': 'experiment_method', 'multiple_relevant': 'experiment_multiple'})


def prepared(value, question, suite):
    qs = {'method': {k:v for k,v in question['definition'].items() if k != 'name'},
          'multiple_relevant': {k:v for k,v in suite['fixed_questions']['multiple_relevant'].items() if k != 'name'}}
    return block.prepare({**value, 'max_candidates':64, 'max_input_chars':16000}, deepcopy(qs))


def validate(cases, suite):
    from schema import _check, _object, _entries, NOISE
    _check(cases['schema_version'] == suite['schema_version'] == 2, 'method schema version must be 2')
    _check(cases['dataset_id'] == suite['dataset_id'] and cases['dataset_version'] == suite['dataset_version'], 'dataset mismatch')
    _check(suite['question_type'] == 'choice' and suite['label_mode'] == 'dynamic-per-case', 'dynamic choice contract required')
    qids = _entries(suite['questions'], 'questions'); rids = _entries(suite['rules'], 'rules'); cids = _entries(suite['configurations'], 'configurations')
    for key, values in zip(('question_id','rule_id','config_id'), (qids,rids,cids)):
        _check(suite['baseline'][key] in values, 'invalid baseline')
    for q in suite['questions']:
        _check(q['definition']['name']=='method' and q['definition']['type']=='choice', 'invalid method question')
        Question.from_dict(q['definition'])
    Question.from_dict(suite['fixed_questions']['multiple_relevant'])
    TypedRule.from_dict(suite['fixed_rules']['multiple_relevant'])
    for rule in suite['rules']:
        TypedRule.from_dict({**rule['definition'],'question_type':'choice'})
    for cfg in suite['configurations']:
        RunConfig.from_dict({k:v for k,v in cfg.items() if k!='id'})
    _check(not suite.get('exclusions'), 'method campaign has no exclusions')
    families={}; ids=set()
    from building_blocks.typescript import _validate_outline
    for case in cases['cases']:
        _object(case['input'], ('text','source_outline'))
        _check(case['id'] not in ids, 'duplicate case'); ids.add(case['id'])
        _check(isinstance(case['tags'],list) and len(set(case['tags']))==len(case['tags']), 'invalid tags')
        _check(case['label_status']=='settled' and case['noise_level'] in NOISE, 'unsettled or invalid noise')
        _check(case['split'] in ('development','held_out'), 'invalid split')
        family=case['source_family_id']; split=case['split']
        _check(family not in families or families[family]==split, 'family crosses splits'); families[family]=split
        value=case['input']; source=value['source_outline']; _validate_outline(source,source['path'])
        _check(isinstance(value['text'],str) and bool(value['text'].strip()), 'blank text')
        expected=case['expected']; _object(expected, ('method_label','multiple_relevant','selected_id'))
        _check(expected['multiple_relevant'] in ('yes','no'), 'invalid multiple target')
        labels=None
        for q in suite['questions']:
            p=prepared(value,q,suite); current=p.questions['method']['criteria']
            _check(labels is None or current==labels, 'changed dynamic choices'); labels=current
            _check(expected['method_label'] in current, 'unknown expected label')
            mapping=p.state['label_map']
            _check(expected['selected_id']==(mapping.get(expected['method_label']) if expected['multiple_relevant']=='no' else None), 'inconsistent target')
