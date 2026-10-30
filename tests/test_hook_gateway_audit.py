"""Remaining observable contract gaps identified in the Phase6 audit."""
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from contextlib import nullcontext
import pytest
from laya_context_router.hook_gateway import parse_args
from laya_context_router.hook_contracts import ValidationError,Context

ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('flag,value,valid',[
    ('--deadline','300',True),('--deadline','300.1',False),('--deadline','inf',False),
    ('--deadline','-1',False),('--max-context-chars','0',False),('--max-context-chars','8001',True),
    ('--max-dependency-depth','0',True),('--max-dependency-depth','20',True),
    ('--max-dependency-depth','-1',False),('--max-dependency-depth','21',False),
    ('--max-dependency-chars','1',True),('--max-dependency-chars','1000000',True),
    ('--max-dependency-chars','0',False),('--max-dependency-chars','1000001',False)])
def test_cli_operational_boundaries(flag,value,valid):
    if valid:assert parse_args(['--hook','X',flag,value]).hook=='X'
    else:
        with pytest.raises(ValidationError):parse_args(['--hook','X',flag,value])

def test_stdin_read_once_and_signal_cleanup(monkeypatch):
    import laya_context_router.hook_gateway as gateway
    class Input(io.StringIO):
        calls=[]
        def read(self,n):self.calls.append(n);return super().read(n)
    stream=Input('{"hook_event_name":"X"}');output=io.StringIO()
    previous=signal.getsignal(signal.SIGALRM)
    monkeypatch.setattr(sys,'stdin',stream);monkeypatch.setattr(sys,'stdout',output)
    monkeypatch.setattr(gateway,'isolate_stdout',nullcontext)
    assert gateway.main(['--hook','X'],dispatcher=lambda *a:Context('known'),logger=lambda *a,**k:None)==0
    assert stream.calls==[65537]
    assert signal.getsignal(signal.SIGALRM)==previous and signal.getitimer(signal.ITIMER_REAL)==(0.0,0.0)
    assert json.loads(output.getvalue())['hookSpecificOutput']['additionalContext']=='known'

@pytest.mark.parametrize('kind',['context','noop'])
def test_real_log_filesystem_failure_is_nonrecursive(tmp_path,kind):
    parent=tmp_path/'parent';parent.write_text('not a directory')
    script='''from pathlib import Path
import laya_context_router.log_utils as logs
from laya_context_router.hook_gateway import main
from laya_context_router.hook_contracts import Context,Noop
logs.LOG_PATH=Path(__LOG_DEST__)
original=logs.log
calls=[]
def log(*a,**k):calls.append(1);return original(*a,**k)
logs.log=log
main(['--hook','X'],dispatcher=lambda *a:RESULT)
assert len(calls)==3
# Existing callers retain best-effort behavior even on the same failure.
original('INFO','legacy','event')
'''.replace('__LOG_DEST__',repr(str(parent/'debug.jsonl'))).replace('RESULT',"Context('known')" if kind=='context' else "Noop('no_match')")
    r=subprocess.run([sys.executable,'-c',script],input='{"hook_event_name":"X"}',text=True,capture_output=True,
        timeout=5,env={**os.environ,'PYTHONPATH':str(ROOT/'src')})
    assert r.returncode==0 and r.stderr.count('laya logging failed')==3
    assert r.stdout==('{"hookSpecificOutput":{"hookEventName":"X","additionalContext":"known"}}\n' if kind=='context' else '')

@pytest.mark.parametrize('strict',[False,True])
def test_log_timeout_never_swallowed(strict,monkeypatch):
    import laya_context_router.log_utils as logs
    def timeout(*a,**k):raise TimeoutError('planned')
    monkeypatch.setattr(Path,'mkdir',timeout)
    with pytest.raises(TimeoutError):logs.log('INFO','test','event',raise_on_error=strict)

def test_empty_prompt_actual_gateway_never_loads_sdk(tmp_path):
    event={'session_id':'s','transcript_path':'not-existing.jsonl','cwd':str(tmp_path),
           'hook_event_name':'UserPromptSubmit','prompt':''}
    r=subprocess.run([sys.executable,'-m','laya_context_router.hook_gateway','--hook','UserPromptSubmit',
        '--repository-root',str(tmp_path),'--real'],input=json.dumps(event),text=True,capture_output=True,
        timeout=5,env={**os.environ,'PYTHONPATH':str(ROOT/'src')})
    assert r.returncode==0 and r.stdout=='' and 'ineligible_request' in r.stderr
    assert 'laya_mlx' not in r.stderr
