"""Contract tests for the response-only private-method blocker classifier."""
from copy import deepcopy
import json
from pathlib import Path
import os
import subprocess
import sys
import zipfile
from unittest.mock import Mock

import pytest

from block_runtime import (
    BlockConfigurationError, BlockExecutionError, BlockInputError, Catalog, PreparedInput, SkipBlock,
)
from building_blocks.questions.private_method_testing_blocker import block
from laya.config import RunConfig
from laya.registry import AgentRegistry
from laya.predict import ResponseError

QUESTION = block.QUESTION


def prediction(choice='yes', confidence=.8, probabilities=None):
    return {'answers': {QUESTION: {'type': 'choice', 'choice': choice,
        'probabilities': probabilities or {choice: .8, ('no' if choice == 'yes' else 'yes'): .2},
        'answer_confidence': confidence}}}


class Harness:
    def __init__(self, raw=None):
        self.raw = prediction() if raw is None else raw
        self.calls = []
        self.loads = []
        self.registry = AgentRegistry(loader=self.load)

    def load(self, model, **kwargs):
        self.loads.append((model, kwargs))
        return self

    def predict(self, text, questions, **kwargs):
        self.calls.append((text, deepcopy(questions), kwargs))
        if isinstance(self.raw, Exception):
            raise self.raw
        return self.raw

    def run(self, value=None, **kwargs):
        return block.run({'response': 'I could not add the tests because the method is private.'} if value is None else value,
            config=kwargs.pop('config', RunConfig(model='synthetic')),
            registry=self.registry, **kwargs)


@pytest.mark.parametrize('choice', ['yes', 'no'])
def test_accepted_answers_are_distinct_from_execution_status(choice):
    h = Harness(prediction(choice)); result = h.run()
    assert result.status == 'completed' and result.reason is None
    assert result.decisions == {QUESTION: {'answer': choice, 'decided': True, 'reason': None}}
    assert result.data == {QUESTION: choice}
    assert len(h.loads) == len(h.calls) == 1
    assert h.calls[0][1] == {QUESTION: Catalog().question(QUESTION)}


def test_original_text_and_caller_configuration_are_preserved():
    text = 'הבדיקה לא נכתבה\n"private normalize"\n'
    value = {'response': text}; h = Harness(); raw = deepcopy(h.raw)
    config = RunConfig(model='synthetic', temperature=.2, lang='he')
    h.run(value, config=config)
    assert h.calls[0][0] == text and h.calls[0][2] == {'lang': 'he'}
    assert value == {'response': text} and h.raw == raw and config.temperature == .2


@pytest.mark.parametrize('value', [None, 0, False, [], {}, {'response': None},
    {'response': 12}, {'response': True}, {'response': []}, {'response': ''},
    {'response': ' \n '}, {'response': 'x', 'method': 'normalize'}])
def test_bad_input_fails_before_model_load(value):
    h = Harness()
    with pytest.raises(BlockInputError):
        block.run(value, config=RunConfig(model='synthetic'), registry=h.registry)
    assert not h.loads and not h.calls


@pytest.mark.parametrize('probabilities,confidence,accepted', [
    ({'yes': .8, 'no': .2}, .8, True),
    ({'yes': .50, 'no': .50}, .5, False),
    ({'yes': .51, 'no': .49}, .51, False),
    ({'yes': .8, 'no': .2}, .49, False),
    ({'yes': .575, 'no': .425}, .5, True),
])
def test_rule_rejection_is_undecided_not_no(probabilities, confidence, accepted):
    h = Harness(prediction('yes', confidence, probabilities)); r = h.run()
    assert r.status == 'completed'
    assert r.decisions[QUESTION]['decided'] is accepted
    assert r.data == {QUESTION: 'yes' if accepted else 'undecided'}


def test_skip_is_distinct_from_no():
    h = Harness()
    def skip(*_): raise SkipBlock('caller_skip')
    r = h.run(prepare_input=skip)
    assert (r.status, r.reason, r.decisions, r.data) == ('skipped', 'caller_skip', {}, {QUESTION: 'undecided'})
    assert not h.loads and not h.calls


def test_wording_override_order_and_custom_preparer_do_not_mutate_inputs():
    question = Catalog().question(QUESTION)
    question['instructions'] = 'Alternative wording'
    question['criteria'] = dict(reversed(list(question['criteria'].items())))
    original = deepcopy(question); h = Harness()
    def custom(value, questions):
        value['response'] = 'changed copy'
        questions[QUESTION]['instructions'] = 'Prepared wording'
        return PreparedInput('custom text', questions, {})
    value = {'response': 'original'}
    h.run(value, question_overrides={QUESTION: question}, prepare_input=custom)
    assert value == {'response': 'original'} and question == original
    assert h.calls[0][0] == 'custom text'
    assert h.calls[0][1][QUESTION]['instructions'] == 'Prepared wording'


@pytest.mark.parametrize('criteria', [
    {'yes': 'y'}, {'yes': 'y', 'no': 'n', 'maybe': 'm'}, {'yes': 'y', 'other': 'n'},
])
def test_changed_choice_vocabulary_is_rejected_before_prediction(criteria):
    question = Catalog().question(QUESTION); question['criteria'] = criteria
    h = Harness()
    with pytest.raises(BlockInputError): h.run(question_overrides={QUESTION: question})
    assert not h.loads and not h.calls


def test_missing_rule_or_unknown_override_key_is_configuration_error():
    for override in ({QUESTION: 'missing'}, {'unexpected': 'private_method_testing_blocker_default'}):
        h = Harness()
        with pytest.raises(BlockConfigurationError): h.run(rule_overrides=override)
        assert not h.loads and not h.calls


def test_bad_custom_preparation_is_input_error():
    h = Harness()
    with pytest.raises(BlockInputError): h.run(prepare_input=lambda _v, q: PreparedInput(' \n', q))
    assert not h.loads and not h.calls


@pytest.mark.parametrize('change', ['unknown_choice', 'missing_answer', 'missing_probability', 'nan'])
def test_invalid_model_response_does_not_become_no(change):
    raw = prediction(); answer = raw['answers'][QUESTION]
    if change == 'unknown_choice': answer['choice'] = 'maybe'
    if change == 'missing_answer': raw['answers'].clear()
    if change == 'missing_probability': del answer['probabilities']['no']
    if change == 'nan': answer['answer_confidence'] = float('nan')
    h = Harness(raw)
    with pytest.raises(ResponseError): h.run()
    assert len(h.calls) == 1


def test_loader_predictor_and_timeout_errors_are_not_swallowed():
    for error in (RuntimeError('load'), RuntimeError('predict'), TimeoutError('deadline')):
        h = Harness(error)
        if str(error) == 'load': h.registry = AgentRegistry(loader=Mock(side_effect=error))
        with pytest.raises(type(error)) as caught: h.run()
        assert caught.value is error


def test_invalid_reducer_output_is_wrapped(monkeypatch):
    h = Harness(); monkeypatch.setattr(block, 'reduce', lambda *_: {QUESTION: 'maybe'})
    with pytest.raises(BlockExecutionError): h.run()


def test_reused_registry_and_isolated_results():
    h = Harness()
    first = h.run(); first.data[QUESTION] = 'changed'; first.decisions.clear()
    second = h.run()
    assert second.data == {QUESTION: 'yes'} and second.decisions[QUESTION]['answer'] == 'yes'
    assert len(h.loads) == 1 and len(h.calls) == 2


def test_semantic_fixtures_are_reviewable_data_not_mocked_accuracy():
    path = Path(__file__).resolve().parents[3] / 'fixtures/private_method_testing_blocker_responses.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    assert data['synthetic'] is False
    cases = data['cases']
    assert len(cases) == 23 and len({case['id'] for case in cases}) == len(cases)
    assert {case['expected'] for case in cases} == {'yes', 'no'}
    assert all(case['response'].strip() and case['rationale'] and case['category'] for case in cases)


def test_block_resources_and_execution_in_installed_wheel(tmp_path):
    root = Path(__file__).resolve().parents[4]
    wheel_dir = tmp_path / 'wheels'
    subprocess.run([sys.executable, '-m', 'pip', 'wheel', '--no-build-isolation', '--no-deps',
                    '--wheel-dir', str(wheel_dir), str(root)], check=True, capture_output=True, text=True)
    wheel, = wheel_dir.glob('*.whl')
    installed = tmp_path / 'installed'
    files = [
        'building_blocks/questions/private_method_testing_blocker/block.py',
        'building_blocks/questions/private_method_testing_blocker/block.json',
        'building_blocks/questions/private_method_testing_blocker/README.md',
        'defaults/questions/private_method_testing_blocker.json',
        'defaults/rules/private_method_testing_blocker_default.json',
    ]
    with zipfile.ZipFile(wheel) as archive:
        for item in files:
            path = '' + item
            assert archive.read(path) == (root / 'src' / path).read_bytes()
        archive.extractall(installed)
    code = '''
from building_blocks.questions.private_method_testing_blocker.block import run
from laya.config import RunConfig
from laya.registry import AgentRegistry
class Agent:
 def predict(self, text, questions, **kwargs):
  assert set(questions) == {'private_method_testing_blocker'}
  return {'answers': {'private_method_testing_blocker': {'type': 'choice', 'choice': 'yes', 'probabilities': {'yes': .8, 'no': .2}, 'answer_confidence': .8}}}
result = run({'response': 'No tests because method private'}, config=RunConfig(model='mock'), registry=AgentRegistry(loader=lambda *a, **kw: Agent()))
assert result.data == {'private_method_testing_blocker': 'yes'}
'''
    subprocess.run([sys.executable, '-c', code], cwd=tmp_path,
                   env={**os.environ, 'PYTHONPATH': str(installed)},
                   check=True, capture_output=True, text=True)
