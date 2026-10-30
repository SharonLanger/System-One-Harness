from types import SimpleNamespace
import sys
import pytest
from laya_context_router.hook_contracts import Failure
from laya_context_router.hooks.dispatcher import ingest_common
from laya_context_router.hooks.user_prompt_submit.dispatcher import PromptRequest
from laya_context_router.hooks.user_prompt_submit.prompt_context_enrichment import _prepare_feature_config


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
    import laya_context_router.laya.config as config
    monkeypatch.setattr(config,'load_config',lambda *a:pytest.fail('must not load config'))
    r=request(tmp_path);r.config.real=False;r.config.config='does-not-exist'
    assert _prepare_feature_config(r).code=='model_disabled'
    assert 'laya_mlx' not in sys.modules

def test_configuration_failure(tmp_path):
    r=request(tmp_path);r.config.config=str(tmp_path/'missing.json')
    assert _prepare_feature_config(r).code=='invalid_configuration'

from laya_context_router.hook_contracts import Context,Noop
from laya_context_router.hooks.user_prompt_submit.prompt_context_enrichment import (
    _map_flow_result,enrich_prompt_context)

# Literal exhaustive lists are independent of the production sets.
@pytest.mark.parametrize('reason',['ineligible_request','unsupported_request','no_file','multiple_files',
    'excluded','missing','ambiguous','no_candidates','candidate_budget_exceeded','ambiguous_candidates',
    'input_budget_exceeded','method_undecided','no_single_match','multiple_undecided','multiple_relevant'])
def test_expected_flow_refusals(reason,tmp_path):
    assert _map_flow_result({'status':'noop','reason':reason,'context':None},project_root=tmp_path)==Noop(reason)

@pytest.mark.parametrize('reason',['deadline_exceeded','extractor_error','invalid_dependency_budget',
    'invalid_fallback_budget','invalid_reference','model_error','source_changed','unknown_candidate',
    'inaccessible','outside_repository','not_file','invalid_resolution_mode'])
def test_operational_flow_failures(reason,tmp_path):
    assert _map_flow_result({'status':'noop','reason':reason,'context':None},project_root=tmp_path)==Failure(reason,'feature')

@pytest.mark.parametrize('result',[None,{},[],{'status':'wat','reason':None,'context':None},
    {'status':'noop','reason':'future','context':None},{'status':'noop','reason':'missing','context':{}},
    {'status':'context','reason':'missing','context':{}},{'status':'context','reason':None,'context':{}},
    {'status':'noop','reason':False,'context':None}])
def test_bad_flow_result_never_formats(result,tmp_path):
    assert _map_flow_result(result,project_root=tmp_path,
        formatter=lambda *a,**k:pytest.fail('must not format')).code=='invalid_flow_result'

def collector_context(root):
    code='function chosen() {}';digest='a'*64
    return {'schema_version':1,'path':str(root/'a.ts'),'source_hash':digest,
        'callable':{'id':f'{digest}:0:{len(code)}','name':'chosen','signature':'function chosen()',
                    'start':0,'end':len(code),'location':{'line':1,'column':1}},
        'code':code,'display_code':code,'diagnostics':[],'limitations':[],
        'coverage':'partial','dependencies':[],'gaps':[],
        'collection':{'max_depth':2,'max_dependency_chars':12000,'dependency_chars':0}}

def test_actual_formatter_root_api(tmp_path):
    result=_map_flow_result({'status':'context','reason':None,'context':collector_context(tmp_path)},project_root=tmp_path)
    assert result==Context('Selected TypeScript context (partial).\n\nSelected method\n\na.ts (lines 1–1)\nfunction chosen() {}')

@pytest.mark.parametrize('output',[None,'',False])
def test_invalid_formatter_output(output,tmp_path):
    result=_map_flow_result({'status':'context','reason':None,'context':collector_context(tmp_path)},
        project_root=tmp_path,formatter=lambda *a,**k:output)
    assert result.code=='formatting_error'

def test_formatter_exception(tmp_path):
    def formatter(*a,**k):raise ValueError('planned')
    assert _map_flow_result({'status':'context','reason':None,'context':collector_context(tmp_path)},
        project_root=tmp_path,formatter=formatter).code=='formatting_error'

def test_handler_forwards_explicit_root_mode_and_retains_raw_cwd(tmp_path):
    calls=[]
    def flow(prompt,**kwargs):
        calls.append((prompt,kwargs));return {'status':'noop','reason':'multiple_relevant','context':None}
    sentinel=object()
    result=enrich_prompt_context(request(tmp_path),lambda *a,**k:None,flow=flow,registry=sentinel)
    assert result==Noop('multiple_relevant') and len(calls)==1
    assert str(calls[0][1]['cwd'])=='/unrelated/cwd'
    assert calls[0][1]['repository_root']==tmp_path
    assert calls[0][1]['resolve_from_project_root'] is True
    assert calls[0][1]['registry'] is sentinel

@pytest.mark.parametrize('real',[False,True])
def test_real_gateway_disabled_or_ineligible_never_loads_model(tmp_path,real):
    import json,os,subprocess
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    script='''import json,sys
from laya_context_router.hook_gateway import main
import laya_context_router.flows.file_method_context as flow
import laya_context_router.context_format as fmt
def forbidden(*a,**k):raise AssertionError('unexpected flow/formatter')
fmt.format_context=forbidden
records=[]
main(ARGS,logger=lambda l,e,**d:records.append({'event':e,**d}))
assert 'laya_mlx' not in sys.modules
open(LOG,'w').write(json.dumps(records))
'''.replace('ARGS',repr(['--hook','UserPromptSubmit','--repository-root',str(tmp_path)]+(['--real'] if real else []))).replace('LOG',repr(str(tmp_path/'records.json')))
    p={'hook_event_name':'UserPromptSubmit','session_id':'session','transcript_path':'unused.jsonl','cwd':str(tmp_path),'prompt':'hello'}
    r=subprocess.run([sys.executable,'-c',script],input=json.dumps(p),text=True,capture_output=True,
        timeout=5,env={**os.environ,'PYTHONPATH':str(root/'src')})
    code='ineligible_request' if real else 'model_disabled'
    assert r.returncode==0 and r.stdout=='' and code in r.stderr
    final=json.loads((tmp_path/'records.json').read_text())[-1]
    assert (final['reason']==code and final['outcome']=='noop') if real else (final['code']==code and final['outcome']=='error')
    assert final['session_id']=='session' and final['stdout_bytes_written']==0

@pytest.mark.parametrize('stage',['root','config','validation','formatting'])
def test_timeouts_propagate_without_later_work(stage,tmp_path,monkeypatch):
    from pathlib import Path
    import laya_context_router.laya.config as config
    import laya_context_router.building_blocks.typescript as typescript
    def timeout(*a,**k):raise TimeoutError('planned')
    def forbidden(*a,**k):pytest.fail('dependent work after timeout')
    r=request(tmp_path)
    if stage=='root':
        monkeypatch.setattr(Path,'resolve',timeout)
        monkeypatch.setattr(config,'load_config',forbidden)
        r.config.config='unused'
        with pytest.raises(TimeoutError):_prepare_feature_config(r)
    elif stage=='config':
        monkeypatch.setattr(config,'load_config',timeout)
        r.config.config='unused'
        with pytest.raises(TimeoutError):_prepare_feature_config(r)
    else:
        value={'status':'context','reason':None,'context':collector_context(tmp_path)}
        if stage=='validation':
            monkeypatch.setattr(typescript,'_validate_context',timeout)
            formatter=forbidden
        else:formatter=timeout
        with pytest.raises(TimeoutError):_map_flow_result(value,project_root=tmp_path,formatter=formatter)
