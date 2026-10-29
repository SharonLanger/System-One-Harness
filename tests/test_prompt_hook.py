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
HEADER = 'Selected TypeScript context (partial):\n'


def hook_case(tmp_path, text='function greet() { return "😀"; }'):
    repo = tmp_path/'repo'; repo.mkdir(); cwd = repo/'nested'; cwd.mkdir()
    path = cwd/'a.ts'; path.write_text(text)
    data = outline(path); q = questions_for(data); chosen = data['callables'][0]['id']
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
    return HEADER+json.dumps(context,ensure_ascii=False,separators=(',',':'))


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


def test_full_context_metadata_counts_towards_budget(tmp_path):
    case=hook_case(tmp_path, text='function greet() { return "😀"; }')
    full=expected_context(case)
    assert len(full)>len(case['path'].read_text())
    budget=len(case['path'].read_text())
    result=invoke(case,args=case['args']+['--max-context-chars',str(budget)])
    assert_noop(result)
    assert 'context_budget_exceeded' in result.stderr


@pytest.mark.parametrize('payload', ['', '{', '[]', 'null', '{}'])
def test_invalid_input_json_no_model(tmp_path,payload):
    case=hook_case(tmp_path); assert_noop(invoke(case,payload)); assert not case['log'].exists()


@pytest.mark.parametrize('key,value', [('cwd',None),('cwd','relative'),('cwd',13),('prompt',None),('prompt',[]),('hook_event_name',None)])
def test_invalid_required_fields(tmp_path,key,value):
    case=hook_case(tmp_path); case['event'][key]=value
    assert_noop(invoke(case)); assert not case['log'].exists()


@pytest.mark.parametrize('mode', ['unmatched','event','outside','no-real','bad-source'])
def test_hook_noop_before_sdk(tmp_path,mode):
    case=hook_case(tmp_path)
    if mode=='unmatched': case['event']['prompt']='hello'
    if mode=='event': case['event']['hook_event_name']='Stop'
    if mode=='outside': case['event']['cwd']=str(tmp_path)
    if mode=='no-real': case['args'].remove('--real')
    if mode=='bad-source': case['path'].write_text('function broken( {')
    assert_noop(invoke(case),diagnostic=mode!='event'); assert not case['log'].exists()


@pytest.mark.parametrize('args', [[],['--unknown'],['--repository-root','relative'],['--repository-root','/does-not-exist'],['--deadline','0'],['--max-context-chars','8001']])
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
    if delta < 0: assert_noop(result); assert 'context_budget_exceeded' in result.stderr
    else: assert json.loads(result.stdout)['hookSpecificOutput']['additionalContext']==expected


@pytest.mark.parametrize('key', ['cwd','prompt','hook_event_name'])
def test_missing_required_field(tmp_path,key):
    case=hook_case(tmp_path); del case['event'][key]
    assert_noop(invoke(case)); assert not case['log'].exists()


def test_duplicate_json_and_oversize_context_fail_closed(tmp_path):
    case=hook_case(tmp_path)
    payload=json.dumps(case['event'])[:-1]+',"prompt":"overwritten"}'
    assert_noop(invoke(case,payload)); assert not case['log'].exists()
    case['path'].write_text('function greet() { return "'+ 'x'*5000 +'"; }')
    data=outline(case['path']); q=questions_for(data)
    spec={'prompt':case['event']['prompt'],'questions':q,'raw':raw_for(q,data['callables'][0]['id'])}
    case['spec'].write_text(json.dumps(spec))
    result=invoke(case); assert_noop(result); assert 'context_budget_exceeded' in result.stderr


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


@pytest.mark.parametrize('budget', ['0','-1','8001'])
def test_context_invalid_budget_before_sdk(tmp_path,budget):
    case=hook_case(tmp_path)
    assert_noop(invoke(case,args=case['args']+['--max-context-chars',budget])); assert not case['log'].exists()
