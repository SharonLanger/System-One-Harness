import copy
import json
import sys
from pathlib import Path
import pytest
from laya_context_router.building_blocks import typescript_methods as api

@pytest.fixture
def project(tmp_path):
    (tmp_path/'tsconfig.json').write_text('{"include":["*.ts"]}')
    (tmp_path/'main.ts').write_text('export function work(n: number): number { return n; }\nexport function run(){work(1);work(2)}')
    return tmp_path

def test_four_python_operations(project):
    opts={'project_root':project}
    methods=api.list_methods('main.ts',**opts)
    assert methods['status']=='ok'
    assert [m['name'] for m in methods['data']['methods']]==['work','run']
    assert api.get_method_implementation('main.ts','work',**opts)['data']['code']=='export function work(n: number): number { return n; }'
    outgoing=api.list_called_methods('main.ts','run',**opts)
    incoming=api.list_calling_methods('main.ts','work',tsconfig_path='tsconfig.json',**opts)
    for result,key in [(outgoing,'methods'),(incoming,'callers')]:
        assert result['status']=='ok',result
        m=result['data'][key][0]
        assert m['signature']
        assert len(m['call_sites'])==2
        assert api.get_method_implementation(m['file'],m['name'],**opts)['status']=='ok'
    assert 'callable_id' not in json.dumps([methods,outgoing,incoming])

@pytest.mark.parametrize('kwargs',[{'node':'nonexistent-lcr-node'},{'helper':'missing-build.js'},{'timeout':0}])
def test_transport_errors_are_safe(project,kwargs):
    r=api.list_methods('main.ts',project_root=project,**kwargs)
    assert r['status']=='error' and r['data'] is None
    assert str(project) not in json.dumps(r)

def test_fake_protocol_failures(project):
    helper=project/'fake.py'
    for text in ['print("bad json")','print("{}")','import sys;sys.exit(2)','import time;time.sleep(2)']:
        helper.write_text(text)
        r=api.list_methods('main.ts',project_root=project,node=sys.executable,helper=helper,timeout=.1)
        assert r['status']=='error' and r['data'] is None

@pytest.mark.parametrize('file',['../escape.ts','/absolute.ts',None,3])
def test_bad_input(project,file):
    assert api.list_methods(file,project_root=project)['status']=='error'

def test_duplicate_and_uncertainty(project):
    (project/'main.ts').write_text('class A{save(){}} class B{save(n:number){}}')
    assert api.get_method_implementation('main.ts','save',project_root=project)['status']=='ambiguous'
    (project/'main.ts').write_text('class C{work(){}} function run(c:C){c.work()}')
    r=api.list_calling_methods('main.ts','work',project_root=project,tsconfig_path='tsconfig.json')
    assert r['status']=='uncertain' and r['data'] is None

def test_cwd_and_source_fidelity(project,monkeypatch):
    source='export function work() {\r\n return "id: abc123 😀";\r\n}'
    (project/'main.ts').write_bytes(source.encode())
    a=api.get_method_implementation('main.ts','work',project_root=project)
    monkeypatch.chdir(project.parent)
    assert api.get_method_implementation('main.ts','work',project_root=project)==a
    assert a['data']['code']==source

@pytest.mark.parametrize('change',[{'id':'secret'},{'start_line':0},{'end_line':False},{'signature':1},{'file':'../escape'}])
def test_schema_rejects_bad_metadata(project,monkeypatch,change):
    original=api.list_methods('main.ts',project_root=project)
    original['data']['methods'][0].update(change)
    monkeypatch.setattr(api,'_request',lambda *a,**k:copy.deepcopy(original))
    assert api.list_methods('main.ts',project_root=project)['status']=='error'

def test_symlink_loop_root_is_safe(tmp_path):
    loop=tmp_path/'loop'
    loop.symlink_to(loop)
    assert api.list_methods('main.ts',project_root=loop)['status']=='error'

@pytest.mark.parametrize('status',['uncertain','ambiguous','error'])
def test_non_success_has_no_data_or_raw_diagnostics(project,monkeypatch,status):
    code={'uncertain':'uncertain_navigation','ambiguous':'ambiguous_method','error':'source_error'}[status]
    monkeypatch.setattr(api,'_request',lambda *a,**k:{'status':status,'data':None,'diagnostics':[{'code':code,'message':'TRACE /secret/path hash-secret'}]})
    result=api.list_methods('main.ts',project_root=project)
    assert result['status']==status and result['data'] is None
    assert 'secret' not in json.dumps(result)

@pytest.mark.parametrize('change',[{'start_column':0},{'end_column':False},{'file':'/escape'},{'end_line':0}])
def test_bad_site_schema_is_safe(project,monkeypatch,change):
    result=api.list_called_methods('main.ts','run',project_root=project)
    result['data']['methods'][0]['call_sites'][0].update(change)
    monkeypatch.setattr(api,'_request',lambda *a,**k:result)
    assert api.list_called_methods('main.ts','run',project_root=project)['status']=='error'

def test_bad_scope_schema_is_safe(project,monkeypatch):
    result=api.list_calling_methods('main.ts','work',project_root=project,tsconfig_path='tsconfig.json')
    result['data']['scope']['searched_files']=['/outside']
    monkeypatch.setattr(api,'_request',lambda *a,**k:result)
    assert api.list_calling_methods('main.ts','work',project_root=project,tsconfig_path='tsconfig.json')['status']=='error'
