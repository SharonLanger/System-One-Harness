"""Prompt-only requested work classification on the shared V2 runtime."""
from copy import deepcopy
from pathlib import Path
from ....block_runtime import Block, PreparedInput

BLOCK_DIR = Path(__file__).parent
ACTIONS = frozenset(('explain', 'generate_tests', 'modify_code'))


def validate_input(value):
    if (not isinstance(value, dict) or set(value) != {'prompt'}
            or not isinstance(value['prompt'], str) or not value['prompt'].strip()):
        raise ValueError('requested_action requires only a nonblank string prompt')
    return deepcopy(value)


def prepare(value, questions):
    return PreparedInput(value['prompt'], questions, {})


def validate_prepared(prepared, original):
    if not prepared.text.strip():
        raise ValueError('requested_action prepared text must be nonblank')
    question = prepared.questions['requested_action']
    if question['type'] != 'choice' or set(question['criteria']) != ACTIONS:
        raise ValueError('requested_action requires the three stable choice IDs')


def reduce(decisions, state):
    return {'action': decisions.get('requested_action', {}).get('answer', 'undecided')}


def validate_output(value):
    if (not isinstance(value, dict) or set(value) != {'action'}
            or not isinstance(value['action'], str)
            or value['action'] not in ACTIONS | {'undecided'}):
        raise ValueError('invalid requested_action result')
    return value


def run(input_data, *, config, registry, rule_overrides=None, question_overrides=None,
        prepare_input=None, catalog=None):
    """Return BlockResult; callers own registry lifetime and subsequent routing."""
    block = Block(BLOCK_DIR / 'block.json', validate_input=validate_input,
                  prepare_input=prepare, reduce=reduce, validate_output=validate_output,
                  validate_prepared=validate_prepared, catalog=catalog)
    return block.run(input_data, config=config, registry=registry,
                     rule_overrides=rule_overrides, question_overrides=question_overrides,
                     prepare_input=prepare_input)
