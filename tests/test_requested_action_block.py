"""Synthetic SDK outputs test transport/policy, never semantic model accuracy."""
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import Mock
import pytest
from block_runtime import Catalog, BlockInputError
from laya.config import RunConfig
from laya.registry import AgentRegistry

LABELS = ('explain', 'generate_tests', 'modify_code')
FIXTURES = Path(__file__).parent / 'fixtures'


def response(label='explain', probs=(.8,.15,.05), confidence=.8):
    labels = (label,) + tuple(x for x in (*LABELS, 'unclear') if x != label)
    if len(probs) == 3:
        probs = (*probs, 0)
    return {'answers': {'requested_action': {'type':'choice','choice':label,
        'probabilities':dict(zip(labels,probs)), 'answer_confidence':confidence}}}


class Harness:
    def __init__(self, raw=None):
        self.raw = response() if raw is None else raw
        self.calls=[]; self.loads=[]
        self.registry=AgentRegistry(loader=self.load)
    def load(self,model,**kwargs):
        self.loads.append((model,kwargs)); return self
    def predict(self,text,questions,**kwargs):
        self.calls.append((text,deepcopy(questions),kwargs))
        if isinstance(self.raw,Exception): raise self.raw
        return self.raw
    def run(self, value=None, **kwargs):
        from building_blocks.questions.requested_action.block import run
        return run({'prompt':'Explain total'} if value is None else value,
            config=kwargs.pop('config',RunConfig(model='synthetic')),registry=self.registry,**kwargs)


@pytest.mark.parametrize('label',LABELS)
def test_T01_T07_T10_T13_T43_labels_and_caller(label):
    h=Harness(response(label));r=h.run()
    assert r.status=='completed' and r.reason is None
    assert r.data=={'action':label}
    assert r.decisions=={'requested_action':{'answer':label,'decided':True,'reason':None}}
    assert h.calls[0][1]=={'requested_action':Catalog().question('requested_action')}
    branches={'explain':'read','generate_tests':'tests','modify_code':'edit','undecided':'normal'}
    assert branches[r.data['action']]=={'explain':'read','generate_tests':'tests','modify_code':'edit'}[label]


@pytest.mark.parametrize('text',['Explain total',' \n Explain total\n ', 'הסבר "a/b.ts" \\ code', 'noise '*20000+' Explain total'])
def test_T02_T03_T04_transport_only_no_token_claim(text):
    h=Harness();h.run({'prompt':text});assert h.calls[0][0]==text


@pytest.mark.parametrize('value',[None,42,False,[],{}, {'prompt':None},{'prompt':3},{'prompt':True},{'prompt':[]},{'prompt':''},{'prompt':' \n '},{'prompt':'x','implementation':'code'},{'prompt':'x','code':'x'}])
def test_T03_T05_T06_T42_input_rejected_before_load(value):
    from building_blocks.questions.requested_action.block import run
    h=Harness()
    with pytest.raises(BlockInputError):run(value,config=RunConfig(),registry=h.registry)
    assert not h.calls and not h.loads


@pytest.mark.parametrize('probs,confidence,reason',[
 ((.8,.15,.05),.8,None),((.49,.30,.21),.49,None),
 ((.55,.45,0),.55,None),((.50,.35,.15),.5,None),
 ((.499,.300,.201),.0,None),
 ((.44,.341,.219),.9,'below_threshold:probability_gap'),((.50,.50,0),.5,'below_threshold:probability_gap')])
def test_T14_T20_T43_policy_boundaries(probs,confidence,reason):
    from answers.enrich import enrich_prediction
    from answers.rules import accepts
    raw=response(probs=probs,confidence=confidence);h=Harness(raw);r=h.run()
    accepted,actual=accepts(enrich_prediction(raw['answers']['requested_action']),Catalog().rule('requested_action_default'))
    assert actual==reason and r.reason is None and r.status=='completed'
    assert r.decisions['requested_action']=={'answer':'explain' if accepted else 'undecided','decided':accepted,'reason':actual}
    assert r.data=={'action':'explain' if accepted else 'undecided'}
    assert len(h.calls)==1


def test_T08_T09_T11_T12_T21_T22(monkeypatch):
    from building_blocks.questions.requested_action import block
    import block_runtime.runtime as runtime
    spy=Mock(wraps=runtime.enrich_prediction);monkeypatch.setattr(runtime,'enrich_prediction',spy)
    h=Harness(); value={'prompt':'x'}; before=deepcopy(h.raw); overrides={'requested_action':Catalog().question('requested_action')}; saved=deepcopy(overrides)
    # Catalog construction/import is lazy; no loader has run.
    Catalog(); assert h.loads==[]
    h.raw['answers']['requested_action'].update(confidence=0,action={'act_probability':0},sdk_metadata={'version':'synthetic'})
    before=deepcopy(h.raw)
    r=h.run(value,question_overrides=overrides)
    assert spy.call_count==1 and len(h.calls)==1
    assert value=={'prompt':'x'} and overrides==saved and h.raw==before
    assert spy.call_args.args[0]['sdk_metadata']=={'version':'synthetic'}
    assert r.data=={'action':'explain'}
    del h.raw['answers']['requested_action']['answer_confidence']
    r=h.run();assert r.decisions['requested_action']=={'answer':'explain','decided':True,'reason':None}


def test_T10_invalid_output():
    from building_blocks.questions.requested_action.block import validate_output
    for value in ({'action':'other'}, {}, {'action':'explain','extra':1}, [], {'action':[]}):
        with pytest.raises(ValueError):validate_output(value)


def test_T01_saved_fixtures():
    data=json.loads((FIXTURES/'requested_action_responses.json').read_text())
    assert data['synthetic'] is True
    for label,raw in data['responses'].items():assert Harness(raw).run().data=={'action':label}

