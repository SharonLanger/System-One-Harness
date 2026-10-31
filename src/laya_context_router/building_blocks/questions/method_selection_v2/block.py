"""Dynamic readable method questions with private source identity mapping."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

from ....block_runtime import Block, PreparedInput, SkipBlock
from ...typescript import _validate_outline, TypeScriptError

BLOCK_DIR = Path(__file__).parent
DEFAULT_TEMPERATURE = 0.5


def _maps(outline):
    candidates = outline['callables']
    mapping = {c['id']: {**deepcopy(c), 'path': outline['path'],
                         'source_hash': outline['source_hash']} for c in candidates}
    counts = {name: sum(c['name'] == name for c in candidates) for name in {c['name'] for c in candidates}}
    labels = {}
    for candidate in candidates:
        label = candidate['name']
        if counts[label] > 1 or label == 'none_or_unclear':
            label += f"@{candidate['location']['line']}:{candidate['location']['column']}"
        if label in labels:
            raise ValueError('duplicate readable candidate label')
        labels[label] = candidate['id']
    return mapping, labels


def _state(value):
    mapping, labels = _maps(value['source_outline'])
    return {'candidate_map': mapping, 'label_map': labels, 'reason': None}


def _skip(reason, state):
    raise SkipBlock(reason, {**state, 'reason': reason})


def prepare(value, questions):
    state = _state(value)
    candidates = value['source_outline']['callables']
    if not candidates:
        _skip('no_candidates', state)
    if len(candidates) > value['max_candidates']:
        _skip('candidate_budget_exceeded', state)
    if len({c['signature'] for c in candidates}) != len(candidates):
        _skip('ambiguous_candidates', state)
    sentinel = questions['method']['criteria']['none_or_unclear']
    questions['method']['criteria'] = {label: state['candidate_map'][source_id]['signature']
                                      for label, source_id in state['label_map'].items()}
    questions['method']['criteria']['none_or_unclear'] = sentinel
    prepared = PreparedInput(value['text'], questions, state)
    _budget(prepared, value)
    return prepared


def _budget(prepared, value):
    size = len(prepared.text) + len(json.dumps(prepared.questions, ensure_ascii=False, separators=(',', ':')))
    if size > value['max_input_chars']:
        _skip('input_budget_exceeded', prepared.state)


def validate_prepared(prepared, value):
    expected = _state(value)
    if (not isinstance(prepared.state, dict)
            or prepared.state.get('candidate_map') != expected['candidate_map']
            or prepared.state.get('label_map') != expected['label_map']):
        raise ValueError('invalid prepared candidate map or label mapping')
    candidates = value['source_outline']['callables']
    if not candidates: _skip('no_candidates', prepared.state)
    if len(candidates) > value['max_candidates']: _skip('candidate_budget_exceeded', prepared.state)
    if len({c['signature'] for c in candidates}) != len(candidates): _skip('ambiguous_candidates', prepared.state)
    criteria = prepared.questions['method']['criteria']
    if set(criteria) != set(expected['label_map']) | {'none_or_unclear'}:
        raise ValueError('prepared method criteria must match readable candidate labels')
    _budget(prepared, value)
    return prepared


def reduce(decisions, state):
    reason = state.get('reason')
    selected_id = None
    if decisions:
        method, multiple = decisions['method'], decisions['multiple_relevant']
        if not method['decided']: reason = 'method_undecided'
        elif method['answer'] == 'none_or_unclear': reason = 'no_single_match'
        elif not multiple['decided']: reason = 'multiple_undecided'
        elif multiple['answer'] == 'yes': reason = 'multiple_relevant'
        elif method['answer'] not in state['label_map']: reason = 'unknown_candidate'
        else: selected_id = state['label_map'][method['answer']]
    return {'selected_id': selected_id, 'reason': reason,
            'candidate_map': deepcopy(state['candidate_map']), 'label_map': deepcopy(state['label_map'])}


def validate_output(value):
    if (not isinstance(value, dict) or set(value) != {'selected_id', 'reason', 'candidate_map', 'label_map'}
            or not isinstance(value['candidate_map'], dict) or not isinstance(value['label_map'], dict)
            or (value['reason'] is not None and not isinstance(value['reason'], str))
            or (value['selected_id'] is not None and (value['selected_id'] not in value['candidate_map']
                or value['selected_id'] not in value['label_map'].values() or value['reason'] is not None))):
        raise ValueError('invalid method selection result')
    return value


def run(input_data, *, config, registry, max_candidates=64, max_input_chars=16000,
        rule_overrides=None, question_overrides=None, prepare_input=None, catalog=None):
    """Use the selected profile unless the caller explicitly supplies a temperature.

    Accept a full validated outline; budgets count Unicode characters, not tokens.
    """
    effective_config = replace(config, temperature=DEFAULT_TEMPERATURE) if config.temperature is None else config
    def validate_input(value):
        if (type(max_candidates) is not int or max_candidates < 0
                or type(max_input_chars) is not int or max_input_chars <= 0):
            raise ValueError('budgets must be nonnegative candidates and positive input characters')
        if not isinstance(value, dict) or not isinstance(value.get('text'), str):
            raise ValueError('method input must be an object with string text')
        outline = value.get('source_outline')
        if not isinstance(outline, dict) or not isinstance(outline.get('path'), str) or not outline['path']:
            raise ValueError('method input requires a full source outline')
        try:
            _validate_outline(outline, outline['path'])
        except TypeScriptError as exc:
            raise ValueError('invalid source outline or candidate') from exc
        _maps(outline)
        return {**deepcopy(value), 'max_candidates': max_candidates, 'max_input_chars': max_input_chars}
    block = Block(BLOCK_DIR / 'block.json', validate_input=validate_input, prepare_input=prepare,
                  reduce=reduce, validate_output=validate_output, validate_prepared=validate_prepared, catalog=catalog)
    return block.run(input_data, config=effective_config, registry=registry, rule_overrides=rule_overrides,
                     question_overrides=question_overrides, prepare_input=prepare_input)
