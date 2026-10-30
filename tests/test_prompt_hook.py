"""Synthetic official-protocol input; only laya_mlx boundary is mocked in child."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from laya_context_router.building_blocks.typescript import outline, collect_project_context
from test_method_selection import questions_for, raw_for

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / 'hooks/user_prompt_submit.py'
from laya_context_router.context_format import format_context


def hook_case(tmp_path, text='function greet() { return "😀"; }'):
    repo = tmp_path/'repo'; repo.mkdir(); cwd = repo/'nested'; cwd.mkdir()
    path = cwd/'a.ts'; path.write_text(text)
    data = outline(path); q = questions_for(data); chosen = data['callables'][0]['signature']
    event = {'session_id':'synthetic-session','transcript_path':'unused.jsonl','permission_mode':'default',
             'hook_event_name':'UserPromptSubmit','cwd':str(cwd),'prompt':'Explain `a.ts`: how does greet work?'}
    config = repo/'config.json'; config.write_text(json.dumps({'model':'mock-hook','temperature':.2,'lang':'fr'}))
    shim = tmp_path/'shim'; shim.mkdir(); log = tmp_path/'events.jsonl'
    spec = tmp_path/'spec.json'; spec.write_text(json.dumps({'prompt':event['prompt'],'questions':q,'raw':raw_for(q,chosen)}))
    (shim/'sitecustomize.py').write_text('''import json, os, sys, types, time
spec=json.load(open(os.environ['HOOK_TEST_SPEC']))
def record(data):
    with open(os.environ['HOOK_TEST_LOG'],'a') as f: f.write(json.dumps(data)+'\\n')
class Agent:
    def predict(self,text,questions,**kwargs):
        assert (text,questions,kwargs)==(spec['prompt'],spec['questions'],{'lang':'fr'})
        record({'predict':text,'questions':questions,'kwargs':kwargs})
        print('synthetic SDK noise')
        if spec.get('native_noise'):
            os.write(1, b'synthetic native SDK noise\\n')
            sys.__stdout__.write('synthetic original stdout noise\\n')
            sys.__stdout__.flush()
        if spec.get('sleep'): time.sleep(spec['sleep'])
        if spec.get('error'): raise RuntimeError('planned synthetic failure')
        return spec['raw']
def load(model,**kwargs):
    assert (model,kwargs)==('mock-hook',{'lang_temperatures':{'fr':{'temperature':[.2]*3}}})
    record({'load':model,'kwargs':kwargs})
    if spec.get('native_noise'): os.write(1, b'synthetic native load noise\\n')
    if spec.get('load_sleep'): time.sleep(spec['load_sleep'])
    return Agent()
sys.modules['laya_mlx']=types.SimpleNamespace(load=load)
''')
    env={**os.environ,'PYTHONPATH':os.pathsep.join([str(shim),str(ROOT/'src')]),
         'HOOK_TEST_SPEC':str(spec),'HOOK_TEST_LOG':str(log)}
    args=['--repository-root',str(repo),'--config',str(config),'--real']
    return {'repo':repo,'path':path,'event':event,'data':data,'env':env,'args':args,'log':log,'spec':spec}


def invoke(case, payload=None, args=None):
    return subprocess.run(['bash','-c','exec "$@"','laya-hook',sys.executable,str(HOOK),*(case['args'] if args is None else args)],
                          input=json.dumps(case['event']) if payload is None else payload,
                          text=True,capture_output=True,env=case['env'],cwd=ROOT,timeout=15)


def assert_noop(result, diagnostic=True):
    assert result.returncode == 0 and result.stdout == ''
    if diagnostic: assert result.stderr


def expected_context(case):
    root=case['args'][case['args'].index('--repository-root')+1]
    context=collect_project_context(case['path'],case['data']['callables'][0]['id'],repository_root=root)
    context['coverage']='partial'
    return format_context(context,project_root=root)


def test_hook_real_pipeline_protocol_nested_cwd_and_stdout_purity(tmp_path):
    case=hook_case(tmp_path); before=case['path'].read_bytes()
    case['event']['future_unrelated_field']={'nested':True}
    original=json.dumps(case['event'])
    result=invoke(case)
    assert result.returncode==0
    assert json.loads(result.stdout)=={'hookSpecificOutput':{'hookEventName':'UserPromptSubmit','additionalContext':expected_context(case)}}
    assert 'synthetic SDK noise' in result.stderr and 'synthetic SDK noise' not in result.stdout
    assert case['path'].read_bytes()==before and json.dumps(case['event'])==original
    events=[json.loads(x) for x in case['log'].read_text().splitlines()]
    assert len(events)==2 and events[0]['load']=='mock-hook' and events[1]['predict']==case['event']['prompt']


@pytest.mark.parametrize('failure', [False, True])
def test_native_and_original_stdout_never_contaminate_protocol(tmp_path, failure):
    case=hook_case(tmp_path)
    spec=json.loads(case['spec'].read_text()); spec['native_noise']=True; spec['error']=failure
    case['spec'].write_text(json.dumps(spec))
    result=invoke(case)
    assert result.returncode==0
    if failure:
        assert result.stdout==''
        assert 'model_error' in result.stderr
    else:
        assert json.loads(result.stdout)=={'hookSpecificOutput':{
            'hookEventName':'UserPromptSubmit','additionalContext':expected_context(case)}}
        assert result.stdout.count('"hookSpecificOutput"')==1
    for noise in ('synthetic SDK noise', 'synthetic native SDK noise',
                  'synthetic original stdout noise', 'synthetic native load noise'):
        assert noise in result.stderr and noise not in result.stdout


def test_formatted_context_is_sent_unchanged_above_warning_threshold(tmp_path):
    case=hook_case(tmp_path, text='function greet() { return "😀"; }')
    full=expected_context(case)
    assert len(full)>len(case['path'].read_text())
    budget=len(case['path'].read_text())
    result=invoke(case,args=case['args']+['--max-context-chars',str(budget)])
    assert json.loads(result.stdout)['hookSpecificOutput']['additionalContext']==full


@pytest.mark.parametrize('payload', ['', '{', '[]', 'null', '{}'])
def test_invalid_input_json_no_model(tmp_path,payload):
    case=hook_case(tmp_path); assert_noop(invoke(case,payload)); assert not case['log'].exists()


@pytest.mark.parametrize('key,value', [('cwd',None),('cwd','relative'),('cwd',13),('prompt',None),('prompt',[]),('hook_event_name',None)])
def test_invalid_required_fields(tmp_path,key,value):
    case=hook_case(tmp_path); case['event'][key]=value
    assert_noop(invoke(case)); assert not case['log'].exists()


@pytest.mark.parametrize('mode', ['unmatched','event','no-real','bad-source'])
def test_hook_noop_before_sdk(tmp_path,mode):
    case=hook_case(tmp_path)
    if mode=='unmatched': case['event']['prompt']='hello'
    if mode=='event': case['event']['hook_event_name']='Stop'
    if mode=='outside': case['event']['cwd']=str(tmp_path)
    if mode=='no-real': case['args'].remove('--real')
    if mode=='bad-source': case['path'].write_text('function broken( {')
    assert_noop(invoke(case),diagnostic=mode!='event'); assert not case['log'].exists()


@pytest.mark.parametrize('args', [[],['--unknown'],['--repository-root','relative'],['--repository-root','/does-not-exist'],['--deadline','0'],['--max-context-chars','0']])
def test_invalid_cli_never_exits_two(tmp_path,args):
    case=hook_case(tmp_path); assert_noop(invoke(case,args=args)); assert not case['log'].exists()


def test_config_failure_and_model_error(tmp_path):
    case=hook_case(tmp_path)
    config=Path(case['args'][3]); config.write_text('{')
    assert_noop(invoke(case)); assert not case['log'].exists()
    config.write_text(json.dumps({'model':'mock-hook','temperature':.2,'lang':'fr'}))
    spec=json.loads(case['spec'].read_text()); spec['error']=True; case['spec'].write_text(json.dumps(spec))
    assert_noop(invoke(case)); assert len(case['log'].read_text().splitlines())==2


def test_bounded_deadline_model_sleep(tmp_path):
    case=hook_case(tmp_path); spec=json.loads(case['spec'].read_text()); spec['sleep']=10; case['spec'].write_text(json.dumps(spec))
    start=time.monotonic(); result=invoke(case,args=case['args']+['--deadline','1'])
    assert_noop(result); assert time.monotonic()-start < 4
    assert 'deadline_exceeded' in result.stderr


def test_bounded_deadline_during_model_load(tmp_path):
    case=hook_case(tmp_path); spec=json.loads(case['spec'].read_text()); spec['load_sleep']=10
    case['spec'].write_text(json.dumps(spec))
    start=time.monotonic(); result=invoke(case,args=case['args']+['--deadline','1'])
    assert_noop(result); assert 'deadline_exceeded' in result.stderr
    assert time.monotonic()-start < 4


def test_bounded_deadline_while_waiting_for_stdin(tmp_path):
    case=hook_case(tmp_path)
    process=subprocess.Popen([sys.executable,str(HOOK),*case['args'],'--deadline','1'],
                             stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,text=True,env=case['env'],cwd=ROOT)
    try:
        process.stdin.write('{')
        process.stdin.flush()
        process.wait(timeout=4)
        process.stdin.close()
        stdout,stderr=process.stdout.read(),process.stderr.read()
        assert process.returncode==0 and stdout==''
        assert 'deadline exceeded' in stderr and not case['log'].exists()
    finally:
        if process.poll() is None:
            process.kill(); process.communicate()


@pytest.mark.parametrize('status', ['missing','ambiguous'])
def test_missing_or_ambiguous_source_is_protocol_noop(tmp_path,status):
    case=hook_case(tmp_path)
    case['event']['cwd']=str(case['repo'])
    if status=='missing':
        case['path'].unlink()
    else:
        other=case['repo']/'other'; other.mkdir()
        (other/'a.ts').write_text('function greet() {}')
    result=invoke(case)
    assert_noop(result); assert status in result.stderr
    assert not case['log'].exists()


@pytest.mark.parametrize('extra', [0,1])
def test_input_character_ceiling(tmp_path,extra):
    case=hook_case(tmp_path); case['event']['prompt']='hello'
    payload=json.dumps(case['event']); payload+=' '*(65536+extra-len(payload))
    result=invoke(case,payload); assert_noop(result); assert not case['log'].exists()
    assert ('input_budget_exceeded' in result.stderr)==bool(extra)


@pytest.mark.parametrize('delta', [-1,0,1])
def test_context_character_budget_no_truncation(tmp_path,delta):
    case=hook_case(tmp_path); expected=expected_context(case)
    result=invoke(case,args=case['args']+['--max-context-chars',str(len(expected)+delta)])
    assert json.loads(result.stdout)['hookSpecificOutput']['additionalContext']==expected


@pytest.mark.parametrize('key', ['cwd','prompt','hook_event_name'])
def test_missing_required_field(tmp_path,key):
    case=hook_case(tmp_path); del case['event'][key]
    assert_noop(invoke(case)); assert not case['log'].exists()


def test_duplicate_json_fails_closed(tmp_path):
    case=hook_case(tmp_path)
    payload=json.dumps(case['event'])[:-1]+',"prompt":"overwritten"}'
    assert_noop(invoke(case,payload)); assert not case['log'].exists()


def test_oversize_source_sent_intact(tmp_path):
    case=hook_case(tmp_path, text='function greet() { return "'+ 'x'*9000 +'"; }')
    result=invoke(case)
    assert json.loads(result.stdout)['hookSpecificOutput']['additionalContext']==expected_context(case)


def test_without_sdk_mock_no_real_flag_never_imports_sdk(tmp_path):
    case=hook_case(tmp_path); case['env']['PYTHONPATH']=str(ROOT/'src')
    case['args'].remove('--real')
    result=invoke(case); assert_noop(result); assert 'explicit --real required' in result.stderr
    assert not case['log'].exists()


@pytest.mark.parametrize('deadline', ['21','300'])
def test_explicit_longer_deadline_accepts_fast_mock_request(tmp_path,deadline):
    case=hook_case(tmp_path)
    result=invoke(case,args=case['args']+['--deadline',deadline])
    assert result.returncode==0 and json.loads(result.stdout)['hookSpecificOutput']['additionalContext']==expected_context(case)


@pytest.mark.parametrize('deadline', ['0','-1','nan','inf','-inf','300.001'])
def test_deadline_invalid_values_before_sdk(tmp_path,deadline):
    case=hook_case(tmp_path)
    assert_noop(invoke(case,args=case['args']+['--deadline',deadline])); assert not case['log'].exists()


@pytest.mark.parametrize('budget', ['0','-1','nan'])
def test_context_invalid_budget_before_sdk(tmp_path,budget):
    case=hook_case(tmp_path)
    assert_noop(invoke(case,args=case['args']+['--max-context-chars',budget])); assert not case['log'].exists()


@pytest.mark.parametrize('budget', ['8001','16000'])
def test_positive_context_thresholds_are_valid(tmp_path,budget):
    case=hook_case(tmp_path)
    result=invoke(case,args=case['args']+['--max-context-chars',budget])
    assert json.loads(result.stdout)['hookSpecificOutput']['additionalContext']==expected_context(case)


def test_display_paths_use_project_root_across_event_cwds(tmp_path):
    case=hook_case(tmp_path)
    nested=invoke(case)
    case['event']['cwd']=str(case['repo'])
    at_root=invoke(case)
    assert json.loads(nested.stdout)==json.loads(at_root.stdout)
    assert 'nested/a.ts (lines 1–1)' in json.loads(at_root.stdout)['hookSpecificOutput']['additionalContext']


def hook_trace(case):
    trace=case['repo']/'hook-trace.jsonl'
    shim=Path(case['env']['PYTHONPATH'].split(os.pathsep)[0])/'sitecustomize.py'
    with shim.open('a') as file:
        file.write('\nimport laya_context_router.log_utils as logs\n'
                   f'logs.LOG_PATH=__import__("pathlib").Path({str(trace)!r})\n')
    return trace


@pytest.mark.parametrize('delta', [-1,0,1])
def test_warning_boundary_logs_exact_emitted_payload(tmp_path,delta):
    case=hook_case(tmp_path); trace=hook_trace(case)
    expected=expected_context(case); threshold=len(expected)+delta
    result=invoke(case,args=case['args']+['--max-context-chars',str(threshold)])
    response=json.loads(result.stdout)
    assert response['hookSpecificOutput']['additionalContext']==expected
    records=[json.loads(line) for line in trace.read_text().splitlines()]
    hook=[record for record in records if record['component']=='hook_gateway']
    prepared=[r['details'] for r in hook if r['event']=='response_prepared']
    final=[r['details'] for r in hook if r['event']=='gateway_finished'][-1]
    assert len(prepared)==1 and prepared[0]['serialized_bytes']==len(result.stdout.encode())
    assert 'response' not in prepared[0]
    assert final['response_present'] and final['stdout_bytes_written']==len(result.stdout.encode())
    warnings=[record for record in hook if record['event']=='context_size_warning']
    assert bool(warnings)==(delta<0)
    if warnings:
        assert {k:warnings[0]['details'][k] for k in ('context_chars','max_context_chars','action')}=={'context_chars':len(expected),'max_context_chars':threshold,'action':'send_unchanged'}
    assert len(expected.encode('utf-8'))>len(expected)


def test_large_raw_metadata_does_not_trigger_warning(tmp_path):
    case=hook_case(tmp_path); trace=hook_trace(case)
    shim=Path(case['env']['PYTHONPATH'].split(os.pathsep)[0])/'sitecustomize.py'
    with shim.open('a') as file:
        file.write('\nimport laya_context_router.flows.file_method_context as flow\n'
                   'original_run=flow.run\n'
                   'def metadata_run(*args,**kwargs):\n'
                   '    result=original_run(*args,**kwargs)\n'
                   '    result["context"]["diagnostic_metadata"]="x"*20000\n'
                   '    return result\nflow.run=metadata_run\n')
    result=invoke(case)
    assert json.loads(result.stdout)['hookSpecificOutput']['additionalContext']==expected_context(case)
    assert 'context_size_warning' not in trace.read_text()


def test_failed_stdout_write_never_logs_successful_emission(tmp_path):
    case=hook_case(tmp_path); trace=hook_trace(case)
    process=subprocess.Popen([sys.executable,str(HOOK),*case['args']],stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=case['env'],cwd=ROOT)
    process.stdout.close()
    process.stdin.write(json.dumps(case['event'])); process.stdin.close()
    process.wait(timeout=15)
    stderr=process.stderr.read()
    assert 'BrokenPipeError' in stderr
    records=[json.loads(line) for line in trace.read_text().splitlines()]
    assert any(record['event']=='response_prepared' for record in records)
    assert not any(record['event']=='response_emitted' for record in records)


def test_noop_logs_reason_without_prepared_or_emitted_payload(tmp_path):
    case=hook_case(tmp_path); trace=hook_trace(case)
    case['event']['prompt']='Explain the algorithm generally'
    result=invoke(case)
    assert_noop(result)
    records=[json.loads(line) for line in trace.read_text().splitlines()]
    hook=[record for record in records if record['component']=='hook_gateway']
    noop=[record for record in hook if record['event']=='gateway_finished']
    assert len(noop)==1 and noop[0]['details']['reason']=='no_file'
    assert noop[0]['details']['response_present'] is False and noop[0]['details']['stdout_bytes_written']==0
    assert not any(record['event'] in {'response_prepared','response_emitted'} for record in hook)
