"""Final flow decision uses fixed blocks and real source utilities."""
from time import monotonic
import json
import pytest
from .conftest import PROMPT
from laya_context_router.flows import first_method_context as flow
from laya_context_router.flows.first_method_context_utils import EnrichmentDecision
from laya_context_router.hooks import session_state
from laya_context_router.hooks.contracts import Context, Noop
from laya_context_router.hooks.gateway import serialize_response


def test_final_decision_metadata_and_skip(h, golden):
    calls=[]
    def finalize(selected): calls.append(selected); return EnrichmentDecision(False, 'already_enriched_since_compaction')
    result=h.run(finalize_enrichment=finalize)
    assert isinstance(result,Noop)
    assert serialize_response(result,'UserPromptSubmit') == ''
    assert not h.prepared()
    assert len(calls)==1
    s=calls[0]
    assert s.file_path == str(h.path.resolve())
    assert s.name == h.candidate['name'] and s.signature == h.candidate['signature']
    assert f'Lines: {s.start_line}–{s.end_line}' in golden
    assert h.run(finalize_enrichment=lambda _:EnrichmentDecision(True, 'no_history')) == Context(golden)


@pytest.mark.parametrize('kind',['no_file','action','selection','overflow','source'])
def test_early_routes_never_finalize(h,monkeypatch,kind):
    if kind=='action': h.action_result.data['action']='modify_code'
    if kind=='selection': h.selection_result.data.update(selected_id=None,reason='unclear')
    if kind=='source': monkeypatch.setattr(flow.typescript,'extract_callable',lambda *a: (_ for _ in ()).throw(ValueError()))
    calls=[]
    result=h.run(prompt='no file' if kind=='no_file' else PROMPT,
                 max_context_chars=1 if kind=='overflow' else 8000,
                 finalize_enrichment=lambda s:calls.append(s))
    assert not isinstance(result,Context) and not calls


@pytest.mark.parametrize('error',[RuntimeError('read_failed'),ValueError('invalid_session')])
def test_state_error_preserves_context_and_debug(h,monkeypatch,golden,error):
    def fail(*args,**kwargs): raise error
    monkeypatch.setattr(flow,'inspect_and_save_event',fail)
    assert flow.handle_prompt(h.request(deadline_at=monotonic()+20),h.logger,registry=h.registry)==Context(golden)
    assert any(e=='session_state_enrichment_failed' for _,e,_ in h.logs)
    assert not any(e=='session_state_saved' for _,e,_ in h.logs)


def test_adapter_uses_exact_session_deadline(h,monkeypatch):
    calls=[]; deadline=monotonic()+20
    def inspect(sid,decide,**kw):
        calls.append((sid,kw)); d,e=decide([])
        assert e['payload']['files'][0]['methods'][0]['startLine']>0
        return d
    monkeypatch.setattr(flow,'inspect_and_save_event',inspect)
    assert isinstance(flow.handle_prompt(h.request(deadline_at=deadline),h.logger,registry=h.registry),Context)
    assert calls==[('offline-session',{'deadline':deadline})]


def test_real_flow_session_sequence(h,monkeypatch,tmp_path):
    real=flow.inspect_and_save_event
    monkeypatch.setattr(flow,'inspect_and_save_event',lambda *a,**kw:real(*a,logs_root=tmp_path,**kw))
    def run(session='offline-session'):
        request=h.request(deadline_at=monotonic()+20)
        request.envelope.common['session_id']=session
        return flow.handle_prompt(request,h.logger,registry=h.registry)
    state_path=tmp_path/'session-state/offline-session.jsonl'
    assert isinstance(run(),Context)
    first=state_path.read_bytes()
    assert isinstance(run(),Noop) and state_path.read_bytes()==first
    original=h.candidate['name']
    other=next(c['name'] for c in h.outline['callables'] if c['name']!=original)
    h.choose(other)
    assert isinstance(run(),Context)
    h.choose(original)
    assert isinstance(run(),Noop)
    compact={'source':{'kind':'hook','name':'PostCompact'},'type':'PostCompact','payload':{}}
    session_state.save_event('offline-session',compact,logs_root=tmp_path,deadline=monotonic()+20)
    assert isinstance(run(),Context)
    after=state_path.read_bytes()
    assert isinstance(run(),Noop) and state_path.read_bytes()==after
    events=[json.loads(l) for l in state_path.read_text().splitlines()]
    assert [e['type'] for e in events]==['context_enriched','context_enriched','PostCompact','context_enriched']
    assert isinstance(run('other-session'),Context)
    assert state_path.read_bytes()==after
    assert any(e=='enrichment_skipped' for _,e,_ in h.logs)
    assert all(e['source']['name'] in ('first_method_context','PostCompact') for e in events)


def test_invalid_metadata_avoids_transaction(h,monkeypatch):
    def invalid(*a,**kw): raise ValueError('metadata')
    monkeypatch.setattr(flow,'SelectedMethod',invalid)
    calls=[]
    assert isinstance(h.run(finalize_enrichment=lambda s:calls.append(s)),Context)
    assert calls==[]
    assert any(e=='session_state_enrichment_failed' for _,e,_ in h.logs)


@pytest.mark.parametrize('allow',[True,False])
def test_regular_logger_failure_preserves_committed_decision(h,monkeypatch,allow):
    monkeypatch.setattr(flow,'inspect_and_save_event',lambda *a,**kw:EnrichmentDecision(allow,'no_history' if allow else 'already_enriched_since_compaction'))
    def logger(*a,**kw): raise RuntimeError('debug unavailable')
    result=flow.handle_prompt(h.request(deadline_at=monotonic()+20),logger,registry=h.registry)
    assert isinstance(result,Context if allow else Noop)


def test_finalizer_timeout_propagates(h,monkeypatch):
    def expired(*a,**kw): raise TimeoutError('deadline')
    monkeypatch.setattr(flow,'inspect_and_save_event',expired)
    with pytest.raises(TimeoutError):
        flow.handle_prompt(h.request(deadline_at=monotonic()+20),h.logger,registry=h.registry)


def test_navigation_fallback_still_finalizes(h,monkeypatch):
    def unavailable(*a,**kw): raise RuntimeError('navigation')
    monkeypatch.setattr(flow.typescript,'get_called_method_locations',unavailable)
    calls=[]
    def finalize(s): calls.append(s); return EnrichmentDecision(True,'no_history')
    result=h.run(finalize_enrichment=finalize)
    assert isinstance(result,Context) and len(calls)==1
    assert 'Methods called by' not in result.text
