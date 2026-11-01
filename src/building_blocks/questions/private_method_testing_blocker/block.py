"""Classify a reported private-method reason for missing requested tests."""
from copy import deepcopy
from pathlib import Path

from block_runtime import Block, PreparedInput

BLOCK_DIR = Path(__file__).parent
CHOICES = frozenset({'yes', 'no'})
QUESTION = 'private_method_testing_blocker'


def validate_input(value):
    if (not isinstance(value, dict) or set(value) != {'response'}
            or not isinstance(value['response'], str) or not value['response'].strip()):
        raise ValueError('private_method_testing_blocker requires only a nonblank string response')
    return deepcopy(value)


def prepare(value, questions):
    return PreparedInput(value['response'], questions, {})


def validate_prepared(prepared, _original):
    if not prepared.text.strip():
        raise ValueError('prepared text must be nonblank')
    question = prepared.questions[QUESTION]
    if question['type'] != 'choice' or set(question['criteria']) != CHOICES:
        raise ValueError('private_method_testing_blocker requires the yes and no choice IDs')


def reduce(decisions, _state):
    return {QUESTION: decisions[QUESTION]['answer'] if decisions else 'undecided'}


def validate_output(value):
    if (not isinstance(value, dict) or set(value) != {QUESTION}
            or not isinstance(value[QUESTION], str)
            or value[QUESTION] not in CHOICES | {'undecided'}):
        raise ValueError('invalid private_method_testing_blocker result')
    return value


def run(input_data, *, config, registry, rule_overrides=None, question_overrides=None,
        prepare_input=None, catalog=None):
    """Return the reported blocker decision using the shared V2 runtime."""
    block = Block(BLOCK_DIR / 'block.json', validate_input=validate_input,
                  prepare_input=prepare, validate_prepared=validate_prepared,
                  reduce=reduce, validate_output=validate_output, catalog=catalog)
    return block.run(input_data, config=config, registry=registry,
                     rule_overrides=rule_overrides, question_overrides=question_overrides,
                     prepare_input=prepare_input)
