"""A/D/G parity and input-contract coverage for additive V2 blocks."""
from copy import deepcopy
import json

import pytest

from laya_context_router.building_blocks.questions.ticket_triage_v2.block import run as ticket
from laya_context_router.building_blocks.questions.method_selection_v2.block import run as method
from laya_context_router.building_blocks.questions.ticket_triage.block import run_legacy as old_ticket
from laya_context_router.building_blocks.questions.method_selection.block import run_legacy as old_method
from laya_context_router.laya.config import RunConfig
from laya_context_router.laya.registry import AgentRegistry
from test_interpret import REQUEST, RAW
from test_method_selection import raw_for, questions_for


def source():
    digest = 'a' * 64
    return {'schema_version': 1, 'path': '/project/a.ts', 'source_hash': digest,
            'diagnostics': [], 'limitations': [], 'callables': [
                {'id': f'{digest}:0:20', 'name': 'sum', 'signature': 'function sum()',
                 'start': 0, 'end': 20, 'location': {'line': 1, 'column': 1}},
                {'id': f'{digest}:21:40', 'name': 'sum', 'signature': 'function sum(x: number)',
                 'start': 21, 'end': 40, 'location': {'line': 2, 'column': 1}}]}


def registry(response, calls, expected=None):
    class Fake:
        def predict(self, text, questions, **kwargs):
            if expected is not None:
                assert questions == expected
            calls.append((text, deepcopy(questions)))
            return deepcopy(response)
    return AgentRegistry(loader=lambda *args, **kwargs: Fake())


def legacy_shape(result):
    return {**result.data, 'decisions': result.decisions}


def test_A01_A02_ticket_exact_payload_and_mixed_decision_parity():
    questions = {k: REQUEST['questions'][k] for k in ('department', 'churn_risk')}
    first = {'answers': {k: deepcopy(RAW['answers'][k]) for k in questions}}
    second = deepcopy(first)
    second['answers']['department']['answer_confidence'] = 0.1
    second['answers']['churn_risk'].update(noul=0.8, answer_confidence=0.8)
    for raw in (first, second):
        calls = []
        result = ticket({'text': REQUEST['text']}, config=RunConfig(), registry=registry(raw, calls, questions))
        expected = old_ticket(REQUEST['text'], config=RunConfig(), registry=registry(raw, [], questions))
        assert result.status == 'completed' and result.reason is None
        assert result.decisions == expected and result.data == {}
        assert len(calls) == 1


@pytest.mark.parametrize('selected,multiple,confidence,reason', [
    ('sum@1:1', 0.1, 0.95, None), ('sum@1:1', 0.1, 0.1, 'method_undecided'),
    ('none_or_unclear', 0.1, 0.95, 'no_single_match'),
    ('sum@1:1', 0.5, 0.95, 'multiple_undecided'),
    ('sum@1:1', 0.9, 0.95, 'multiple_relevant')])
def test_A03_A05_A08_G09_method_exact_legacy_parity(selected, multiple, confidence, reason):
    data = source(); before = deepcopy(data); questions = questions_for(data)
    raw = raw_for(questions, selected, multiple, confidence)
    if reason == 'multiple_undecided':
        raw['answers']['multiple_relevant']['answer_confidence'] = 0.1
    calls = []
    result = method({'text': 'Explain sum', 'source_outline': data}, config=RunConfig(),
                    registry=registry(raw, calls, questions))
    expected = old_method('Explain sum', data, config=RunConfig(), registry=registry(raw, [], questions))
    assert legacy_shape(result) == expected
    assert result.status == 'completed' and result.data['reason'] == reason
    assert len(calls) == 1 and data == before
    result.data['candidate_map'].clear()
    assert data == before


@pytest.mark.parametrize('kind,reason', [('empty', 'no_candidates'), ('budget', 'candidate_budget_exceeded'),
                                        ('ambiguous', 'ambiguous_candidates')])
def test_A06_D09_skips_zero_model_calls(kind, reason):
    data = source(); kwargs = {}
    if kind == 'empty': data['callables'] = []
    if kind == 'budget': kwargs['max_candidates'] = 1
    if kind == 'ambiguous': data['callables'][1]['signature'] = data['callables'][0]['signature']
    calls = []
    result = method({'text': 'x', 'source_outline': data}, config=RunConfig(), registry=registry({}, calls), **kwargs)
    assert result.status == 'skipped' and result.reason == reason and result.decisions == {}
    assert legacy_shape(result) == old_method('x', data, config=RunConfig(), registry=registry({}, []), **kwargs)
    assert calls == []


@pytest.mark.parametrize('bad', [None, [], {}, {'text': 4}])
def test_D01_ticket_invalid_input_early(bad):
    calls = []
    with pytest.raises(ValueError): ticket(bad, config=RunConfig(), registry=registry({}, calls))
    assert calls == []


@pytest.mark.parametrize('change', ['no_id', 'duplicate', 'shape'])
def test_D02_method_full_outline_contract(change):
    data = source()
    if change == 'no_id': del data['callables'][0]['id']
    if change == 'duplicate': data['callables'][1] = deepcopy(data['callables'][0])
    if change == 'shape': del data['schema_version']
    with pytest.raises(ValueError):
        method({'text': 'x', 'source_outline': data}, config=RunConfig(), registry=registry({}, []))


def test_A09_D15_unicode_exact_character_budget():
    data = source(); questions = questions_for(data); text = 'é😀'
    budget = len(text) + len(json.dumps(questions, ensure_ascii=False, separators=(',', ':')))
    raw = raw_for(questions, 'sum@1:1')
    for limit in (budget, budget - 1):
        calls = []
        result = method({'text': text, 'source_outline': data}, config=RunConfig(),
                        registry=registry(raw, calls), max_input_chars=limit)
        assert result.status == ('completed' if limit == budget else 'skipped')
        assert len(calls) == (1 if limit == budget else 0)


def test_D04_D05_D10_custom_preparation_copies_and_mapping_guard():
    from laya_context_router.block_runtime import PreparedInput
    from laya_context_router.building_blocks.questions.method_selection_v2.block import prepare
    data = source(); before = deepcopy(data); calls = []; prepared_calls = []
    def custom(value, questions):
        prepared_calls.append(deepcopy(value))
        result = prepare(value, questions)
        result.questions['method']['instructions'] = 'Choose the requested callable.'
        return PreparedInput('changed', result.questions, result.state)
    result = method({'text': 'original', 'source_outline': data}, config=RunConfig(),
                    registry=registry(raw_for(questions_for(data), 'sum@1:1'), calls), prepare_input=custom)
    assert len(prepared_calls) == 1 and calls[0][0] == 'changed'
    assert calls[0][1]['method']['instructions'] == 'Choose the requested callable.'
    assert data == before and result.data['selected_id'] == data['callables'][0]['id']
    prepared_calls.clear()
    with pytest.raises(ValueError):
        method({'text': 4, 'source_outline': data}, config=RunConfig(), registry=registry({}, []), prepare_input=custom)
    assert prepared_calls == []
    def bad_mapping(value, questions):
        result = prepare(value, questions)
        result.state['label_map']['sum@1:1'] = 'fabricated-id'
        return result
    with pytest.raises(ValueError):
        method({'text': 'x', 'source_outline': data}, config=RunConfig(), registry=registry({}, []), prepare_input=bad_mapping)


@pytest.mark.parametrize('text', ['', '   ', 'é😀'])
def test_D14_ticket_preserves_blank_and_unicode_text(text):
    calls = []
    raw = {'answers': {k: deepcopy(RAW['answers'][k]) for k in ('department', 'churn_risk')}}
    ticket({'text': text}, config=RunConfig(), registry=registry(raw, calls))
    assert calls[0][0] == text


def test_G04_G05_G06_real_outline_selection_extraction(tmp_path):
    from laya_context_router.building_blocks.typescript import outline, extract_callable
    path = tmp_path / 'methods.ts'
    code = 'function alpha() { return 1; }\nclass Beta { static sum(x: number) { return x + 1; } }'
    path.write_text(code)
    data = outline(path)
    chosen = next(c for c in data['callables'] if c['name'].endswith('sum'))
    questions = questions_for(data)
    label = next(k for k, v in questions['method']['criteria'].items() if v == chosen['signature'])
    events = ['outline']
    for multiple, confidence in [(0.1, 0.95), (0.9, 0.95), (0.1, 0.1), (0.5, 0.95)]:
        response = raw_for(questions, label, multiple, confidence)
        if multiple == 0.5:
            response['answers']['multiple_relevant']['answer_confidence'] = 0.1
        result = method({'text': 'Explain sum', 'source_outline': data}, config=RunConfig(),
                        registry=registry(response, [], questions))
        events.append('selection')
        if result.status == 'completed' and result.data['selected_id'] is not None:
            extracted = extract_callable(path, result.data['selected_id'])
            events.append('extract')
            assert extracted['code'] == 'static sum(x: number) { return x + 1; }'
            assert extracted['source_hash'] == data['source_hash']
            assert extracted['callable']['id'] == chosen['id']
    assert events == ['outline', 'selection', 'extract', 'selection', 'selection', 'selection']


@pytest.mark.parametrize('limit', [True, -1, 1.2, '2'])
def test_D15_invalid_candidate_limits(limit):
    with pytest.raises(ValueError):
        method({'text': 'x', 'source_outline': source()}, config=RunConfig(), registry=registry({}, []), max_candidates=limit)


def test_G10_G14_compatibility_adapter_routes_full_outline_through_v2(monkeypatch):
    from laya_context_router.building_blocks.questions.method_selection import block as adapter
    from laya_context_router.building_blocks.questions.method_selection_v2 import block as implementation
    from laya_context_router.block_runtime import BlockResult
    seen = []
    def fake(value, **kwargs):
        seen.append(value)
        return BlockResult('completed', None, {'marker': {}},
                           {'selected_id': None, 'reason': 'test', 'candidate_map': {}, 'label_map': {}})
    monkeypatch.setattr(implementation, 'run', fake)
    result = adapter.run('x', source(), config=RunConfig(), registry=registry({}, []))
    assert result == {'selected_id': None, 'reason': 'test', 'decisions': {'marker': {}},
                      'candidate_map': {}, 'label_map': {}}
    assert seen == [{'text': 'x', 'source_outline': source()}]


def test_G09_G14_abbreviated_legacy_outline_retains_explicit_old_entrypoint():
    from test_block_legacy_characterization import SOURCE, response, fake_registry
    from laya_context_router.building_blocks.questions.method_selection import block as adapter
    expected = adapter.run_legacy('Explain alpha', SOURCE, config=RunConfig(), registry=fake_registry(response(), []))
    actual = adapter.run('Explain alpha', SOURCE, config=RunConfig(), registry=fake_registry(response(), []))
    assert actual == expected


@pytest.mark.parametrize('version', [0, 2, '1', None, True])
def test_D02_G10_versioned_malformed_outline_never_downgrades(version):
    from laya_context_router.building_blocks.questions.method_selection import block as adapter
    data = source(); data['schema_version'] = version; calls = []
    with pytest.raises(ValueError):
        adapter.run('x', data, config=RunConfig(), registry=registry({}, calls))
    assert calls == []


def test_D04_D15_custom_preparation_cannot_bypass_character_budget():
    from laya_context_router.block_runtime import PreparedInput
    from laya_context_router.building_blocks.questions.method_selection_v2.block import prepare
    calls = []
    def custom(value, questions):
        result = prepare(value, questions)
        return PreparedInput('x' * 20000, result.questions, result.state)
    result = method({'text': 'x', 'source_outline': source()}, config=RunConfig(),
                    registry=registry({}, calls), prepare_input=custom)
    assert result.status == 'skipped' and result.reason == 'input_budget_exceeded'
    assert result.decisions == {} and calls == []


def test_D11_sdk_question_mutation_does_not_leak_to_next_run():
    data = source(); expected = questions_for(data); before = deepcopy(data); calls = []
    class Mutating:
        def predict(self, text, questions, **kwargs):
            assert questions == expected
            calls.append(deepcopy(questions))
            response = raw_for(questions, 'sum@1:1')
            questions['method']['criteria'].clear()
            return response
    shared = AgentRegistry(loader=lambda *args, **kwargs: Mutating())
    for _ in range(2):
        result = method({'text': 'x', 'source_outline': data}, config=RunConfig(), registry=shared)
        assert result.data['selected_id'] == data['callables'][0]['id']
    assert calls == [expected, expected] and data == before
