"""Contract checks with synthetic LAYA responses; semantic accuracy needs live evaluation."""
from copy import deepcopy
from unittest.mock import Mock

import pytest

from laya_context_router.block_runtime import (BlockInputError, BlockConfigurationError,
                                                BlockExecutionError, Catalog, PreparedInput, SkipBlock)
from laya_context_router.building_blocks.questions.task_completion import block
from laya_context_router.laya.config import RunConfig
from laya_context_router.laya.registry import AgentRegistry
from laya_context_router.laya.predict import ResponseError


def answer(label='yes', probabilities=None):
    probabilities = probabilities or ({'yes': .9, 'no': .1} if label == 'yes' else {'yes': .1, 'no': .9})
    return {'answers': {'task_completion': {'type': 'choice', 'choice': label,
            'probabilities': probabilities, 'answer_confidence': probabilities[label]}}}


class Harness:
    def __init__(self, raw=None):
        self.raw = answer() if raw is None else raw
        self.loads = []
        self.calls = []
        self.registry = AgentRegistry(loader=self.load)

    def load(self, model, **kwargs):
        self.loads.append((model, kwargs))
        return self

    def predict(self, text, questions, **kwargs):
        self.calls.append((text, deepcopy(questions), kwargs))
        if isinstance(self.raw, Exception):
            raise self.raw
        return self.raw

    _default = object()

    def run(self, value=_default, **kwargs):
        return block.run({'response': 'Finished the assigned work.'} if value is self._default else value,
                         config=kwargs.pop('config', RunConfig(model='synthetic')),
                         registry=self.registry, **kwargs)


@pytest.mark.parametrize('label', ['yes', 'no'])
def test_accepted_binary_answer(label):
    h = Harness(answer(label)); result = h.run()
    assert result.status == 'completed'
    assert result.decisions == {'task_completion': {'answer': label, 'decided': True, 'reason': None}}
    assert result.data == {'completion': label}
    assert len(h.calls) == len(h.loads) == 1


def test_exact_text_and_caller_config_preserved():
    h = Harness(); config = RunConfig(model='model-a', temperature=.23, lang='he')
    text = ' שורה\nprivate method: "שלום" '
    h.run({'response': text}, config=config)
    assert h.calls[0][0] == text
    assert h.calls[0][1] == {'task_completion': Catalog().question('task_completion')}
    assert h.calls[0][2] == {'lang': 'he'}
    assert h.loads[0][0] == 'model-a'
    assert config.temperature == .23


@pytest.mark.parametrize('value', [None, 3, False, [], {}, {'response': None},
    {'response': 2}, {'response': True}, {'response': []}, {'response': ''},
    {'response': ' \n '}, {'response': 'done', 'assignment': 'five tests'}])
def test_bad_input_rejected_before_model_load(value):
    h = Harness()
    with pytest.raises(BlockInputError): h.run(value)
    assert not h.loads and not h.calls


@pytest.mark.parametrize('probs,expected', [
    ({'yes': .9, 'no': .1}, 'yes'),
    ({'yes': .6, 'no': .4}, 'yes'),
    ({'yes': .55, 'no': .45}, 'undecided'),
    ({'yes': .5, 'no': .5}, 'undecided'),
])
def test_threshold_rejection_is_not_no(probs, expected):
    h = Harness(answer('yes', probs)); result = h.run()
    assert result.data == {'completion': expected}
    assert result.decisions['task_completion']['decided'] == (expected != 'undecided')
    assert len(h.calls) == 1


def test_question_wording_order_rule_and_registry_isolation():
    h = Harness(); catalog = Catalog()
    question = catalog.question('task_completion')
    question['instructions'] = 'Changed wording'
    question['criteria'] = dict(reversed(list(question['criteria'].items())))
    original = deepcopy(question)
    first = h.run(question_overrides={'task_completion': question})
    second = h.run()
    assert first.data == second.data == {'completion': 'yes'}
    assert question == original
    assert h.calls[0][1]['task_completion']['instructions'] == 'Changed wording'
    assert h.calls[1][1]['task_completion']['instructions'] != 'Changed wording'
    assert len(h.loads) == 1


@pytest.mark.parametrize('override', [
    {'question_overrides': {'other': 'task_completion'}},
    {'question_overrides': {'task_completion': 'missing'}},
    {'question_overrides': {'task_completion': {'type':'choice', 'instructions':'x', 'criteria':{'yes':'y'}}}},
    {'question_overrides': {'task_completion': {'type':'choice', 'instructions':'x', 'criteria':{'yes':'y','no':'n','maybe':'m'}}}},
    {'question_overrides': {'task_completion': {'type':'noul', 'instructions':'x'}}},
    {'rule_overrides': {'task_completion': 'missing'}},
    {'rule_overrides': {'task_completion': 'multiple_methods_default'}},
])
def test_invalid_overrides_never_load(override):
    h = Harness()
    with pytest.raises((BlockInputError, BlockConfigurationError)): h.run(**override)
    assert not h.calls and not h.loads


def test_custom_preparation_and_skip():
    h = Harness(); value = {'response': 'original'}
    result = h.run(value, prepare_input=lambda data, questions: PreparedInput('custom', questions))
    assert result.data == {'completion':'yes'} and h.calls[0][0] == 'custom'
    assert value == {'response': 'original'}
    skipped = Harness()
    def skip(*_): raise SkipBlock('caller_skip')
    result = skipped.run(prepare_input=skip)
    assert (result.status, result.decisions, result.data) == ('skipped', {}, {'completion':'undecided'})
    assert not skipped.loads


def test_bad_custom_preparation_and_reducer(monkeypatch):
    h = Harness()
    with pytest.raises(BlockInputError): h.run(prepare_input=lambda _, q: PreparedInput(' ', q))
    assert not h.calls
    monkeypatch.setattr(block, 'reduce', lambda *_: {'completion': 'maybe'})
    with pytest.raises(BlockExecutionError): h.run()


@pytest.mark.parametrize('change', ['missing', 'wrong_choice', 'nan', 'bad_sum'])
def test_malformed_prediction_raises_not_no(change):
    raw = answer()
    if change == 'missing': raw['answers'].clear()
    elif change == 'wrong_choice': raw['answers']['task_completion']['choice'] = 'maybe'
    elif change == 'nan': raw['answers']['task_completion']['probabilities']['yes'] = float('nan')
    elif change == 'bad_sum': raw['answers']['task_completion']['probabilities']['yes'] = .3
    h = Harness(raw)
    with pytest.raises(ResponseError): h.run()
    assert len(h.calls) == 1


def test_prediction_error_propagates_without_retry():
    failure = TimeoutError('deadline'); h = Harness(failure)
    with pytest.raises(TimeoutError) as captured: h.run()
    assert captured.value is failure and len(h.calls) == 1


def test_reducer_validation():
    for value in ({'completion':'maybe'}, {'completion':True}, {}, {'completion':'yes','extra':1}):
        with pytest.raises(ValueError): block.validate_output(value)
