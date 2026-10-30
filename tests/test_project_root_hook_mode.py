"""Root-mode selection retains the real resolver/helper; model alone is stubbed."""
import json
import subprocess
import sys
from pathlib import Path
import pytest
from laya_context_router.building_blocks.resolve_file import resolve_file
from laya_context_router.flows.file_method_context import run
from test_prompt_hook import hook_case,ROOT

@pytest.mark.parametrize('value',[None,0,1,'true',[],{}])
def test_invalid_root_mode_fails_before_helper_or_model(value,tmp_path,monkeypatch):
    import laya_context_router.building_blocks.resolve_file as facade
    monkeypatch.setattr(facade.typescript,'resolve_reference',lambda *a,**k:pytest.fail('helper ran'))
    with pytest.raises(ValueError,match='boolean'):
        resolve_file('a.ts',cwd=tmp_path,repository_root=tmp_path,resolve_from_project_root=value)
    assert run('Explain `a.ts`: method?',cwd=tmp_path,repository_root=tmp_path,config=None,registry=None,
               resolve_from_project_root=value)['reason']=='invalid_resolution_mode'

def test_legacy_and_root_search_bases_differ(tmp_path):
    nested=tmp_path/'nested';nested.mkdir()
    root=tmp_path/'a.ts';root.write_text('function root() {}')
    child=nested/'a.ts';child.write_text('function nested() {}')
    legacy=resolve_file('a.ts',cwd=nested,repository_root=tmp_path)
    assert legacy.status=='ambiguous' and legacy.candidates==(root,child)
    assert resolve_file('a.ts',cwd=nested,repository_root=tmp_path,
                        resolve_from_project_root=True).selected_path==root

def invoke_gateway(case,*,process_cwd=ROOT):
    return subprocess.run([sys.executable,'-m','laya_context_router.hook_gateway','--hook','UserPromptSubmit',*case['args']],
        input=json.dumps(case['event']),text=True,capture_output=True,timeout=15,env=case['env'],cwd=process_cwd)

@pytest.mark.parametrize('location',['nested','root','unrelated'])
def test_actual_gateway_root_selection_and_display_ignore_cwd(tmp_path,location):
    code='function greet() { return "ROOT"; }'
    case=hook_case(tmp_path,code)
    from test_prompt_hook import hook_trace
    trace=hook_trace(case)
    root_file=case['repo']/'a.ts';case['path'].replace(root_file)
    case['path'].write_text('function other() { return "NESTED"; }')
    unrelated=tmp_path/'unrelated';unrelated.mkdir()
    cwd={'nested':case['path'].parent,'root':case['repo'],'unrelated':unrelated}[location]
    case['event']['cwd']=str(cwd)
    before=json.dumps(case['event'])
    result=invoke_gateway(case,process_cwd=unrelated)
    assert result.returncode==0
    context=json.loads(result.stdout)['hookSpecificOutput']['additionalContext']
    assert context.startswith('Selected TypeScript context (partial).\n\nSelected method\n\na.ts (lines 1–1)\n'+code)
    assert 'NESTED' not in context and str(case['repo']) not in context
    assert json.dumps(case['event'])==before
    records=[json.loads(line) for line in trace.read_text().splitlines()]
    ingested=next(r for r in records if r['event']=='hook_input_ingested')
    assert ingested['details']['cwd']==str(cwd)
    events=[json.loads(x) for x in case['log'].read_text().splitlines()]
    assert len(events)==2  # one load, one prediction; no duplicate inference

@pytest.mark.parametrize('reference,status',[('../outside/a.ts','outside_repository'),
    ('missing/a.ts','missing'),('escape.ts','outside_repository')])
def test_root_mode_reuses_containment_and_missing(tmp_path,reference,status):
    root=tmp_path/'repo';root.mkdir();outside=tmp_path/'outside';outside.mkdir()
    source=outside/'a.ts';source.write_text('function outside() {}')
    (root/'escape.ts').symlink_to(source)
    assert resolve_file(reference,cwd=outside,repository_root=root,
                        resolve_from_project_root=True).status==status

def test_root_mode_ambiguity_absolute_and_prefix_collision(tmp_path):
    root=tmp_path/'repo';root.mkdir();other=tmp_path/'repository';other.mkdir()
    for folder in ('one','two'):
        d=root/folder;d.mkdir();(d/'a.ts').write_text('function x() {}')
    assert resolve_file('a.ts',cwd=other,repository_root=root,resolve_from_project_root=True).status=='ambiguous'
    assert resolve_file(str(root/'one/a.ts'),cwd=other,repository_root=root,
                        resolve_from_project_root=True).selected_path==root/'one/a.ts'
    outside=other/'a.ts';outside.write_text('function x() {}')
    assert resolve_file(str(outside),cwd=other,repository_root=root,
                        resolve_from_project_root=True).status=='outside_repository'

def test_wrapper_and_shared_entry_return_identical_context(tmp_path):
    from test_prompt_hook import invoke
    case=hook_case(tmp_path)
    direct=invoke_gateway(case);compat=invoke(case)
    assert direct.returncode==compat.returncode==0
    assert direct.stdout==compat.stdout and json.loads(direct.stdout)

@pytest.mark.parametrize('mode',['multiple','model_error','invalid_budget'])
def test_actual_gateway_complete_noop_and_errors(tmp_path,mode):
    case=hook_case(tmp_path)
    spec=json.loads(case['spec'].read_text())
    if mode=='multiple':
        spec['raw']['answers']['multiple_relevant']['noul']=.95
    if mode=='model_error':spec['error']=True
    if mode=='invalid_budget':case['args']+=['--max-dependency-depth','-1']
    case['spec'].write_text(json.dumps(spec))
    if mode in {'multiple','model_error'}:
        shim=Path(case['env']['PYTHONPATH'].split(__import__('os').pathsep)[0])/'sitecustomize.py'
        with shim.open('a') as f:
            f.write("\nimport laya_context_router.flows.file_method_context as flow\nimport laya_context_router.context_format as fmt\ndef forbidden(*a,**k):raise AssertionError('must not collect or format')\nflow.collect_project_context=forbidden\nfmt.format_context=forbidden\n")
    result=invoke_gateway(case)
    assert result.returncode==0 and result.stdout==''
    reason={'multiple':'multiple_relevant','model_error':'model_error','invalid_budget':'invalid_budget'}[mode]
    assert reason in result.stderr
    if mode=='invalid_budget':assert not case['log'].exists()


@pytest.mark.parametrize('reference',['../outside.ts','escape.ts'])
def test_gateway_never_reads_outside_source_or_loads_model(tmp_path,reference):
    case=hook_case(tmp_path)
    outside=tmp_path/'outside.ts';outside.write_text('function secret() {}')
    (case['repo']/'escape.ts').symlink_to(outside)
    case['event']['prompt']=f'Explain `{reference}`: method?'
    result=invoke_gateway(case)
    assert result.returncode==0 and result.stdout=='' and 'outside_repository' in result.stderr
    assert not case['log'].exists()


def test_gateway_unicode_root(tmp_path):
    folder=tmp_path/'space 😀';folder.mkdir()
    case=hook_case(folder)
    result=invoke_gateway(case)
    assert result.returncode==0 and 'function greet()' in json.loads(result.stdout)['hookSpecificOutput']['additionalContext']
