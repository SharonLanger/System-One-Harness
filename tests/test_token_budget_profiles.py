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
    return {'model_id':p.model_id,'revision':p.revision,
            'runtime_version':p.runtime_version,'tokenizer_version':p.tokenizer_version,
            'source_hashes':dict(m.SOURCE_HASHES),'tokenizer_sha256':p.tokenizer_sha256,
            'config_sha256':p.config_sha256,'checkpoint_config_sha256':p.checkpoint_config_sha256,
            'max_len':1024,'head_max_len':256,'hooks_present':False,'backend_matches_files':True}



def test_verified_identity_is_immutable_and_model_specific():
    m=api();p=m.verify_observation(RunConfig().model,observation())
    assert (p.max_len,p.head_max_len)==(1024,256)
    with pytest.raises(FrozenInstanceError):p.max_len=8192
    assert m.CODE.max_len==512 and m.CODE.status=='candidate'
    with pytest.raises(InspectionUnavailable,match='candidate'):
        m.verify_observation(m.CODE.model_id,observation())


@pytest.mark.parametrize('field,value',[
 ('model_id','other'),('revision','main'),('runtime_version','0.6.1'),('source_hashes',{}),
 ('tokenizer_sha256','bad'),('config_sha256','bad'),('checkpoint_config_sha256','bad'),
 ('max_len',8192),('head_max_len',512),('hooks_present',True),('backend_matches_files',False),
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
