"""Legacy wrappers/replay stay usable; strict enforcement is explicitly selected."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from laya_context_router.laya import predict as api
from laya_context_router.laya.budget import InspectionUnavailable
from test_predict import REQUEST,RAW
from examples._plumbing_inspection import plumbing_provider

@pytest.mark.parametrize('kind',['direct','closure_wrapper'])
def test_legacy_predict_needs_no_inspection(kind):
    calls=[]
    class Agent:
        def predict(self,*args,**kwargs):calls.append((args,kwargs));return deepcopy(RAW)
    agent=Agent()
    class Observed:
        def get_agent(self,config):
            class Wrapper:
                def predict(self,*args,**kwargs):return agent.predict(*args,**kwargs)
            return Wrapper()
    registry=Observed() if kind=='closure_wrapper' else SimpleNamespace(get_agent=lambda c:agent)
    assert api.predict(REQUEST['text'],REQUEST['questions'],registry=registry)==RAW
    assert len(calls)==1


def test_strict_entry_point_refuses_opaque_wrapper():
    assert hasattr(api,'predict_strict'), 'missing explicit strict API'
    registry=SimpleNamespace(get_agent=lambda c:SimpleNamespace(predict=lambda *a,**k:pytest.fail('predicted')))
    with pytest.raises(InspectionUnavailable):api.predict_strict('hello',REQUEST['questions'],registry=registry)


def test_both_paths_share_success_contract():
    assert hasattr(api,'predict_strict'), 'missing explicit strict API'
    calls=[]
    def loader(*a):return SimpleNamespace(predict=lambda *a,**k:(calls.append(1),deepcopy(RAW))[1])
    for fn in (api.predict,api.predict_strict):
        assert fn('hello',REQUEST['questions'],loader=loader,inspection_provider=plumbing_provider)==RAW
    assert calls==[1,1]

@pytest.mark.parametrize('module_name,input_data',[
 ('ticket_triage', 'ticket'),('ticket_triage_v2',{'text':'ticket'}),('requested_action',{'prompt':'Explain it'}),('context_scope',{'prompt':'Explain it'})])
def test_public_blocks_explicitly_select_strict(module_name,input_data):
    import importlib
    module=importlib.import_module('laya_context_router.building_blocks.questions.'+module_name+'.block')
    registry=SimpleNamespace(get_agent=lambda c:SimpleNamespace(predict=lambda *a,**k:pytest.fail('predicted')))
    from laya_context_router.laya.config import RunConfig
    with pytest.raises(InspectionUnavailable):module.run(input_data,config=RunConfig(),registry=registry,strict=True)


def test_legacy_method_adapter_forwards_strict():
    from test_block_legacy_characterization import SOURCE
    from laya_context_router.building_blocks.questions.method_selection.block import run
    from laya_context_router.laya.config import RunConfig
    registry=SimpleNamespace(get_agent=lambda c:SimpleNamespace(predict=lambda *a,**k:pytest.fail('predicted')))
    with pytest.raises(InspectionUnavailable):run('Explain alpha',SOURCE,config=RunConfig(),registry=registry,strict=True)


def test_saved_response_replay_needs_no_loader_or_tokenizer(monkeypatch):
    stored=deepcopy(RAW); events=[]
    class RecordedAgent:
        def __init__(self,raw):self.raw=raw
        def predict(self,*args,**kwargs):return deepcopy(self.raw)
    class Boundary:
        def __init__(self,agent):self.agent=agent
        def get_agent(self,config):return self.agent
    monkeypatch.setattr(api,'log',lambda level,component,event,**kw:events.append(event))
    result=api.predict(REQUEST['text'],REQUEST['questions'],registry=Boundary(RecordedAgent(stored)))
    assert result==stored
    result['answers'].clear()
    assert stored==RAW and 'input_budget_rejected' not in events


def test_v2_method_adapter_forwards_strict():
    from test_v2_blocks import source
    from laya_context_router.building_blocks.questions.method_selection_v2.block import run
    from laya_context_router.laya.config import RunConfig
    registry=SimpleNamespace(get_agent=lambda c:SimpleNamespace(predict=lambda *a,**k:pytest.fail('predicted')))
    with pytest.raises(InspectionUnavailable):run({'text':'Explain sum','source_outline':source()},config=RunConfig(),registry=registry,strict=True)
