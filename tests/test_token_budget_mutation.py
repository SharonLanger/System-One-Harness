"""D006: sequential mutation invalidates cached verification before any dispatch."""
from types import SimpleNamespace
import importlib
import pytest
from token_budget_support import sdk_tokenizer,sdk
from test_token_budget_profiles import observation
from test_token_budget_parity import BASE
from laya_context_router.laya.budget_profiles import VerifiedInspector,TYPED
from laya_context_router.laya.config import RunConfig
from laya_context_router.laya.budget import InspectionUnavailable

@pytest.fixture
def managed():
    common,*_=sdk();calls=[]
    class Agent:
        def predict(self,*a,**kw):calls.append('predict')
        def predict_batch(self,*a,**kw):calls.append('batch')
        def _encode_state(self,*a,**kw):calls.append('encode')
        def _to_internal(self,*a,**kw):calls.append('normalize')
        def _check_question(self,*a,**kw):pass
    agent=Agent();agent.tok=sdk_tokenizer();agent.cfg={'max_len':1024,'head_max_len':256};agent.hooks=[]
    inspector=VerifiedInspector(agent,RunConfig(),TYPED,observation(),common,SimpleNamespace(compose_hooks=lambda x:x))
    return agent,inspector,calls,common

@pytest.mark.parametrize('mutation',['vocabulary','normalizer','mask_token','mask_token_id','cls_token','cls_token_id','sep_token','sep_token_id','pad_token','pad_token_id'])
def test_cached_tokenizer_mutation_refused_and_lock_released(managed,mutation):
    agent,inspector,_,common=managed
    if mutation=='vocabulary':agent.tok.backend.add_tokens(['brand_new_budget_token'])
    elif mutation=='normalizer':
        from tokenizers.normalizers import Lowercase
        agent.tok.backend.normalizer=Lowercase()
    else:setattr(agent.tok,mutation,99999 if mutation.endswith('_id') else 'changed')
    with pytest.raises(InspectionUnavailable) as caught:inspector.inspect('hello',{'q':BASE})
    assert caught.value.report['questions'] is None
    import threading
    acquired=[]
    def check():
        with common._TOKENIZE_LOCK:acquired.append(True)
    thread=threading.Thread(target=check,daemon=True);thread.start();thread.join(2)
    assert acquired==[True]

@pytest.mark.parametrize('method',['predict','predict_batch','_encode_state','_to_internal','_check_question'])
def test_method_override_never_called_even_before_validation(managed,method,monkeypatch):
    agent,inspector,calls,_=managed;events=[]
    setattr(agent,method,lambda *a,**k:calls.append('replacement'))
    api=importlib.import_module('laya_context_router.laya.predict')
    monkeypatch.setattr(api,'log',lambda level,component,event,**kw:events.append((level,kw)))
    registry=SimpleNamespace(get_agent=lambda c:agent,get_inspector=lambda c:inspector)
    with pytest.raises(InspectionUnavailable) as caught:api.predict('hello',{'q':BASE},registry=registry)
    assert not calls
    errors=[kw for level,kw in events if level=='ERROR']
    assert len(errors)==1 and errors[0]['report']==caught.value.report


def test_unchanged_cached_agent_reused(managed):
    _,inspector,calls,_=managed
    for _ in range(3):
        inspector.validate_request('hello',{'q':BASE})
        assert inspector.inspect('hello',{'q':BASE})['violations']==[]
    assert not calls
