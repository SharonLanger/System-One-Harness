from types import SimpleNamespace
import pytest
from laya import budget_profiles as api
from laya.config import RunConfig
from laya.budget import InspectionUnavailable
from test_token_budget_profiles import observation


def local_observation(path):
    raw=str(path); resolved=str(path.resolve(strict=True));obs=observation()
    obs.update(model_id=raw,model_dir=raw,local_identity={'raw_model_id':raw,'raw_model_dir':raw,'resolved_model_id':resolved,'resolved_model_dir':resolved})
    return obs


def test_bound_local_model_identity_is_accepted(tmp_path):
    obs=local_observation(tmp_path)
    assert api.verify_observation(RunConfig().model,obs) is api.TYPED


@pytest.mark.parametrize('field,value',[
 ('max_len',8192),('head_max_len',512),('hooks_present',True),
 ('tokenizer_available',False),('local_identity',None),
])
def test_local_path_keeps_all_refusals(tmp_path,field,value):
    obs=local_observation(tmp_path);obs[field]=value
    with pytest.raises(InspectionUnavailable):api.verify_observation(RunConfig().model,obs)


def test_observation_binds_actual_paths_and_preserves_fields(tmp_path,monkeypatch):
    assert hasattr(api,'observe_identity'), 'missing path-binding observation'
    folder=tmp_path/'checkpoint';folder.mkdir();link=tmp_path/'link';link.symlink_to(folder,target_is_directory=True)
    monkeypatch.chdir(tmp_path)
    for raw in (str(folder),'checkpoint',str(link)):
        agent=SimpleNamespace(model_id=raw,model_dir=folder)
        obs=api.observe_identity(agent)
        assert agent.model_id==raw and agent.model_dir==folder
        assert obs['model_id']==raw
        assert obs['local_identity']['resolved_model_id']==obs['local_identity']['resolved_model_dir']==str(folder)
        full=observation();full.update(obs)
        assert api.verify_observation(RunConfig().model,full) is api.TYPED


@pytest.mark.parametrize('kind',['missing','file','different','canonical'])
def test_unbound_identity_cannot_borrow_requested_configuration(tmp_path,kind):
    assert hasattr(api,'observe_identity'), 'missing path-binding observation'
    folder=tmp_path/'checkpoint';folder.mkdir()
    raw=tmp_path/kind
    if kind=='file':raw.write_text('x')
    if kind=='different':raw.mkdir()
    if kind=='canonical':raw=RunConfig().model
    obs=observation();obs.update(api.observe_identity(SimpleNamespace(model_id=str(raw),model_dir=folder)))
    assert obs['local_identity'] is None
    if kind=='canonical':assert api.verify_observation(RunConfig().model,obs) is api.TYPED
    else:
        with pytest.raises(InspectionUnavailable):api.verify_observation(RunConfig().model,obs)


def test_raw_observed_identity_in_report(tmp_path,monkeypatch):
    from token_budget_support import tokenizer,mock_runtime
    from token_budget_support import BASE
    obs=local_observation(tmp_path);common=mock_runtime()
    agent=SimpleNamespace(tok=tokenizer(),cfg={'max_len':1024,'head_max_len':256},hooks=[],model_id=str(tmp_path))
    monkeypatch.setattr(api,'_observe_agent',lambda *a:(obs,common,SimpleNamespace(compose_hooks=lambda x:list(x))))
    result=api.verified_provider(agent,RunConfig()).inspect('hello',{'q':BASE})
    assert result['model']['requested_id']==RunConfig().model
    assert result['model']['observed_id']==str(tmp_path)
    assert agent.model_id==str(tmp_path)
