import json
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import monotonic
from types import SimpleNamespace

import pytest

from hooks.contracts import Failure, Noop
from hooks.dispatcher import dispatch_hook
from hooks.gateway import parse_args, parse_payload, POST_COMPACT_INPUT_CHARS
from hooks.session_state import ROOT, save_event

EVENT = {'source': {'kind': 'hook', 'name': 'PostCompact'}, 'type': 'PostCompact', 'payload': {}}


def payload(tmp_path, trigger='manual'):
    return {'hook_event_name': 'PostCompact', 'session_id': 'abc123', 'cwd': str(tmp_path),
            'transcript_path': '/unused/transcript', 'trigger': trigger, 'compact_summary': 'SECRET שלום'}


@pytest.mark.parametrize('trigger', ['manual', 'auto'])
def test_dispatch_writes_exact_event(tmp_path, monkeypatch, trigger):
    calls=[]
    monkeypatch.setattr('hooks.post_compact.dispatcher.save_event',
                        lambda *a, **kw: calls.append((a,kw)))
    args=parse_args(['--hook','PostCompact','--log-state']);args.deadline_at=monotonic()+10
    assert isinstance(dispatch_hook(payload(tmp_path,trigger),args,'id',lambda *a,**kw:None),Noop)
    assert calls[0][0] == ('abc123',EVENT)


def test_routing_and_invalid_input(tmp_path, monkeypatch):
    monkeypatch.setattr('hooks.post_compact.dispatcher.save_event',
                        lambda *a,**kw: pytest.fail('must not write'))
    args=SimpleNamespace(hook='PostCompact',log_state=False)
    assert dispatch_hook(payload(tmp_path),args,'id',lambda *a,**kw:None).reason=='unsupported_action'
    args.log_state=True
    assert isinstance(dispatch_hook(payload(tmp_path,'bad'),args,'id',lambda *a,**kw:None),Failure)
    bad=payload(tmp_path);bad.pop('session_id')
    assert isinstance(dispatch_hook(bad,args,'id',lambda *a,**kw:None),Failure)
    for argv in [['--hook','UserPromptSubmit','--log-state'],['--hook','PostCompact','--log-state','--real']]:
        with pytest.raises(Exception):parse_args(argv)


def test_input_limits_and_summary(tmp_path):
    value=payload(tmp_path);value['compact_summary']='x'*70000
    assert parse_payload(json.dumps(value),'PostCompact')==value
    with pytest.raises(Exception):parse_payload('x'*(POST_COMPACT_INPUT_CHARS+1),'PostCompact')
    value['hook_event_name']='UserPromptSubmit'
    with pytest.raises(Exception):parse_payload(json.dumps(value),'UserPromptSubmit')


def test_adapter_real_node_concurrent_and_sessions(tmp_path):
    if not shutil.which('node') or not (ROOT/'build/typescript/session-state-cli.js').exists():
        pytest.fail('build TypeScript helper before running integration tests')
    def write(i):save_event('abc123',EVENT,deadline=monotonic()+15,logs_root=tmp_path)
    with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(write,range(8)))
    records=[json.loads(x) for x in (tmp_path/'session-state/abc123.jsonl').read_text().splitlines()]
    assert len(records)==8
    assert all(x['type']=='PostCompact' and x['payload']=={} and x['timestamp'] for x in records)
    save_event('other',EVENT,deadline=monotonic()+10,logs_root=tmp_path)
    assert len((tmp_path/'session-state/other.jsonl').read_text().splitlines())==1
    original=(tmp_path/'session-state/abc123.jsonl').read_bytes()
    with (tmp_path/'session-state/abc123.jsonl').open('ab') as f:f.write(b'broken')
    with pytest.raises(RuntimeError):write(0)
    assert (tmp_path/'session-state/abc123.jsonl').read_bytes()==original+b'broken'


def test_adapter_errors_and_lock_deadline(tmp_path):
    import fcntl
    with pytest.raises(ValueError):save_event('../bad',EVENT,deadline=monotonic()+10,logs_root=tmp_path)
    with pytest.raises(FileNotFoundError):save_event('id',EVENT,deadline=monotonic()+10,logs_root=tmp_path,helper=tmp_path/'missing')
    locks=tmp_path/'session-state-locks';locks.mkdir(exist_ok=True)
    with (locks/'id.lock').open('a') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX)
        with pytest.raises(TimeoutError):save_event('id',EVENT,deadline=monotonic()+0.05,logs_root=tmp_path)
    save_event('id',EVENT,deadline=monotonic()+10,logs_root=tmp_path)


def test_gateway_empty_stdout_no_summary_in_diagnostics(tmp_path):
    script='''import sys
from hooks.gateway import main
from hooks.contracts import Noop
raise SystemExit(main(['--hook','PostCompact','--log-state'], dispatcher=lambda *a: Noop('session_state_logged'), logger=lambda *a,**kw: print(repr(kw),file=sys.stderr)))'''
    result=subprocess.run([sys.executable,'-c',script],input=json.dumps(payload(tmp_path)),
                          text=True,capture_output=True,env={**__import__('os').environ,'PYTHONPATH':str(ROOT/'src')})
    assert result.returncode==0 and result.stdout==''
    assert 'SECRET' not in result.stderr and 'session_state_logged' in result.stderr


def test_plugin_registration():
    hooks=json.loads((ROOT/'plugins/hook-laya/hooks/hooks.json').read_text())['hooks']
    assert 'UserPromptSubmit' in hooks
    entry=hooks['PostCompact'][0]
    assert 'matcher' not in entry and len(entry['hooks'])==1
    assert '--hook PostCompact --log-state' in entry['hooks'][0]['command']


def test_child_timeout_is_reaped_and_next_write_succeeds(tmp_path):
    helper=tmp_path/'slow.js';helper.write_text('setTimeout(() => {}, 30000);')
    with pytest.raises(TimeoutError) as expired:
        save_event('id',EVENT,deadline=monotonic()+0.15,logs_root=tmp_path,helper=helper)
    assert isinstance(expired.value.__cause__, subprocess.TimeoutExpired)
    save_event('id',EVENT,deadline=monotonic()+10,logs_root=tmp_path)


def test_gateway_real_dispatch_and_store(tmp_path):
    script='''from pathlib import Path
import sys
import hooks.session_state as state
from hooks.gateway import main
state.ROOT = Path(sys.argv[1])
# Resolve the built helper independently while redirecting only the log destination.
original=state.save_event
from hooks.post_compact import dispatcher
dispatcher.save_event=lambda session,event,**kw: original(session,event,logs_root=Path(sys.argv[1]),helper=Path(sys.argv[2]),**kw)
raise SystemExit(main(['--hook','PostCompact','--log-state'], logger=lambda *a,**kw: None))'''
    result=subprocess.run([sys.executable,'-c',script,str(tmp_path),str(ROOT/'build/typescript/session-state-cli.js')],
        input=json.dumps(payload(tmp_path)),text=True,capture_output=True,
        env={**__import__('os').environ,'PYTHONPATH':str(ROOT/'src')})
    assert result.returncode==0 and result.stdout==''
    record=json.loads((tmp_path/'session-state/abc123.jsonl').read_text())
    assert record['type']=='PostCompact' and record['payload']=={}

