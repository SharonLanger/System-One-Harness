"""Project metadata is per invocation and independent of source configuration."""
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
import pytest
from hooks.contracts import Context, Noop
from hooks.dispatcher import ingest_common, dispatch_hook
from hooks.project_context import enrich_project_context


def envelope(cwd='/unrelated/subfolder'):
    return ingest_common({'hook_event_name':'UserPromptSubmit','session_id':'s',
        'transcript_path':'unread.jsonl','cwd':cwd,'prompt':'x','extra':{'x':[1]}},'i')


@pytest.mark.parametrize('kind',['missing','empty','relative','nonexistent','file','nullbyte'])
def test_unknown_project_is_nonfatal(tmp_path,kind):
    file=tmp_path/'file';file.write_text('x')
    value={'missing':None,'empty':'','relative':'relative','nonexistent':str(tmp_path/'absent'),
           'file':str(file),'nullbyte':'/bad\0path'}[kind]
    e=envelope();before=deepcopy(e);logs=[]
    result=enrich_project_context(e,value,lambda *a,**k:logs.append(k))
    assert result is not e and result.derived=={'project_dir':None}
    assert e==before and result.raw_payload==before.raw_payload
    assert logs[0]['project_dir_status']==('missing' if value is None else 'invalid')
    assert logs[0]['claude_project_dir']==value


def test_symlink_unicode_spaces_and_unchanged_inputs(tmp_path):
    project=tmp_path/'project 😀 space';project.mkdir();link=tmp_path/'alias';link.symlink_to(project)
    e=envelope();result=enrich_project_context(e,str(link),lambda *a,**k:None)
    assert result.derived=={'project_dir':str(project.resolve())}
    assert result.common==e.common and result.raw_payload==e.raw_payload and e.derived=={}


def test_timeout_propagates_and_inaccessible_is_unknown(tmp_path,monkeypatch):
    from pathlib import Path
    def fail(*a,**k):raise TimeoutError('deadline')
    monkeypatch.setattr(Path,'resolve',fail)
    with pytest.raises(TimeoutError):enrich_project_context(envelope(),str(tmp_path),lambda *a,**k:None)
    def denied(*a,**k):raise PermissionError('denied')
    monkeypatch.setattr(Path,'resolve',denied)
    assert enrich_project_context(envelope(),str(tmp_path),lambda *a,**k:None).derived['project_dir'] is None


@pytest.mark.parametrize('value',[False,42,[],{},'', 'relative'])
def test_bad_derived_value_is_rejected(value):
    r=dispatch_hook(envelope().raw_payload,SimpleNamespace(hook='UserPromptSubmit'),'i',lambda *a,**k:None,
        enricher=lambda e:replace(e,derived={'project_dir':value}))
    assert r.code=='invalid_enrichment'


def test_default_gateway_alternating_projects_and_missing_env(tmp_path,monkeypatch):
    from hooks import gateway,dispatcher
    from hooks.user_prompt_submit import dispatcher as prompt_dispatch
    a=tmp_path/'client1'/'app';b=tmp_path/'client2'/'app';a.mkdir(parents=True);b.mkdir(parents=True)
    seen=[];args=SimpleNamespace(hook='UserPromptSubmit',repository_root='/explicit/source')
    def handler(request,logger):seen.append(request);return Context('fixed')
    monkeypatch.setattr(prompt_dispatch,'_default_handler',handler)
    for root in [a,b,a,b,None]:
        if root:monkeypatch.setenv('CLAUDE_PROJECT_DIR',str(root))
        else:monkeypatch.delenv('CLAUDE_PROJECT_DIR',raising=False)
        assert gateway._default_dispatch(envelope().raw_payload,args,'i',lambda *a,**k:None)==Context('fixed')
    assert [r.envelope.derived['project_dir'] for r in seen]==[str(a),str(b),str(a),str(b),None]
    assert all(r.config.repository_root=='/explicit/source' for r in seen)
    assert all(r.envelope.common['cwd']=='/unrelated/subfolder' for r in seen)
    monkeypatch.setattr(gateway,'os',SimpleNamespace(environ={}))
    assert gateway._default_dispatch({'hook_event_name':'Unknown'},SimpleNamespace(hook='Unknown'),'i',
        lambda level,event,**k:pytest.fail('unknown event must not enrich') if event=='project_context_ingested' else None)==Noop('unsupported_event')


def test_relationships_and_metadata_survive(tmp_path,monkeypatch):
    from hooks import gateway
    from hooks.user_prompt_submit import dispatcher as event_dispatch
    origin=tmp_path/'A';origin.mkdir();seen=[];records=[]
    monkeypatch.setenv('CLAUDE_PROJECT_DIR',str(origin))
    monkeypatch.setattr(event_dispatch,'_default_handler',lambda r,l:seen.append(r.envelope) or Context('x'))
    for session,cwd in [('s1',str(origin/'src')),('s2',str(origin)),
                        ('s1',str(tmp_path/'B')),('s1',str(tmp_path/'A-worktree'/'src'))]:
        p=envelope(cwd).raw_payload;p['session_id']=session
        original=deepcopy(p);invocation=f'id{len(seen)}'
        gateway._default_dispatch(p,SimpleNamespace(hook='UserPromptSubmit'),invocation,
                                  lambda level,event,**data:records.append((event,data)))
        e=seen[-1]
        assert e.raw_payload==original and p==original
        assert e.common['cwd']==cwd and e.common['session_id']==session
        assert e.common['transcript_path']=='unread.jsonl' and e.invocation_id==invocation
        assert e.derived['project_dir']==str(origin)
    ingestion=[data for event,data in records if event=='hook_input_ingested']
    assert len(ingestion)==4 and all(d['project_dir']==str(origin) for d in ingestion)
    assert all(d['project_dir_source']=='CLAUDE_PROJECT_DIR' for d in ingestion)


@pytest.mark.parametrize('kind',['missing','file','noncanonical','symlink'])
def test_injected_project_must_be_existing_canonical_directory(tmp_path,kind):
    file=tmp_path/'file';file.write_text('x');alias=tmp_path/'alias';alias.symlink_to(tmp_path,target_is_directory=True)
    value={'missing':str(tmp_path/'absent'),'file':str(file),'noncanonical':str(tmp_path)+'/../'+tmp_path.name,
           'symlink':str(alias)}[kind]
    r=dispatch_hook(envelope().raw_payload,SimpleNamespace(hook='UserPromptSubmit'),'i',lambda *a,**k:None,
                   enricher=lambda e:replace(e,derived={'project_dir':value}))
    assert r.code=='invalid_enrichment'
