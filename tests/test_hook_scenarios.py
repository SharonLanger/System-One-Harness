"""Complete isolated scenarios: only the Laya SDK module is replaced."""
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

from laya_context_router.building_blocks.typescript import outline
from test_method_selection import questions_for, raw_for
from test_prompt_hook import ROOT, HOOK, hook_case, invoke, assert_noop, expected_context

TRACKED = ROOT/'tests/fixtures/typescript/basic.ts'


def configure(case, path, *, index=0, confidence=.95, sentinel=False):
    data=outline(path); q=questions_for(data)
    selected='none_or_unclear' if sentinel else data['callables'][index]['id']
    case['path']=path; case['data']=data
    case['event']['prompt']=f'Explain `{path}`: how does the selected callable work?'
    case['spec'].write_text(json.dumps({'prompt':case['event']['prompt'],'questions':q,
                                      'raw':raw_for(q,selected,confidence=confidence)}))


def events(case):
    return [json.loads(line) for line in case['log'].read_text().splitlines()]


def test_tracked_source_to_hook_context_and_invocation_isolation(tmp_path):
    before=TRACKED.read_bytes()
    tracked=subprocess.run(['git','ls-files','--error-unmatch',str(TRACKED.relative_to(ROOT))],cwd=ROOT,capture_output=True)
    assert tracked.returncode==0
    outputs=[]
    for index in [0,1]:
        parent=tmp_path/str(index); parent.mkdir(); case=hook_case(parent)
        configure(case,TRACKED,index=index)
        case['args'][1]=str(ROOT); case['event']['cwd']=str(ROOT)
        # Both actual functions use same model/settings in independent processes.
        case['data']={**case['data'],'callables':[case['data']['callables'][index]]}
        spec_before=case['spec'].read_bytes()
        result=invoke(case)
        assert result.returncode==0
        value=json.loads(result.stdout)
        assert value=={'hookSpecificOutput':{'hookEventName':'UserPromptSubmit','additionalContext':expected_context(case)}}
        outputs.append(value['hookSpecificOutput']['additionalContext'])
        log=events(case)
        assert len(log)==2 and log[0]['load']=='mock-hook' and log[1]['predict']==case['event']['prompt']
        assert 'synthetic SDK noise' in result.stderr and 'synthetic SDK noise' not in result.stdout
        assert case['spec'].read_bytes()==spec_before and TRACKED.read_bytes()==before
    assert outputs[0]!=outputs[1] and 'function greet' in outputs[0] and 'function twice' in outputs[1]


@pytest.mark.parametrize('scenario,reason', [('unmatched','no_file'),('rejected','method_undecided'),
                                            ('abstention','no_single_match'),('model_failure','model_error'),
                                            ('malformed_response','model_error')])
def test_complete_protocol_noop_scenarios(tmp_path,scenario,reason):
    case=hook_case(tmp_path); before=case['path'].read_bytes()
    if scenario=='unmatched': case['event']['prompt']='Explain the general algorithm'
    if scenario in {'rejected','abstention'}:
        configure(case,case['path'],confidence=.1 if scenario=='rejected' else .95,sentinel=scenario=='abstention')
    if scenario in {'model_failure','malformed_response'}:
        spec=json.loads(case['spec'].read_text())
        if scenario=='model_failure': spec['error']=True
        else: spec['raw']={'answers':{}}
        case['spec'].write_text(json.dumps(spec))
    result=invoke(case); assert_noop(result); assert reason in result.stderr
    if scenario=='unmatched': assert not case['log'].exists()
    else: assert len(events(case))==2
    assert case['path'].read_bytes()==before


def test_real_extractor_failure_after_mock_accepted_selection(tmp_path):
    case=hook_case(tmp_path)
    shim=Path(case['env']['PYTHONPATH'].split(__import__('os').pathsep)[0])/'sitecustomize.py'
    with shim.open('a') as file:
        file.write('\nfrom pathlib import Path\noriginal_predict=Agent.predict\n'
                   'def replacing_predict(self,*args,**kwargs):\n'
                   '    raw=original_predict(self,*args,**kwargs)\n'
                   f'    Path({str(case["path"])!r}).write_text("function changed() {{}}")\n'
                   '    return raw\nAgent.predict=replacing_predict\n')
    result=invoke(case); assert_noop(result); assert 'extractor_error' in result.stderr
    assert len(events(case))==2
    # This is a deliberate concurrent-edit simulation by the boundary spy,
    # confined to a disposable repo; no code is emitted for the stale ID.
    assert case['path'].read_text()=='function changed() {}'


def test_standalone_scenario_example_is_mocked_and_protocol_correct():
    result=subprocess.run([sys.executable,str(ROOT/'examples/user_prompt_submit_scenario.py')],cwd=ROOT,
                          env={**__import__('os').environ,'PYTHONPATH':str(ROOT/'src')},
                          capture_output=True,text=True,timeout=20)
    assert result.returncode==0, result.stderr
    output=json.loads(result.stdout)
    assert set(output)=={'hookSpecificOutput'}
    assert output['hookSpecificOutput']['hookEventName']=='UserPromptSubmit'
    assert 'function greet' in output['hookSpecificOutput']['additionalContext']


def test_documented_enable_disable_recipe_with_mock_only(tmp_path):
    text=(ROOT/'docs/hook-usage.md').read_text()
    examples=re.findall(r'```json\n(.*?)\n```',text,re.DOTALL)
    settings, hook_input, hook_output=map(json.loads,examples[:3])
    assert hook_input['hook_event_name']=='UserPromptSubmit'
    assert hook_output['hookSpecificOutput']['hookEventName']=='UserPromptSubmit'
    assert isinstance(hook_output['hookSpecificOutput']['additionalContext'],str)
    handler=settings['hooks']['UserPromptSubmit'][0]['hooks'][0]
    assert handler['type']=='command' and handler['timeout']>10
    assert 'remove this UserPromptSubmit entry' in text
    case=hook_case(tmp_path)
    command=(handler['command']
             .replace('/absolute/laya-context-router/.venv/bin/python',sys.executable)
             .replace('/absolute/laya-context-router/hooks/user_prompt_submit.py',str(HOOK))
             .replace('/absolute/run-config.json',case['args'][3]))
    env={**case['env'],'CLAUDE_PROJECT_DIR':str(case['repo'])}
    before=list(case['repo'].rglob('*'))
    enabled=subprocess.run(['bash','-c',command],input=json.dumps(case['event']),text=True,capture_output=True,env=env,timeout=15)
    assert json.loads(enabled.stdout)['hookSpecificOutput']['additionalContext']==expected_context(case)
    # Runtime opt-out is also testable without any Claude settings: remove --real.
    disabled=subprocess.run(['bash','-c',command.replace(' --real','')],input=json.dumps(case['event']),text=True,capture_output=True,env=env,timeout=15)
    assert_noop(disabled); assert len(events(case))==2
    assert list(case['repo'].rglob('*'))==before and not (case['repo']/'.claude').exists()


@pytest.mark.parametrize('budget_delta', [0, -1])
def test_class_method_full_hook_source_and_complete_render_budget(tmp_path, budget_delta):
    raw='public async greet(name: string): Promise<string> {\n    // interior 😀\n    return name;\n  }'
    source='// 🙃 prefix\nexport class Greeter {\n  /** attached excluded */\n  '+raw+' // trailing excluded\n}\n'
    case=hook_case(tmp_path,text=source)
    before=case['path'].read_bytes()
    assert case['data']['callables'][0]['name']=='greet'
    full=expected_context(case)
    result=invoke(case,args=case['args']+['--max-context-chars',str(len(full)+budget_delta)])
    if budget_delta < 0:
        assert_noop(result); assert 'context_budget_exceeded' in result.stderr
    else:
        output=json.loads(result.stdout)
        assert output=={'hookSpecificOutput':{'hookEventName':'UserPromptSubmit','additionalContext':full}}
        context=json.loads(output['hookSpecificOutput']['additionalContext'].split('\n',1)[1])
        assert context['code']==raw and context['coverage']=='partial'
        assert context['callable']['signature']=='public async greet(name: string): Promise<string>'
        assert context['callable']['location']=={'line':4,'column':3}
        assert context['path']==str(case['path'])
        assert 'attached' not in context['code'] and 'trailing' not in context['code']
        assert 'synthetic SDK noise' in result.stderr and 'synthetic SDK noise' not in result.stdout
    assert len(events(case))==2 and case['path'].read_bytes()==before


@pytest.mark.parametrize('source,name,signature,raw', [
    ('const ignored=0, selected = (x: string) => { return x + "😀"; };', 'selected',
     'selected = (x: string) =>', '(x: string) => { return x + "😀"; }'),
    ('const object = { selected: function inside() { return "🙃"; } };', 'selected',
     'selected: function inside()', 'function inside() { return "🙃"; }'),
])
def test_bound_expression_full_hook_labels_binding_extracts_only_callable(tmp_path, source, name, signature, raw):
    case=hook_case(tmp_path,text=source); before=case['path'].read_bytes()
    candidate=case['data']['callables'][0]
    assert candidate['name']==name and candidate['signature']==signature
    result=invoke(case)
    assert result.returncode==0
    output=json.loads(result.stdout)['hookSpecificOutput']
    assert output['hookEventName']=='UserPromptSubmit'
    context=json.loads(output['additionalContext'].split('\n',1)[1])
    assert context['code']==raw and context['callable']==candidate
    assert context['coverage']=='partial' and context['path']==str(case['path'])
    assert events(case)[1]['questions']['method']['criteria'][candidate['id']]==signature
    assert case['path'].read_bytes()==before


@pytest.mark.parametrize('source,index,name,signature,raw', [
    ('function outer() { const local = () => { return "😀"; }; return local; }', 1, 'local',
     'local = () =>', '() => { return "😀"; }'),
    ('export default function () { return "🙃"; }', 0, '<default>',
     'export default function ()', 'export default function () { return "🙃"; }'),
])
def test_recursive_and_anonymous_default_full_hook(tmp_path, source, index, name, signature, raw):
    case=hook_case(tmp_path,text=source); configure(case,case['path'],index=index)
    before=case['path'].read_bytes(); candidate=case['data']['callables'][index]
    result=invoke(case)
    assert result.returncode==0
    output=json.loads(result.stdout)['hookSpecificOutput']
    context=json.loads(output['additionalContext'].split('\n',1)[1])
    assert output['hookEventName']=='UserPromptSubmit'
    assert context['code']==raw and context['callable']==candidate
    assert candidate['name']==name and candidate['signature']==signature
    assert context['path']==str(case['path']) and context['coverage']=='partial'
    assert events(case)[1]['questions']['method']['criteria'][candidate['id']]==signature
    assert case['path'].read_bytes()==before and len(events(case))==2
