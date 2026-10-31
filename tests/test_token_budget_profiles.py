import importlib.util
import json
from dataclasses import FrozenInstanceError
from types import SimpleNamespace
import pytest
from laya_context_router.laya.budget import InspectionUnavailable
from laya_context_router.laya.config import RunConfig
from token_budget_support import FIXTURES


def api():
    assert importlib.util.find_spec('laya_context_router.laya.budget_profiles') is not None, 'missing verified profile capability'
    from laya_context_router.laya import budget_profiles
    return budget_profiles


def observation():
    manifest=json.loads((FIXTURES/'manifest.json').read_text())
    return {'model_id':manifest['models']['typed']['model'],'revision':manifest['models']['typed']['revision'],
            'runtime_version':'0.6.0','tokenizer_version':'0.23.3','source_hashes':{
                'agent.py':'3ceebd3f4acac3ef87718992f0df140c59120e10db7d213365eb1c956a358ee0',
                'runtime.py':manifest['files']['sdk/runtime.py'], 'common.py':manifest['files']['sdk/common.py'],
                'prepared.py':manifest['files']['sdk/prepared.py'], 'tokenizer.py':manifest['files']['sdk/tokenizer.py'],
                'hooks.py':'699c2212cb6aa8aeada9592295aab2a7109751c3bd1b59a6617670c29e09704d'},
            'tokenizer_sha256':manifest['tokenizer']['sha256'], 'config_sha256':manifest['files']['typed/tokenizer_config.json'],
            'checkpoint_config_sha256':manifest['files']['typed/rl_agent_config.json'],
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
    from token_budget_support import sdk_tokenizer,sdk
    from test_token_budget_parity import BASE
    tok=sdk_tokenizer();common,*_=sdk()
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
