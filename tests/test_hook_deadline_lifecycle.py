"""Bounded ordinary callback and pipe behavior; not a hard startup/OS guarantee."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import pytest

ROOT=Path(__file__).resolve().parents[1]
ENV={**os.environ,'PYTHONPATH':str(ROOT/'src')}

@pytest.mark.parametrize('stage',['final','processing'])
def test_deadline_covers_final_and_error_logging(tmp_path,stage):
    path=tmp_path/'records.jsonl'
    code='''import json,time
from laya_context_router.hooks.gateway import main
from laya_context_router.hooks.contracts import Context
calls=[]
processing_started=False
def logger(level,event,**details):
    calls.append(event)
    if MODE=='final' and event=='gateway_finished':time.sleep(30)
    if MODE=='processing' and processing_started:raise AssertionError('post-expiration callback')
    with open(LOG,'a') as f:f.write(json.dumps({'event':event,**details})+'\\n')
def dispatch(*a):
    global processing_started
    processing_started=True
    if MODE=='processing':time.sleep(30)
    return Context('known')
main(['--hook','X','--deadline','.15'],dispatcher=dispatch,logger=logger)
'''.replace('MODE',repr(stage)).replace('LOG',repr(str(path)))
    started=time.monotonic()
    r=subprocess.run([sys.executable,'-c',code],input='{"hook_event_name":"X"}',text=True,
        capture_output=True,timeout=5,env=ENV)
    assert time.monotonic()-started<4 and r.returncode==0
    assert r.stdout==('{"hookSpecificOutput":{"hookEventName":"X","additionalContext":"known"}}\n' if stage=='final' else '')
    assert 'deadline' in r.stderr
    assert 'post-expiration callback' not in r.stderr
    records=[json.loads(x) for x in path.read_text().splitlines()]
    assert not any(x['event']=='gateway_finished' for x in records)
    if stage=='processing':assert [x['event'] for x in records]==['gateway_started','gateway_input_received','gateway_received','gateway_dispatch_started']

def test_undrained_output_pipe_times_out_without_retrying_delivery(tmp_path):
    path=tmp_path/'records.jsonl'
    code='''import json
from laya_context_router.hooks.gateway import main
from laya_context_router.hooks.contracts import Context
def logger(level,event,**details):
    with open(LOG,'a') as f:f.write(json.dumps({'event':event,**details})+'\\n')
main(['--hook','X','--deadline','.15'],dispatcher=lambda *a:Context('x'*2000000),logger=logger)
'''.replace('LOG',repr(str(path)))
    p=subprocess.Popen([sys.executable,'-c',code],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        text=True,env=ENV)
    try:
        p.stdin.write('{"hook_event_name":"X"}');p.stdin.close()
        # Deliberately retain an open reader without draining while child writes.
        p.wait(timeout=5)
        output=p.stdout.read();stderr=p.stderr.read()
        assert p.returncode==0 and 'deadline_exceeded' in stderr
        assert 'stdout_bytes_written=unknown' in stderr
        assert len(output)<2000000
        records=[json.loads(x) for x in path.read_text().splitlines()]
        assert any(x['event']=='response_prepared' for x in records)
        assert not any(x['event']=='gateway_finished' for x in records)
    finally:
        if p.poll() is None:p.kill();p.wait()
        p.stdout.close();p.stderr.close()

def test_invalid_cli_does_not_read_stdin_or_call_logger(monkeypatch,capsys):
    import io
    from laya_context_router.hooks.gateway import main
    class Unreadable(io.StringIO):
        def read(self,*a):pytest.fail('read before valid CLI')
    monkeypatch.setattr(sys,'stdin',Unreadable())
    assert main([],logger=lambda *a,**k:pytest.fail('unarmed callback'))==0
    captured=capsys.readouterr()
    assert captured.out=='' and 'invalid_hook_argument' in captured.err
    assert '[' in captured.err  # invocation ID remains diagnostic evidence
