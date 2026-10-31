import importlib.util
import json
from dataclasses import FrozenInstanceError
from types import SimpleNamespace
import pytest
from laya_context_router.laya.budget import InspectionUnavailable
from laya_context_router.laya.config import RunConfig
from token_budget_support import tokenizer,mock_runtime


def api():
    assert importlib.util.find_spec('laya_context_router.laya.budget_profiles') is not None, 'missing verified profile capability'
    from laya_context_router.laya import budget_profiles
    return budget_profiles


def observation():
    # Controlled metadata only: matching these fields does not qualify a real runtime.
    m=api();p=m.TYPED
    return {'model_id':p.model_id,'revision':'observed-revision',
            'max_len':1024,'head_max_len':256,'hooks_present':False,'tokenizer_available':True}



def test_verified_identity_is_immutable_and_model_specific():
    m=api();p=m.verify_observation(RunConfig().model,observation())
    assert (p.max_len,p.head_max_len)==(1024,256)
    with pytest.raises(FrozenInstanceError):p.max_len=8192
    assert m.CODE.max_len==512 and m.CODE.status=='candidate'
    with pytest.raises(InspectionUnavailable,match='candidate'):
        m.verify_observation(m.CODE.model_id,observation())


@pytest.mark.parametrize('field,value',[
 ('model_id','other'),('max_len',8192),('head_max_len',512),
 ('hooks_present',True),('tokenizer_available',False),
])
def test_mismatch_refuses_unknown_counts(field,value):
    m=api();obs=observation();obs[field]=value
    with pytest.raises(InspectionUnavailable) as caught:m.verify_observation(RunConfig().model,obs)
    assert caught.value.report['questions'] is None
    assert caught.value.report['limits'] is None


def test_missing_metadata_unknown_profile_and_opaque_agent():
    m=api()
    for model,obs in [('unknown',observation()),(RunConfig().model,{})]:
        with pytest.raises(InspectionUnavailable):m.verify_observation(model,obs)
    with pytest.raises(InspectionUnavailable):m.verified_provider(SimpleNamespace(predict=lambda *a:None),RunConfig())


def test_verified_adapter_uses_shared_sdk_lock_and_detects_changes(monkeypatch):
    m=api()
    from token_budget_support import tokenizer,mock_runtime
    from token_budget_support import BASE
    tok=tokenizer();common=mock_runtime()
    agent=SimpleNamespace(tok=tok,cfg={'max_len':1024,'head_max_len':256},hooks=[])
    hooks=SimpleNamespace(compose_hooks=lambda installed:list(installed))
    obs=observation()
    # Observation boundary injected to test host adapter plumbing; no claim of a live agent.
    monkeypatch.setattr(m,'_observe_agent',lambda *a:(obs,common,hooks))
    adapter=m.verified_provider(agent,RunConfig())
    calls=[];original=common.encode_text
    monkeypatch.setattr(common,'encode_text',lambda *a,**kw:(calls.append(kw),original(*a,**kw))[1])
    report=adapter.inspect('hello',{'q':BASE},request_id='r')
    assert calls and report['model']['resolved_revision']==obs['revision']
    assert report['request_id']=='r'
    agent.cfg['max_len']=8192
    with pytest.raises(InspectionUnavailable):adapter.inspect('hello',{'q':BASE},request_id='s')
    agent.cfg['max_len']=1024;agent.hooks.append(object())
    with pytest.raises(InspectionUnavailable):adapter.inspect('hello',{'q':BASE},request_id='s')


def test_loaded_tokenizer_uses_reviewed_limits_without_asset_files(tmp_path,monkeypatch):
    import sys,types
    m=api();tok=tokenizer();common=mock_runtime()
    class Agent:
        def _check_question(self,*args):pass
    Agent.__module__='laya_mlx.agent'
    agent=Agent();agent.model_id=m.TYPED.model_id;agent.model_dir=tmp_path;agent.cfg={'max_len':1024,'head_max_len':256};agent.tok=tok;agent.hooks=[]
    package=types.ModuleType('laya_mlx');package.__path__=[]
    module=types.ModuleType('laya_mlx.agent');module.Agent=Agent
    monkeypatch.setitem(sys.modules,'laya_mlx',package)
    monkeypatch.setitem(sys.modules,'laya_mlx.agent',module)
    monkeypatch.setitem(sys.modules,'laya_mlx.common',common)
    monkeypatch.setitem(sys.modules,'laya_mlx.hooks',SimpleNamespace(compose_hooks=lambda x:x))
    from pathlib import Path
    monkeypatch.setattr(Path,'read_bytes',lambda *a:pytest.fail('asset file read'))
    from token_budget_support import BASE
    report=m.verified_provider(agent,RunConfig()).inspect('hello',{'q':BASE})
    assert report['tokenizer']=={'source':'loaded_agent_tokenizer','runtime':'laya-mlx'}
    assert report['limits']['provenance']=='reviewed_model_limits'
    assert report['model']['qualification']=='reviewed_limits_live_unverified'
    assert report['model']['resolved_revision'] is None
