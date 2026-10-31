from dataclasses import replace
import json
from pathlib import Path
from time import monotonic
import multiprocessing as mp
import pytest
from laya_context_router.hooks import session_state as state
from laya_context_router.flows.first_method_context_utils import SelectedMethod, build_enrichment_event, decide_enrichment

S = SelectedMethod('/project/orders.ts', 'calculate', 'calculate(): number', 20, 45)
C = {'source': {'kind': 'hook', 'name': 'PostCompact'}, 'type': 'PostCompact', 'payload': {}}


def decide(history):
    d = decide_enrichment(history, S)
    return d, build_enrichment_event(S) if d.allow else None


def transact(root, session='s', callback=decide):
    return state.inspect_and_save_event(session, callback, logs_root=root, deadline=monotonic()+20)


def records(root, session='s'):
    return [json.loads(line) for line in (root / 'session-state' / (session+'.jsonl')).read_text().splitlines()]


def test_round_trip_and_compaction(tmp_path, capsys):
    assert transact(tmp_path).allow
    path = tmp_path / 'session-state/s.jsonl'; first = path.read_bytes()
    assert not transact(tmp_path).allow
    assert path.read_bytes() == first
    state.save_event('s', C, logs_root=tmp_path, deadline=monotonic()+20)
    assert transact(tmp_path).allow
    assert not transact(tmp_path).allow
    events = records(tmp_path)
    assert [e['type'] for e in events] == ['context_enriched','PostCompact','context_enriched']
    assert all(e['timestamp'].endswith('Z') for e in events)
    assert path.read_bytes().startswith(first)
    assert transact(tmp_path, 'other').allow
    assert len(records(tmp_path, 'other')) == 1
    assert capsys.readouterr().out == ''


@pytest.mark.parametrize('content', ['', '{bad}\n'])
def test_empty_or_corrupt(tmp_path, content):
    path=tmp_path/'session-state/s.jsonl'; path.parent.mkdir(); path.write_text(content)
    if content:
        with pytest.raises(RuntimeError): transact(tmp_path)
        assert path.read_text() == content
    else:
        assert transact(tmp_path).allow


def test_callback_failure_and_skip_never_write(tmp_path):
    def fail(history): raise ValueError('callback')
    with pytest.raises(ValueError): transact(tmp_path, callback=fail)
    assert not (tmp_path/'session-state/s.jsonl').exists()
    from laya_context_router.flows.first_method_context_utils import EnrichmentDecision
    assert not transact(tmp_path, callback=lambda _: (EnrichmentDecision(False,'test'), None)).allow
    assert not (tmp_path/'session-state/s.jsonl').exists()
    assert transact(tmp_path).allow


@pytest.mark.parametrize('result', [None, (), (None,None), (True,{} )])
def test_invalid_decision_no_write(tmp_path,result):
    with pytest.raises(ValueError): transact(tmp_path, callback=lambda _:result)
    assert not (tmp_path/'session-state/s.jsonl').exists()


def test_expired_deadline(tmp_path):
    with pytest.raises(TimeoutError):
        state.inspect_and_save_event('s', decide, logs_root=tmp_path, deadline=monotonic()-1)
    assert not (tmp_path/'session-state/s.jsonl').exists()


def worker(root, barrier, queue):
    try:
        barrier.wait(timeout=10)
        queue.put(('ok', transact(Path(root)).allow))
    except BaseException as exc:
        queue.put(('error', repr(exc)))


def test_two_processes_one_append(tmp_path):
    ctx=mp.get_context('fork'); barrier=ctx.Barrier(2); queue=ctx.Queue()
    processes=[ctx.Process(target=worker,args=(str(tmp_path),barrier,queue)) for _ in range(2)]
    try:
        for p in processes: p.start()
        results=[queue.get(timeout=30) for _ in processes]
        assert sorted(results) == [('ok',False),('ok',True)]
        assert len(records(tmp_path)) == 1
    finally:
        for p in processes:
            p.join(timeout=5)
            if p.is_alive(): p.terminate(); p.join(timeout=5)
        queue.close()


def test_load_response_validation(monkeypatch, tmp_path):
    class Process:
        returncode=0
        def communicate(self,*args,**kwargs): return ('{"events":"bad"}','')
        def poll(self): return 0
    monkeypatch.setattr(state.subprocess,'Popen',lambda *a,**kw:Process())
    with pytest.raises(RuntimeError,match='invalid_response'):
        transact(tmp_path)
    assert not (tmp_path/'session-state/s.jsonl').exists()


def ordered_worker(root, mode, acquired, release, queue):
    try:
        if mode == 'compact':
            bridge=state._Bridge('s',monotonic()+20,Path(root),None,None)
            with bridge.locked():
                acquired.set()
                if not release.wait(10): raise TimeoutError('test synchronization')
                bridge.call('save',C)
            queue.put(('ok','compact'))
        else:
            def held(history):
                acquired.set()
                if not release.wait(10): raise TimeoutError('test synchronization')
                return decide(history)
            queue.put(('ok',transact(Path(root),callback=held).allow))
    except BaseException as exc:
        queue.put(('error',repr(exc)))


@pytest.mark.parametrize('first_mode',['compact','enrich'])
def test_compaction_and_enrichment_lock_order(tmp_path,first_mode):
    ctx=mp.get_context('fork'); acquired=ctx.Event(); release=ctx.Event(); q=ctx.Queue()
    second_acquired=ctx.Event(); second_release=ctx.Event(); second_release.set()
    second_mode='enrich' if first_mode=='compact' else 'compact'
    first=ctx.Process(target=ordered_worker,args=(str(tmp_path),first_mode,acquired,release,q))
    second=ctx.Process(target=ordered_worker,args=(str(tmp_path),second_mode,second_acquired,second_release,q))
    try:
        first.start(); assert acquired.wait(10)
        second.start(); release.set()
        results=[q.get(timeout=30),q.get(timeout=30)]
        assert all(status=='ok' for status,_ in results),results
        expected=['PostCompact','context_enriched'] if first_mode=='compact' else ['context_enriched','PostCompact']
        assert [e['type'] for e in records(tmp_path)]==expected
        assert transact(tmp_path).allow == (first_mode=='enrich')
    finally:
        release.set()
        for p in (first,second):
            if p.pid:
                p.join(timeout=5)
                if p.is_alive(): p.terminate(); p.join(timeout=5)
        q.close()


def test_lock_wait_deadline(tmp_path,monkeypatch):
    def blocked(*a): raise BlockingIOError()
    monkeypatch.setattr(state.fcntl,'flock',blocked)
    with pytest.raises(TimeoutError):
        state.inspect_and_save_event('s',decide,logs_root=tmp_path,deadline=monotonic()+0.03)
    assert not (tmp_path/'session-state/s.jsonl').exists()


def test_subprocess_timeout_terminates_and_does_not_retry(tmp_path,monkeypatch):
    calls=[]
    class Process:
        returncode=None
        killed=False
        def communicate(self,*a,**kw):
            if not self.killed: raise state.subprocess.TimeoutExpired('node',0)
            return ('','')
        def poll(self): return 0 if self.killed else None
        def kill(self): self.killed=True
    process=Process()
    monkeypatch.setattr(state.subprocess,'Popen',lambda *a,**kw:(calls.append(a) or process))
    with pytest.raises(TimeoutError): transact(tmp_path)
    assert process.killed and len(calls)==1


def test_save_timeout_does_not_retry(tmp_path,monkeypatch):
    calls=[]
    def call(self,operation,event=None):
        calls.append(operation)
        if operation=='load': return []
        raise TimeoutError('save deadline')
    monkeypatch.setattr(state._Bridge,'call',call)
    with pytest.raises(TimeoutError): transact(tmp_path)
    assert calls==['load','save']
