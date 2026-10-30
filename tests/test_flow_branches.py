"""Bounded composition exercises actual blocks; only SDK boundary is controlled."""
import copy
import json

import pytest

from laya_context_router.blocks import QuestionBlock
from laya_context_router.building_blocks.questions.ticket_triage.block import BLOCK_DIR
from laya_context_router.building_blocks.typescript import outline
from laya_context_router.flows.file_method_context import run
from laya_context_router.laya.config import RunConfig
from laya_context_router.laya.registry import AgentRegistry
from test_method_selection import questions_for, raw_for

A = RunConfig('mock-A', 0.2, 'fr')
B = RunConfig('mock-B', 0.7, 'en')


def setup(tmp_path):
    path = tmp_path / 'a.ts'
    path.write_text('function greet() { return 1; }')
    data = outline(path)
    prompt = 'Explain `a.ts`: explain greet'
    second = prompt + '\n\nFallback candidate signatures (same source snapshot):\n' + '\n'.join(
        f'{c["signature"]}' for c in data['callables'])
    return path, data, prompt, second, questions_for(data)


def sequence_registry(sequence):
    remaining = list(sequence); loads = []; calls = []
    class Agent:
        def __init__(self, config): self.config = config
        def predict(self, text, questions, **kwargs):
            expected_config, expected_text, expected_questions, response = remaining.pop(0)
            assert self.config == expected_config
            assert (text, questions, kwargs) == (expected_text, expected_questions, self.config.predict_kwargs())
            calls.append(self)
            if isinstance(response, Exception): raise response
            return copy.deepcopy(response)
    def loader(model, **kwargs):
        config = next(c for c in (A, B) if (c.model, c.load_kwargs()) == (model, kwargs))
        agent = Agent(config); loads.append(agent); return agent
    return AgentRegistry(loader=loader), remaining, loads, calls


def execute(tmp_path, prompt, registry, **kwargs):
    return run(prompt, cwd=tmp_path, repository_root=tmp_path, config=A, registry=registry, **kwargs)


@pytest.mark.parametrize('second_outcome', ['accepted', 'rejected', 'abstain', 'error'])
def test_opt_in_two_round_sequence_terminates(tmp_path, second_outcome):
    _, data, prompt, second, q = setup(tmp_path); selected = data['callables'][0]['signature']
    response = raw_for(q, selected)
    if second_outcome == 'rejected': response = raw_for(q, selected, confidence=0.1)
    if second_outcome == 'abstain': response = raw_for(q, 'none_or_unclear')
    if second_outcome == 'error': response = RuntimeError('planned')
    reg, remaining, loads, calls = sequence_registry([
        (A, prompt, q, raw_for(q, selected, confidence=0.1)), (B, second, q, response)])
    result = execute(tmp_path, prompt, reg, fallback_config=B)
    assert result['status'] == ('context' if second_outcome == 'accepted' else 'noop')
    assert result['reason'] == {'accepted': None, 'rejected': 'method_undecided', 'abstain': 'no_single_match', 'error': 'model_error'}[second_outcome]
    assert not remaining and len(calls) == 2 and len(loads) == 2


@pytest.mark.parametrize('choice,confidence,multiple,reason', [
    ('candidate', .95, .1, None), ('none_or_unclear', .95, .1, 'no_single_match'),
    ('candidate', .95, .9, 'multiple_relevant'), ('candidate', .1, .9, 'method_undecided'),
    ('candidate', .1, .5, 'method_undecided'), ('candidate', .95, .5, 'multiple_relevant'),
])
def test_explicit_outcomes_never_trigger_fallback(tmp_path, choice, confidence, multiple, reason):
    _, data, prompt, _, q = setup(tmp_path)
    selected = data['callables'][0]['signature'] if choice == 'candidate' else choice
    reg, remaining, _, calls = sequence_registry([(A, prompt, q, raw_for(q, selected, multiple, confidence))])
    result = execute(tmp_path, prompt, reg, fallback_config=B)
    assert result['reason'] == reason and len(calls) == 1 and not remaining


def test_default_disabled_and_first_error_terminates(tmp_path):
    _, data, prompt, _, q = setup(tmp_path)
    for response, reason in [(raw_for(q, data['callables'][0]['signature'], confidence=.1), 'method_undecided'),
                             (RuntimeError('planned'), 'model_error')]:
        reg, _, _, calls = sequence_registry([(A, prompt, q, response)])
        assert execute(tmp_path, prompt, reg)['reason'] == reason
        assert len(calls) == 1


@pytest.mark.parametrize('delta', [-1, 0, 1])
def test_second_input_budget_exact_boundary(tmp_path, delta):
    _, data, prompt, second, q = setup(tmp_path); selected = data['callables'][0]['signature']
    size = len(second) + len(json.dumps(q, ensure_ascii=False, separators=(',', ':')))
    expected = [(A, prompt, q, raw_for(q, selected, confidence=.1))]
    if delta >= 0: expected.append((B, second, q, raw_for(q, selected)))
    reg, remaining, _, calls = sequence_registry(expected)
    result = execute(tmp_path, prompt, reg, fallback_config=B, fallback_max_input_chars=size+delta)
    assert result['reason'] == ('input_budget_exceeded' if delta < 0 else None)
    assert len(calls) == (1 if delta < 0 else 2) and not remaining


@pytest.mark.parametrize('budget', [0, -1, True])
def test_invalid_second_budget_no_load(tmp_path, budget):
    _, _, prompt, _, _ = setup(tmp_path)
    reg, _, loads, _ = sequence_registry([])
    assert execute(tmp_path, prompt, reg, fallback_config=B, fallback_max_input_chars=budget)['reason'] == 'invalid_fallback_budget'
    assert not loads


def test_distinct_blocks_independent_policies_and_actual_flow_A_B_A(tmp_path):
    _, data, prompt, second, q = setup(tmp_path); selected = data['callables'][0]['signature']
    block = QuestionBlock(BLOCK_DIR)
    ticket_q = {name: question.to_predict_dict() for name, question in block.questions.items()}
    ticket_raw = {'answers': {
        'department': {'type': 'choice', 'choice': 'technical', 'probabilities': {'billing': .1, 'technical': .8, 'sales': .1}, 'answer_confidence': .8},
        'churn_risk': {'type': 'noul', 'noul': .2, 'answer_confidence': .95}}}
    reg, remaining, loads, calls = sequence_registry([
        (A, prompt, q, raw_for(q, selected, confidence=.1)),
        (B, second, q, raw_for(q, selected, confidence=.8)),
        (A, 'ticket', ticket_q, ticket_raw)])
    assert execute(tmp_path, prompt, reg, fallback_config=B)['status'] == 'context'
    decisions = block.run('ticket', config=A, registry=reg)
    # .8 passes method policy (.3) but fails distinct department policy (.9).
    assert not decisions['department']['decided'] and decisions['churn_risk']['decided']
    assert len(loads) == 2 and calls[0] is calls[2] and calls[0] is not calls[1] and not remaining


def test_low_multiple_confidence_does_not_trigger_fallback(tmp_path):
    _, data, prompt, _, q = setup(tmp_path)
    response = raw_for(q, data['callables'][0]['signature'])
    response['answers']['multiple_relevant']['answer_confidence'] = 0.1
    reg, remaining, _, calls = sequence_registry([(A, prompt, q, response)])
    result = execute(tmp_path, prompt, reg, fallback_config=B)
    assert result['reason'] == 'multiple_undecided'
    assert result['context'] is None and len(calls) == 1 and not remaining
