"""Real existing Python/Node persistence, plus caller no-op boundary examples."""
import json
import multiprocessing as mp
from pathlib import Path
from time import monotonic
import pytest
from laya_context_router.hooks import session_state as state
from laya_context_router.flows.subagent_test_recovery_state import (
    RecoveryTarget, TrackedAssignment, build_assignment_event, decide_enrichment,
)


def assignment(agent='child',session='s'):
    return TrackedAssignment(session,'tool-'+agent,agent,RecoveryTarget('/a.ts','class','A','m','m()'))


def save(root,event,session='s'):
    state.save_event(session,event,logs_root=root,deadline=monotonic()+20)


def transact(root,agent='child',session='s'):
    return state.inspect_and_save_event(session,
        lambda history:decide_enrichment(history,assignment(agent,session),agent_id=agent),
        logs_root=root,deadline=monotonic()+20)


def records(root,session='s'):
    return [json.loads(line) for line in (root/'session-state'/f'{session}.jsonl').read_text().splitlines()]


def test_roundtrip_replay_compaction_and_crash_commit(tmp_path):
    save(tmp_path,build_assignment_event(assignment()))
    assert transact(tmp_path).allow  # Commit exists even if process returns no output afterward.
    path=tmp_path/'session-state/s.jsonl'; committed=path.read_bytes()
    assert not transact(tmp_path).allow
    assert path.read_bytes()==committed
    save(tmp_path,{'source':{'kind':'hook','name':'PostCompact'},'type':'PostCompact','payload':{}})
    assert not transact(tmp_path).allow
    assert [e['type'] for e in records(tmp_path)]==[
        'test_assignment_identified','private_method_test_guidance_enriched','PostCompact']
    assert all(e['timestamp'].endswith('Z') for e in records(tmp_path))
    save(tmp_path,build_assignment_event(assignment(session='other')),session='other')
    assert transact(tmp_path,session='other').allow


def worker(root,agent,barrier,queue):
    try:
        barrier.wait(timeout=10)
        queue.put(('ok',transact(Path(root),agent).allow))
    except BaseException as exc:
        queue.put(('error',repr(exc)))


@pytest.mark.parametrize('agents',[('child','child'),('one','two')])
def test_concurrent_enrichment(tmp_path,agents):
    for agent in set(agents): save(tmp_path,build_assignment_event(assignment(agent)))
    ctx=mp.get_context('fork'); barrier=ctx.Barrier(2); queue=ctx.Queue()
    processes=[ctx.Process(target=worker,args=(str(tmp_path),a,barrier,queue)) for a in agents]
    try:
        for p in processes:p.start()
        results=[queue.get(timeout=30) for _ in processes]
        assert sorted(results)==([('ok',False),('ok',True)] if agents[0]==agents[1] else [('ok',True)]*2)
        enriched=[e for e in records(tmp_path) if e['type']=='private_method_test_guidance_enriched']
        assert len(enriched)==len(set(agents))
    finally:
        for p in processes:
            p.join(timeout=5)
            if p.is_alive():p.terminate();p.join(timeout=5)
        queue.close()


def test_missing_assignment_does_not_create_state(tmp_path):
    assert not transact(tmp_path).allow
    assert not (tmp_path/'session-state/s.jsonl').exists()


def caller(root,diagnostics):
    try:
        decision=transact(root)
        return 'corrective' if decision.allow else None
    except (RuntimeError,OSError,TimeoutError,ValueError) as exc:
        diagnostics.append(type(exc).__name__)
        return None


def test_corrupt_history_diagnoses_and_noops_without_repair(tmp_path):
    path=tmp_path/'session-state/s.jsonl';path.parent.mkdir();path.write_text('{broken}\n')
    diagnostics=[]
    assert caller(tmp_path,diagnostics) is None and diagnostics
    assert path.read_text()=='{broken}\n'


def test_save_failure_no_corrective_output_or_state_mutation(tmp_path,monkeypatch):
    save(tmp_path,build_assignment_event(assignment()))
    path=tmp_path/'session-state/s.jsonl'; original=path.read_bytes()
    real=state._Bridge.call
    def failing(self,operation,event=None):
        if operation=='save':raise OSError('write unavailable')
        return real(self,operation,event)
    monkeypatch.setattr(state._Bridge,'call',failing)
    diagnostics=[]
    assert caller(tmp_path,diagnostics) is None and diagnostics==['OSError']
    assert path.read_bytes()==original


def test_deadline_no_state_written(tmp_path):
    with pytest.raises(TimeoutError):
        state.inspect_and_save_event('s',lambda h:decide_enrichment(h,assignment(),agent_id='child'),
            logs_root=tmp_path,deadline=monotonic()-1)
    assert not (tmp_path/'session-state/s.jsonl').exists()
