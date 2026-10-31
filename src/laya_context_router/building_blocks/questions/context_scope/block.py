"""Classify requested method relationships through the shared block runtime."""
from copy import deepcopy
import json
from pathlib import Path

from ....block_runtime import Block, PreparedInput

BLOCK_DIR = Path(__file__).parent
SCOPES = frozenset({'method_only', 'called_methods', 'calling_methods', 'both_directions'})
ACTIONS = frozenset({'explain', 'generate_tests', 'modify_code', 'undecided'})


def validate_input(value):
    if not isinstance(value, dict) or not {'prompt'} <= value.keys() or not value.keys() <= {'prompt', 'requested_action'}:
        raise ValueError('context scope input requires prompt and optional requested_action only')
    if not isinstance(value['prompt'], str) or not value['prompt'].strip():
        raise ValueError('prompt must be a nonblank string')
    action = value.get('requested_action')
    if action is not None and (not isinstance(action, str) or action not in ACTIONS):
        raise ValueError('requested_action must be explain, generate_tests, modify_code, undecided, or null')
    return deepcopy(value)


def prepare(value, questions):
    text = value['prompt']
    action = value.get('requested_action')
    if action is not None and action != 'undecided':
        text = json.dumps({'prompt': text, 'requested_action': action}, ensure_ascii=False)
    return PreparedInput(text, questions, {})


def validate_prepared(prepared, _value):
    if not prepared.text.strip():
        raise ValueError('prepared text must be nonblank')
    question = prepared.questions['context_scope']
    if set(question['criteria']) != SCOPES:
        raise ValueError('context scope criteria must retain exactly the four scope IDs')


def reduce(decisions, _state):
    return {'scope': decisions['context_scope']['answer'] if decisions else 'undecided'}


def validate_output(value):
    if not isinstance(value, dict) or set(value) != {'scope'}:
        raise ValueError('context scope output must contain only scope')
    if not isinstance(value['scope'], str) or value['scope'] not in SCOPES | {'undecided'}:
        raise ValueError('unknown context scope')
    return value


def run(input_data, *, config, registry, rule_overrides=None, question_overrides=None,
        prepare_input=None, catalog=None, strict=False):
    """Return BlockResult for a prompt and optional previously selected action."""
    block = Block(BLOCK_DIR / 'block.json', validate_input=validate_input,
                  prepare_input=prepare, validate_prepared=validate_prepared,
                  reduce=reduce, validate_output=validate_output, catalog=catalog)
    return block.run(input_data, config=config, registry=registry,
                     rule_overrides=rule_overrides, question_overrides=question_overrides,
                     prepare_input=prepare_input, strict=strict)
