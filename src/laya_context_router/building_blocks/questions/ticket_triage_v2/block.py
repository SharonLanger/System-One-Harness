"""Captured ticket questions on the explicit V2 execution interface."""
from copy import deepcopy
from pathlib import Path
from ....block_runtime import Block, PreparedInput

BLOCK_DIR = Path(__file__).parent


def validate_input(value):
    if not isinstance(value, dict) or not isinstance(value.get('text'), str):
        raise ValueError('ticket input must be an object with string text')
    return deepcopy(value)


def prepare(value, questions):
    return PreparedInput(value['text'], questions, {})


def validate_output(value):
    if value != {}:
        raise ValueError('ticket result data must be an empty object')
    return value


def run(input_data, *, config, registry, rule_overrides=None, question_overrides=None,
        prepare_input=None, catalog=None):
    """Return BlockResult; blank text is preserved, including whitespace."""
    block = Block(BLOCK_DIR / 'block.json', validate_input=validate_input,
                  prepare_input=prepare, reduce=lambda decisions, state: {},
                  validate_output=validate_output, catalog=catalog)
    return block.run(input_data, config=config, registry=registry,
                     rule_overrides=rule_overrides, question_overrides=question_overrides,
                     prepare_input=prepare_input)
