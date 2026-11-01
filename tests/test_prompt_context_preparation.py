from types import SimpleNamespace
import sys
import pytest
from hooks.contracts import Failure
from hooks.dispatcher import ingest_common
from hooks.user_prompt_submit.dispatcher import PromptRequest
from hooks.user_prompt_submit.prompt_context_enrichment import _prepare_feature_config


def request(root,**options):
    event={'hook_event_name':'UserPromptSubmit','session_id':'s','transcript_path':'unused.jsonl','cwd':'/unrelated/cwd','prompt':'x'}
    return PromptRequest('x',ingest_common(event,'id'),SimpleNamespace(repository_root=root,real=True,config=None,**options))

@pytest.mark.parametrize('root',[None,'','relative',False,1])
def test_invalid_explicit_root(root):
    result=_prepare_feature_config(request(root))
    assert isinstance(result,Failure) and result.code=='invalid_project_root'

def test_missing_or_file_root(tmp_path):
    file=tmp_path/'file';file.write_text('x')
    for root in (tmp_path/'missing',file):
        assert _prepare_feature_config(request(root)).code=='invalid_project_root'

def test_root_provenance_and_cwd_preserved(tmp_path):
    root=tmp_path/'space 😀';root.mkdir()
    result=_prepare_feature_config(request(root))
    assert result['project_root']==root and result['project_root_source']=='explicit_configuration'
    assert result['cwd']=='/unrelated/cwd'
    assert 'laya_mlx' not in sys.modules

def test_disabled_does_not_load_config_or_sdk(tmp_path,monkeypatch):
    import laya.config as config
    monkeypatch.setattr(config,'load_config',lambda *a:pytest.fail('must not load config'))
    r=request(tmp_path);r.config.real=False;r.config.config='does-not-exist'
    assert _prepare_feature_config(r).code=='model_disabled'
    assert 'laya_mlx' not in sys.modules

def test_configuration_failure(tmp_path):
    r=request(tmp_path);r.config.config=str(tmp_path/'missing.json')
    assert _prepare_feature_config(r).code=='invalid_configuration'


@pytest.mark.parametrize('real',[False,True])
def test_real_gateway_disabled_or_no_reference_never_loads_model(tmp_path,real):
    import json,os,subprocess
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    script='''import json,sys
from hooks.gateway import main
from laya.registry import AgentRegistry
def forbidden(*a,**k):raise AssertionError('unexpected model access')
AgentRegistry.get_agent=forbidden
records=[]
main(ARGS,logger=lambda l,e,**d:records.append({'event':e,**d}))
assert 'laya_mlx' not in sys.modules
open(LOG,'w').write(json.dumps(records))
'''.replace('ARGS',repr(['--hook','UserPromptSubmit','--repository-root',str(tmp_path)]+(['--real'] if real else []))).replace('LOG',repr(str(tmp_path/'records.json')))
    p={'hook_event_name':'UserPromptSubmit','session_id':'session','transcript_path':'unused.jsonl','cwd':str(tmp_path),'prompt':'hello'}
    r=subprocess.run([sys.executable,'-c',script],input=json.dumps(p),text=True,capture_output=True,
        timeout=5,env={**os.environ,'PYTHONPATH':str(root/'src')})
    code='no_file' if real else 'model_disabled'
    assert r.returncode==0 and r.stdout=='' and code in r.stderr
    final=json.loads((tmp_path/'records.json').read_text())[-1]
    assert (final['reason']==code and final['outcome']=='noop') if real else (final['code']==code and final['outcome']=='error')
    assert final['session_id']=='session' and final['stdout_bytes_written']==0


@pytest.mark.parametrize('stage', ['root', 'config'])
def test_preparation_timeouts_propagate_without_later_work(stage, tmp_path, monkeypatch):
    from pathlib import Path
    from laya import config
    def timeout(*args, **kwargs):
        raise TimeoutError('planned')
    def forbidden(*args, **kwargs):
        pytest.fail('dependent work after timeout')
    r = request(tmp_path); r.config.config = 'unused'
    if stage == 'root':
        monkeypatch.setattr(Path, 'resolve', timeout)
        monkeypatch.setattr(config, 'load_config', forbidden)
    else:
        monkeypatch.setattr(config, 'load_config', timeout)
    with pytest.raises(TimeoutError):
        _prepare_feature_config(r)
