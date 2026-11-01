"""G composition: ordinary Python owns branches; only the SDK boundary is fake."""
from copy import deepcopy
import importlib
import json

import pytest

from block_runtime import Block, Catalog, PreparedInput
from building_blocks.questions.method_selection_v2.block import run as select
from building_blocks.typescript import outline, extract_callable
from flows import first_method_context as flow
from laya.config import RunConfig
from laya.registry import AgentRegistry
from test_method_selection import questions_for, raw_for

A = RunConfig("mock-A", 0.2, "fr")
B = RunConfig("mock-B", 0.7, "en")


def fixture_blocks(tmp_path):
    (tmp_path / 'rules').mkdir()
    (tmp_path / 'questions').mkdir()
    for name, threshold in [('normal', .5), ('strict', .9)]:
        (tmp_path / 'rules' / f'{name}.json').write_text(json.dumps({
            'name': name, 'question_type': 'noul',
            'conditions': [{'field': 'answer_confidence', 'op': 'gte', 'value': threshold}]}))
    catalog = Catalog(tmp_path)
    def make(name):
        return Block({'name': name, 'questions': {name: {'definition': {
            'type': 'noul', 'instructions': f'Answer {name}.'}, 'rule_ref': 'normal'}}},
            catalog=catalog, validate_input=lambda value: value,
            prepare_input=lambda value, questions: PreparedInput(value['text'], questions),
            reduce=lambda decisions, state: {}, validate_output=lambda value: value)
    return make('first'), make('second')


def fixture_registry(events, confidence=.8, value=.8):
    def loader(model, **options):
        events.append(('load', model, options))
        class Agent:
            def predict(self, text, questions, **kwargs):
                events.append(('predict', model, text, deepcopy(questions), kwargs))
                return {'answers': {name: {'type': 'noul', 'noul': value,
                    'answer_confidence': confidence} for name in questions}}
        return Agent()
    return AgentRegistry(loader=loader)


def test_G01_independent_blocks_keep_names_config_and_named_policy(tmp_path):
    first, second = fixture_blocks(tmp_path); events = []; registry = fixture_registry(events)
    one = first.run({'text': 'one'}, config=A, registry=registry)
    two = second.run({'text': 'two'}, config=B, registry=registry, rule_overrides={'second': 'strict'})
    assert set(one.decisions) == {'first'} and set(two.decisions) == {'second'}
    assert one.decisions['first']['answer'] == 'yes'
    assert not two.decisions['second']['decided']
    assert events[0] == ('load', A.model, A.load_kwargs())
    assert events[2] == ('load', B.model, B.load_kwargs())
    assert [(e[1], e[2], e[4]) for e in events if e[0] == 'predict'] == [
        (A.model, 'one', A.predict_kwargs()), (B.model, 'two', B.predict_kwargs())]


@pytest.mark.parametrize('value,confidence,branch,count', [(.8,.8,'continue',2),(.2,.8,'negative',1),(.8,.1,'undecided',1)])
def test_G02_G03_G04_explicit_branch_and_utility_order(tmp_path, value, confidence, branch, count):
    first, second = fixture_blocks(tmp_path); events = []
    registry = fixture_registry(events, confidence, value)
    result = first.run({'text': 'input'}, config=A, registry=registry)
    decision = result.decisions['first']
    if not decision['decided']:
        actual = 'undecided'
    elif decision['answer'] == 'no':
        actual = 'negative'
    else:
        actual = 'continue'
        def utility(text):
            events.append(('utility', text))
            return text.upper()
        final = second.run({'text': utility('input')}, config=A, registry=registry)
        assert final.decisions['second']['answer'] == 'yes'
    assert actual == branch
    assert len([e for e in events if e[0] == 'predict']) == count
    assert [e[0] for e in events] == (['load','predict','utility','predict'] if count == 2 else ['load','predict'])
    if count == 2: assert events[-1][2] == 'INPUT'


@pytest.mark.parametrize('multiple,confidence,multiple_confidence,extracts', [
    (.1,.95,.95,True),(.9,.95,.95,False),(.1,.1,.95,False),(.1,.95,.1,False)])
def test_G05_G06_real_typescript_v2_select_then_extract(tmp_path, multiple, confidence, multiple_confidence, extracts):
    path = tmp_path / 'actual.ts'
    path.write_text('function alpha() { return 1; }\nclass Beta { static sum(x: number) { return x + 1; } }')
    events = ['outline']; data = outline(path); questions = questions_for(data)
    chosen = next(c for c in data['callables'] if c['name'].endswith('sum'))
    label = next(k for k,v in questions['method']['criteria'].items() if v == chosen['signature'])
    response = raw_for(questions, label, multiple, confidence)
    response['answers']['multiple_relevant']['answer_confidence'] = multiple_confidence
    class Agent:
        def predict(self, text, submitted, **kwargs):
            events.append('predict'); assert text == 'Explain sum' and submitted == questions
            return deepcopy(response)
    result = select({'text':'Explain sum', 'source_outline':data}, config=A,
                    registry=AgentRegistry(loader=lambda *a, **k: Agent()))
    if result.data['selected_id'] is not None:
        events.append('extract'); extracted = extract_callable(path, result.data['selected_id'])
        assert extracted['code'] == 'static sum(x: number) { return x + 1; }'
        assert extracted['source_hash'] == data['source_hash']
        assert extracted['callable'] == chosen and extracted['path'] == str(path)
    assert events == (['outline','predict','extract'] if extracts else ['outline','predict'])








def test_G12_imports_do_not_load_agents_or_run_flows(monkeypatch):
    def forbidden(*args, **kwargs): raise AssertionError('import triggered model or flow')
    monkeypatch.setattr(AgentRegistry,'get_agent',forbidden)
    monkeypatch.setattr(flow,'run',forbidden)
    for module in ('block_runtime.catalog',
                   'building_blocks.questions.ticket_triage_v2.block',
                   'building_blocks.questions.method_selection_v2.block'):
        importlib.reload(importlib.import_module(module))


@pytest.mark.parametrize('invalid_rule', [False, True])
def test_G13_existing_offline_experiment_preserves_summary_and_rule_error(tmp_path, monkeypatch, invalid_rule):
    from pathlib import Path
    from test_v2_blocks import source
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'experiments'))
    experiment = importlib.import_module('block_method_selection')
    data = source(); questions = questions_for(data)
    payload = tmp_path / 'input.json'
    payload.write_text(json.dumps({'text':'Explain sum','source_outline':data,'config':{'model':A.model}}))
    class Agent:
        def predict(self, text, submitted, **kwargs):
            assert text == 'Explain sum' and submitted == questions
            return raw_for(questions, 'sum@1:1')
    loads = []
    def loader(*args, **kwargs):
        loads.append(args)
        return Agent()
    if invalid_rule:
        # The legacy experiment has no CLI rule flag. Inject the new public call
        # at its existing block boundary to exercise its unchanged error report.
        def invalid(text, source_outline, **kwargs):
            return select({'text':text,'source_outline':source_outline},
                          rule_overrides={'method':'missing_policy'}, **kwargs)
        monkeypatch.setattr(experiment,'run_block',invalid)
    output = tmp_path / 'reports'
    code = experiment.run(input_path=payload,loader=loader,output_root=output,printer=lambda _:None)
    details_path, = output.rglob('details.json')
    details = json.loads(details_path.read_text())
    summary = (details_path.parent / 'summary.md').read_text()
    assert code == int(invalid_rule)
    if invalid_rule:
        assert details['run']['status'] == 'failed' and details['error']['stage'] == 'block'
        assert 'missing_policy' in details['error']['message'] and 'missing_policy' in summary
        assert not loads and details['result'] is None
    else:
        assert details['run']['status'] == 'success' and details['error'] is None
        assert details['result']['selected_id'] == data['callables'][0]['id']
        assert details['result']['decisions']['method']['answer'] == 'sum@1:1'
        assert 'Outcome: **selected**' in summary and 'Selected candidate: **sum**' in summary
        assert data['source_hash'] in summary and len(loads) == 1
