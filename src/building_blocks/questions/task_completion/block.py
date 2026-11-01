"""Classify reported task completion from a subagent's final response."""
from copy import deepcopy
from pathlib import Path

from block_runtime import Block, PreparedInput

BLOCK_DIR = Path(__file__).parent
CHOICES = frozenset({'yes', 'no'})


def validate_input(value):
    if (not isinstance(value, dict) or set(value) != {'response'}
            or not isinstance(value['response'], str) or not value['response'].strip()):
        raise ValueError('task_completion requires only a nonblank string response')
    return deepcopy(value)


def prepare(value, questions):
    return PreparedInput(value['response'], questions, {})


def validate_prepared(prepared, _original):
    if not prepared.text.strip():
        raise ValueError('task_completion prepared text must be nonblank')
    question = prepared.questions['task_completion']
    if question['type'] != 'choice' or set(question['criteria']) != CHOICES:
        raise ValueError('task_completion requires the stable yes/no choices')


def reduce(decisions, _state):
    return {'completion': decisions['task_completion']['answer'] if decisions else 'undecided'}


def validate_output(value):
    if (not isinstance(value, dict) or set(value) != {'completion'}
            or not isinstance(value['completion'], str)
            or value['completion'] not in CHOICES | {'undecided'}):
        raise ValueError('invalid task_completion result')
    return value


def run(input_data, *, config, registry, rule_overrides=None, question_overrides=None,
        prepare_input=None, catalog=None):
    """Return the reported-completion decision, without verifying artifacts."""
    block = Block(BLOCK_DIR / 'block.json', validate_input=validate_input,
                  prepare_input=prepare, validate_prepared=validate_prepared,
                  reduce=reduce, validate_output=validate_output, catalog=catalog)
    return block.run(input_data, config=config, registry=registry,
                     rule_overrides=rule_overrides, question_overrides=question_overrides,
                     prepare_input=prepare_input)
