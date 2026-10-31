"""Phase-zero legacy contract snapshots (test-plan A01–A10).

Expected payloads and decisions are independent of production preparation code.
"""
from examples._plumbing_inspection import plumbing_provider
import copy
import inspect
import json

import pytest

from laya_context_router.building_blocks.questions.method_selection import block as method
from laya_context_router.building_blocks.questions.ticket_triage import block as ticket
from laya_context_router.laya.config import RunConfig
from laya_context_router.laya.registry import AgentRegistry
from test_interpret import REQUEST, RAW


SOURCE = {'path': '/project/example.ts', 'source_hash': 'fixed-hash', 'callables': [
    {'id': 'opaque-a', 'name': 'alpha', 'signature': 'function alpha(value: number): number',
     'location': {'line': 1, 'column': 1}, 'start': 0, 'end': 45},
    {'id': 'opaque-b', 'name': 'beta', 'signature': 'function beta(): string',
     'location': {'line': 3, 'column': 1}, 'start': 46, 'end': 80},
]}
PAYLOAD = {
    'method': {'type': 'choice', 'instructions': 'Select exactly one callable that the request asks to explain. Choose none_or_unclear when no single callable is appropriate.',
               'criteria': {'alpha': 'function alpha(value: number): number', 'beta': 'function beta(): string',
                            'none_or_unclear': 'No single matching callable, or unclear request.'}},
    'multiple_relevant': {'type': 'noul', 'instructions': 'Does the request require explaining more than one candidate callable?'},
}
ACCEPT = {'answer': 'alpha', 'decided': True, 'reason': None}
NO = {'answer': 'no', 'decided': True, 'reason': None}


def response(selected='alpha', confidence=.95, multiple=.1, multiple_confidence=.95):
    return {'answers': {
        'method': {'type': 'choice', 'choice': selected, 'answer_confidence': confidence,
                   'probabilities': {key: .9 if key == selected else .05 for key in ('alpha', 'beta', 'none_or_unclear')}},
        'multiple_relevant': {'type': 'noul', 'noul': multiple, 'answer_confidence': multiple_confidence},
    }}


def fake_registry(raw, calls, expected=PAYLOAD, text='Explain alpha', mutate=False):
    class Fake:
        def predict(self, actual_text, questions, **kwargs):
            assert (actual_text, questions, kwargs) == (text, expected, {})
            assert list(questions) == list(expected)
            if 'method' in questions:
                assert list(questions['method']['criteria']) == list(expected['method']['criteria'])
            calls.append(copy.deepcopy((actual_text, questions, kwargs)))
            if mutate:
                questions['method']['instructions'] = 'mutated by SDK'
            return copy.deepcopy(raw)
    return AgentRegistry(inspection_provider=plumbing_provider, loader=lambda model: Fake())


def execute(source=SOURCE, raw=None, calls=None, **kwargs):
    if calls is None:
        calls = []
    return method.run('Explain alpha', source, config=RunConfig(),
                      registry=fake_registry(response() if raw is None else raw, calls), **kwargs)


def expected_result(reason=None, selected='opaque-a', decisions=None, source=SOURCE):
    return {'selected_id': selected, 'reason': reason,
            'decisions': {'method': ACCEPT, 'multiple_relevant': NO} if decisions is None else decisions,
            'candidate_map': {c['id']: {**copy.deepcopy(c), 'path': source['path'], 'source_hash': source['source_hash']} for c in source['callables']},
            'label_map': {c['name']: c['id'] for c in source['callables']}}


@pytest.mark.parametrize('second,expected', [
    (False, {'department': {'answer': 'billing', 'decided': True, 'reason': None},
             'churn_risk': {'answer': 'undecided', 'decided': False, 'reason': 'below_threshold:distance_from_boundary'}}),
    (True, {'department': {'answer': 'undecided', 'decided': False, 'reason': 'below_threshold:answer_confidence'},
            'churn_risk': {'answer': 'yes', 'decided': True, 'reason': None}}),
])
def test_A01_A02_ticket_capture_exact_payload_and_independent_decisions(second, expected):
    payload = {name: copy.deepcopy(REQUEST['questions'][name]) for name in ('department', 'churn_risk')}
    raw = {'answers': {name: copy.deepcopy(RAW['answers'][name]) for name in payload}}
    if second:
        raw['answers']['department'].update(choice='technical', answer_confidence=.8,
                                            probabilities={'billing': .1, 'technical': .8, 'sales': .1})
        raw['answers']['churn_risk'].update(noul=.8, answer_confidence=.8)
    before = copy.deepcopy((payload, raw)); calls = []
    assert ticket.run(REQUEST['text'], config=RunConfig(), registry=fake_registry(raw, calls, payload, REQUEST['text'])) == expected
    assert len(calls) == 1
    assert (payload, raw) == before


def test_A03_A04_method_exact_payload_maps_and_accepted_result():
    calls = []
    assert execute(calls=calls) == expected_result()
    assert len(calls) == 1


@pytest.mark.parametrize('raw,reason,decisions', [
    (response(confidence=.1), 'method_undecided', {'method': {'answer': 'undecided', 'decided': False, 'reason': 'below_threshold:answer_confidence'}, 'multiple_relevant': NO}),
    (response(selected='none_or_unclear'), 'no_single_match', {'method': {'answer': 'none_or_unclear', 'decided': True, 'reason': None}, 'multiple_relevant': NO}),
    (response(multiple_confidence=.1), 'multiple_undecided', {'method': ACCEPT, 'multiple_relevant': {'answer': 'undecided', 'decided': False, 'reason': 'below_threshold:answer_confidence'}}),
    (response(multiple=.9), 'multiple_relevant', {'method': ACCEPT, 'multiple_relevant': {'answer': 'yes', 'decided': True, 'reason': None}}),
])
def test_A05_method_no_selection_reasons(raw, reason, decisions):
    calls = []
    assert execute(raw=raw, calls=calls) == expected_result(reason, None, decisions)
    assert len(calls) == 1


@pytest.mark.parametrize('case,reason', [('empty', 'no_candidates'), ('budget', 'candidate_budget_exceeded'), ('signature', 'ambiguous_candidates')])
def test_A06_skips_do_not_load_or_predict(case, reason):
    source = copy.deepcopy(SOURCE); kwargs = {}
    if case == 'empty':
        source['callables'] = []
    elif case == 'budget':
        kwargs['max_candidates'] = 1
    else:
        source['callables'][1]['signature'] = source['callables'][0]['signature']
    def forbidden(*args, **kwargs):
        pytest.fail('skip must not load or predict')
    result = method.run('Explain alpha', source, config=RunConfig(), registry=AgentRegistry(inspection_provider=plumbing_provider, loader=forbidden), **kwargs)
    assert result == expected_result(reason, None, {}, source)


def test_A07_duplicate_names_disambiguate_by_location():
    source = copy.deepcopy(SOURCE)
    for candidate in source['callables']:
        candidate['name'] = 'same'
    payload = copy.deepcopy(PAYLOAD)
    payload['method']['criteria'] = {'same@1:1': SOURCE['callables'][0]['signature'], 'same@3:1': SOURCE['callables'][1]['signature'], 'none_or_unclear': PAYLOAD['method']['criteria']['none_or_unclear']}
    raw = response(); raw['answers']['method'].update(choice='same@1:1', probabilities={'same@1:1': .9, 'same@3:1': .05, 'none_or_unclear': .05})
    calls = []
    result = method.run('Explain alpha', source, config=RunConfig(), registry=fake_registry(raw, calls, payload))
    assert result['selected_id'] == 'opaque-a'
    assert result['label_map'] == {'same@1:1': 'opaque-a', 'same@3:1': 'opaque-b'}
    assert len(calls) == 1


@pytest.mark.parametrize('case', ['duplicate_id', 'duplicate_label', 'missing_signature', 'nonobject', 'missing_list'])
def test_A07_invalid_candidates_fail_before_model(case):
    source = copy.deepcopy(SOURCE)
    if case == 'duplicate_id': source['callables'][1]['id'] = 'opaque-a'
    elif case == 'duplicate_label':
        source['callables'][1].update(name='alpha', location={'line': 1, 'column': 1})
    elif case == 'missing_signature': del source['callables'][0]['signature']
    elif case == 'nonobject': source['callables'][0] = None
    else: del source['callables']
    def forbidden(*args, **kwargs): pytest.fail('invalid input must not load')
    with pytest.raises(ValueError, match='candidate'):
        method.run('x', source, config=RunConfig(), registry=AgentRegistry(inspection_provider=plumbing_provider, loader=forbidden))


def test_A08_payload_and_source_mapping_are_independent_copies():
    source = copy.deepcopy(SOURCE); before = copy.deepcopy(source); calls = []
    result = method.run('Explain alpha', source, config=RunConfig(), registry=fake_registry(response(), calls, mutate=True))
    result['candidate_map']['opaque-a']['location']['line'] = 999
    result['label_map']['alpha'] = 'corrupted'
    calls[0][1]['method']['criteria']['alpha'] = 'corrupted'
    assert source == before
    assert execute(source=source) == expected_result()


def test_A09_unicode_character_budget_exact_boundary_and_overflow():
    text = 'Explain α🦊'; calls = []
    size = len(text) + len(json.dumps(PAYLOAD, ensure_ascii=False, separators=(',', ':')))
    for budget, expected in [(size, expected_result()), (size - 1, expected_result('input_budget_exceeded', None, {}))]:
        registry = fake_registry(response(), calls, text=text)
        assert method.run(text, SOURCE, config=RunConfig(), registry=registry, max_input_chars=budget) == expected
    assert len(calls) == 1
    assert calls[0][0] == text and calls[0][1] == PAYLOAD


def test_A10_public_signatures_and_plain_dictionary_contract():
    assert str(inspect.signature(ticket.run)) == '(text, *, config, registry, strict=False)'
    assert str(inspect.signature(method.run)) == '(text, source_outline, *, config, registry, max_candidates=64, max_input_chars=16000, strict=False)'
    result = execute()
    assert type(result) is dict
    assert list(result) == ['selected_id', 'reason', 'decisions', 'candidate_map', 'label_map']
    assert list(result['decisions']) == ['method', 'multiple_relevant']
    assert all(list(decision) == ['answer', 'decided', 'reason'] for decision in result['decisions'].values())


def test_A01_A05_default_policy_json_snapshots():
    assert json.loads((ticket.BLOCK_DIR / 'rules.json').read_text()) == {'rules_by_question': {
        'department': {'name': 'department-policy', 'conditions': [{'field': 'answer_confidence', 'op': 'gte', 'value': .9}], 'conditions_by_type': {'choice': [{'field': 'probability_gap', 'op': 'gte', 'value': .5}]}},
        'churn_risk': {'name': 'churn-policy', 'conditions': [{'field': 'distance_from_boundary', 'op': 'gte', 'value': .1}]}}}
    assert json.loads((method.BLOCK_DIR / 'rules.json').read_text()) == {'rules_by_question': {
        'method': {'name': 'method-selection', 'conditions': [{'field': 'answer_confidence', 'op': 'gte', 'value': .5}], 'conditions_by_type': {'choice': [{'field': 'probability_gap', 'op': 'gte', 'value': .15}]}},
        'multiple_relevant': {'name': 'multiple-methods', 'conditions': [{'field': 'answer_confidence', 'op': 'gte', 'value': .5}]}}}
