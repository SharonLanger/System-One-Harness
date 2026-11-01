import json
from pathlib import Path
import subprocess
import sys
import textwrap
import pytest
from laya.config import RunConfig, load_config
from laya.registry import AgentRegistry
from laya.predict import predict, DEFAULT_MODEL
from test_predict import Agent, REQUEST, RAW


def test_config_defaults_roundtrip(tmp_path):
    assert RunConfig.from_dict({}) == RunConfig()
    assert RunConfig().to_dict() == {'model': DEFAULT_MODEL}
    cfg = RunConfig('A', 0, 'fr')
    assert cfg.to_dict() == {'model':'A','temperature':0,'lang':'fr'}
    p = tmp_path/'config.json'; p.write_text(json.dumps(cfg.to_dict()))
    assert load_config(p) == cfg


def test_registry_a_b_a_temperature_language_and_kwargs():
    loads=[]
    def loader(model, **kwargs):
        agent=Agent(); loads.append((model,kwargs,agent)); return agent
    registry=AgentRegistry(loader=loader)
    configs=[RunConfig('A'),RunConfig('B'),RunConfig('A'),RunConfig('A',0.2),RunConfig('A',0.7),RunConfig('A',0.2),RunConfig('A',0,'fr'),RunConfig('A',0,'en')]
    agents=[registry.get_agent(c) for c in configs]
    assert agents[0] is agents[2] and agents[3] is agents[5]
    assert len({id(a) for a in agents}) == 6
    assert [(m,k) for m,k,a in loads] == [('A',{}),('B',{}),('A',{'lang_temperatures':{'en':{'temperature':[0.2]*3}}}),('A',{'lang_temperatures':{'en':{'temperature':[0.7]*3}}}),('A',{'lang_temperatures':{'fr':{'temperature':[0]*3}}}),('A',{'lang_temperatures':{'en':{'temperature':[0]*3}}})]
    for config,agent in zip(configs,agents):
        assert predict(REQUEST['text'],REQUEST['questions'],config=config,registry=registry) == RAW
        assert agent.calls[-1] == ((REQUEST['text'],REQUEST['questions']),{} if config.temperature is None else {'lang':config.lang})


def test_registry_failed_load_recovery_and_separate_lifetimes():
    calls=[]
    def loader(model):
        calls.append(model)
        if len(calls)==1: raise RuntimeError('load failed')
        return Agent()
    r=AgentRegistry(loader=loader)
    with pytest.raises(RuntimeError): r.get_agent(RunConfig())
    a=r.get_agent(RunConfig())
    assert r.get_agent(RunConfig()) is a and len(calls)==2
    assert AgentRegistry(loader=loader).get_agent(RunConfig()) is not a


def test_registry_starts_fresh_in_separate_processes():
    script = textwrap.dedent('''
        import json
        import sys

        sys.path.insert(0, sys.argv[1])
        from laya.config import RunConfig
        from laya.registry import AgentRegistry

        class FakeAgent:
            pass

        agent = FakeAgent()
        loads = []

        def loader(model, **kwargs):
            loads.append([model, kwargs])
            return agent

        registry = AgentRegistry(loader=loader)
        config = RunConfig('process-test-model', 0.2, 'fr')
        assert registry._agents == {}
        assert loads == []
        first = registry.get_agent(config)
        assert first is agent
        assert registry.get_agent(config) is first
        assert not any(
            name == 'laya_mlx' or name.startswith('laya_mlx.')
            or name == 'mlx' or name.startswith('mlx.')
            for name in sys.modules
        )
        print(json.dumps(loads))
    ''')
    source = str(Path(__file__).resolve().parents[1] / 'src')
    expected = [['process-test-model', {
        'lang_temperatures': {'fr': {'temperature': [0.2] * 3}}
    }]]
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, '-I', '-c', script, source],
            capture_output=True, text=True, check=True, timeout=30,
        )
        assert json.loads(result.stdout) == expected
        assert result.stderr == ''


def test_config_is_immutable_and_load_kwargs_do_not_leak():
    from dataclasses import FrozenInstanceError
    cfg=RunConfig('A',0.2)
    with pytest.raises(FrozenInstanceError): cfg.temperature=0.7
    first=cfg.load_kwargs(); first['lang_temperatures']['en']['temperature'][0]=7
    assert cfg.load_kwargs()['lang_temperatures']['en']['temperature']==[0.2]*3


def test_predict_failure_does_not_replace_agent():
    agent=Agent(); registry=AgentRegistry(loader=lambda model:agent)
    original=agent.predict
    def fail(*a,**k): raise RuntimeError('predict failed')
    agent.predict=fail
    with pytest.raises(RuntimeError): predict('x',REQUEST['questions'],registry=registry)
    agent.predict=original
    assert predict('x',REQUEST['questions'],registry=registry)==RAW
    assert registry.get_agent(RunConfig()) is agent


@pytest.mark.parametrize('kwargs',[{'temperature':float('nan')},{'temperature':True},{'model':''},{'lang':''}])
def test_bad_config(kwargs):
    with pytest.raises(ValueError): RunConfig(**kwargs)
