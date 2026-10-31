"""C01–C24: actual scope block pipeline with only the SDK boundary faked."""
from examples._plumbing_inspection import plumbing_provider
from copy import deepcopy
import json
from pathlib import Path
import pytest

from laya_context_router.building_blocks.questions.context_scope import block
from laya_context_router.block_runtime import BlockInputError, BlockExecutionError
from laya_context_router.laya.config import RunConfig
from laya_context_router.laya.registry import AgentRegistry
from laya_context_router.laya.predict import ResponseError

LABELS = ('method_only', 'called_methods', 'calling_methods', 'both_directions')

def response(label='method_only', probs=None):
    fixture=json.loads((Path(__file__).parent/'fixtures/context_scope_responses.json').read_text())
    raw=deepcopy(fixture['responses'][label])
    if probs is not None:
        raw['answers']['context_scope']['probabilities']=probs
        raw['answers']['context_scope']['answer_confidence']=probs[label]
    return raw


def registry(raw=None, calls=None, loads=None, error=None):
    raw = response() if raw is None else raw
    calls = [] if calls is None else calls
    loads = [] if loads is None else loads
    class Agent:
        def predict(self, text, questions, **kwargs):
            calls.append((text, deepcopy(questions), kwargs))
            if error: raise error
            return deepcopy(raw)
    def loader(*args, **kwargs):
        loads.append((args, kwargs))
        return Agent()
    return AgentRegistry(inspection_provider=plumbing_provider, loader=loader)

_DEFAULT = object()

def run(value=_DEFAULT, raw=None, calls=None, loads=None, **kwargs):
    return block.run({'prompt': 'Explain this method.'} if value is _DEFAULT else value,
                     config=RunConfig(model='mock'), registry=registry(raw, calls, loads), **kwargs)

@pytest.mark.parametrize('label', LABELS)
def test_C01_C12_labels(label):
    result=run(raw=response(label))
    assert result.status=='completed' and result.reason is None
    assert result.data=={'scope':label}
    assert result.decisions=={'context_scope':{'answer':label,'decided':True,'reason':None}}

@pytest.mark.parametrize('action', [None,'undecided','explain','generate_tests','modify_code'])
def test_C02_C03_C04_C05_payload(action):
    prompt='  Explain "שלום" {x}\n in src/a.ts 😀  '
    calls=[]; data={'prompt':prompt}
    if action is not None: data['requested_action']=action
    run(data,calls=calls)
    text,questions,_=calls[0]
    if action in (None,'undecided'): assert text==prompt
    else:
        assert json.loads(text)==data
        assert 'שלום' in text
    assert set(questions)=={'context_scope'}
    assert set(questions['context_scope']['criteria'])==set(LABELS)
    calls=[];run({'prompt':prompt,'requested_action':None},calls=calls)
    assert calls[0][0]==prompt

@pytest.mark.parametrize('value', [None,[],{}, {'prompt':None},{'prompt':1},{'prompt':True},
    {'prompt':''},{'prompt':' \n\t'}, {'prompt':'x','code':'ignored'},
    *({'prompt':'x','requested_action':v} for v in [0,True,[],{},'EXPLAIN','other'])])
def test_C06_C07_invalid_input(value):
    loads=[];calls=[]
    with pytest.raises(BlockInputError):run(value,calls=calls,loads=loads)
    assert loads==calls==[]

def test_C08_C10_no_mutation_long_transport():
    value={'prompt':'x'*20000+' שלום','requested_action':'explain'};raw=response()
    before=deepcopy((value,raw));calls=[]
    run(value,raw,calls)
    assert (value,raw)==before and json.loads(calls[0][0])==value

def test_C11_predict_and_enrich_once(monkeypatch):
    import laya_context_router.block_runtime.runtime as runtime
    original=runtime.enrich_prediction;seen=[];calls=[]
    def traced(value):seen.append(deepcopy(value));return original(value)
    monkeypatch.setattr(runtime,'enrich_prediction',traced)
    run(calls=calls)
    assert len(calls)==len(seen)==1

@pytest.mark.parametrize('probs,expected,reason',[
    ((.8,.1,.06,.04),'method_only',None),
    ((.49,.25,.16,.10),'undecided','below_threshold:answer_confidence'),
    ((.55,.45,0,0),'undecided','below_threshold:probability_gap'),
    ((.50,.35,.10,.05),'method_only',None),
    ((.499,.300,.151,.050),'undecided','below_threshold:answer_confidence'),
    ((.500,.351,.099,.050),'undecided','below_threshold:probability_gap'),
    ((.5,.5,0,0),'undecided','below_threshold:probability_gap')])
def test_C12_C18_rule_boundaries(probs,expected,reason):
    result=run(raw=response(probs=dict(zip(LABELS,probs))))
    assert result.status=='completed' and result.reason is None
    assert result.data=={'scope':expected}
    assert result.decisions['context_scope']=={'answer':expected,'decided':reason is None,'reason':reason}

@pytest.mark.parametrize('confidence,act',[(0,0),(1,1)])
def test_C20_ungated_fields(confidence,act):
    raw=response();raw['answers']['context_scope'].update(confidence=confidence,action={'act_probability':act})
    assert run(raw=raw).data=={'scope':'method_only'}

def test_C21_missing_metric():
    raw=response();del raw['answers']['context_scope']['answer_confidence']
    result=run(raw=raw)
    assert result.data=={'scope':'undecided'}
    assert result.decisions['context_scope']['reason']=='field_missing:answer_confidence'

@pytest.mark.parametrize('kind',['missing','type','choice','keys','sum','nan','infinity'])
def test_C22_invalid_response(kind):
    raw=response();answer=raw['answers']['context_scope']
    if kind=='missing':raw['answers'].clear()
    if kind=='type':answer['type']='noul'
    if kind=='choice':answer['choice']='other'
    if kind=='keys':answer['probabilities']['other']=answer['probabilities'].pop('method_only')
    if kind=='sum':answer['probabilities']['method_only']=.1
    if kind=='nan':answer['confidence']=float('nan')
    if kind=='infinity':answer['confidence']=float('inf')
    with pytest.raises(ResponseError):run(raw=raw)

@pytest.mark.parametrize('error',[RuntimeError('sdk'),TimeoutError('deadline')])
def test_C23_prediction_errors_once(error):
    calls=[];loads=[]
    with pytest.raises(type(error),match=str(error)):
        block.run({'prompt':'x'},config=RunConfig(),registry=registry(calls=calls,loads=loads,error=error))
    assert len(calls)==len(loads)==1

@pytest.mark.parametrize('value',[{},[],{'scope':'unknown'},{'scope':'method_only','extra':True}])
def test_C24_output_validator(value):
    with pytest.raises(ValueError):block.validate_output(value)

def test_C24_invalid_reducer_output_becomes_execution_error(monkeypatch):
    monkeypatch.setattr(block,'validate_output',lambda value: (_ for _ in ()).throw(ValueError('bad output')))
    with pytest.raises(BlockExecutionError):run()


def test_semantic_corpus_is_labeled_without_claiming_model_accuracy():
    corpus=json.loads((Path(__file__).parent/'fixtures/context_scope_prompts.json').read_text())
    assert {case['id'] for case in corpus['cases']}=={f'S{i:02}' for i in range(1,23)}
    for case in corpus['cases']:
        assert case['prompt'].strip()
        assert case['expected_scope'] in (*LABELS,None)
        assert case['status'] in {'settled','provisional','taxonomy_pending','prompt_insufficient','out_of_scope'}
        if case['status'] in {'taxonomy_pending','prompt_insufficient','out_of_scope'}:
            assert case['expected_scope'] is None
        if case['status']=='provisional':assert case['note']
    assert {case['split'] for case in corpus['cases']}=={'held_out','development'}
