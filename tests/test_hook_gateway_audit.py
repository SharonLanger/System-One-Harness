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
from hooks.gateway import parse_args
from hooks.contracts import ValidationError,Context

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
    import hooks.gateway as gateway
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
import log_utils as logs
from hooks.gateway import main
from hooks.contracts import Context,Noop
logs.LOG_PATH=Path(__LOG_DEST__)
original=logs.log
calls=[]
def log(*a,**k):calls.append(1);return original(*a,**k)
logs.log=log
main(['--hook','X'],dispatcher=lambda *a:RESULT)
assert len(calls)==7
# Existing callers retain best-effort behavior even on the same failure.
original('INFO','legacy','event')
'''.replace('__LOG_DEST__',repr(str(parent/'debug.jsonl'))).replace('RESULT',"Context('known')" if kind=='context' else "Noop('no_match')")
    r=subprocess.run([sys.executable,'-c',script],input='{"hook_event_name":"X"}',text=True,capture_output=True,
        timeout=5,env={**os.environ,'PYTHONPATH':str(ROOT/'src')})
    assert r.returncode==0 and r.stderr.count('laya logging failed')==7
    assert r.stdout==('{"hookSpecificOutput":{"hookEventName":"X","additionalContext":"known"}}\n' if kind=='context' else '')

@pytest.mark.parametrize('strict',[False,True])
def test_log_timeout_never_swallowed(strict,monkeypatch):
    import log_utils as logs
    def timeout(*a,**k):raise TimeoutError('planned')
    monkeypatch.setattr(Path,'mkdir',timeout)
    with pytest.raises(TimeoutError):logs.log('INFO','test','event',raise_on_error=strict)

def test_empty_prompt_actual_gateway_never_loads_sdk(tmp_path):
    event={'session_id':'s','transcript_path':'not-existing.jsonl','cwd':str(tmp_path),
           'hook_event_name':'UserPromptSubmit','prompt':''}
    r=subprocess.run([sys.executable,'-m','hooks.gateway','--hook','UserPromptSubmit',
        '--repository-root',str(tmp_path),'--real'],input=json.dumps(event),text=True,capture_output=True,
        timeout=5,env={**os.environ,'PYTHONPATH':str(ROOT/'src')})
    assert r.returncode==0 and r.stdout=='' and 'ineligible_request' in r.stderr
    assert 'laya_mlx' not in r.stderr

@pytest.mark.parametrize('raw,expected_code', [
    ('{ broken', 'invalid_json'),
    ('x' * 65550, 'input_budget_exceeded'),
])
def test_entry_and_bounded_input_are_logged_before_rejection(raw,expected_code,monkeypatch,capsys):
    import hooks.gateway as gateway
    records=[]
    class Input(io.StringIO):
        def read(self,n):
            assert records[0][0]=='gateway_started'
            return super().read(n)
    monkeypatch.setattr(sys,'stdin',Input(raw))
    monkeypatch.setattr(gateway,'isolate_stdout',nullcontext)
    gateway.main(['--hook','UserPromptSubmit'],
        logger=lambda level,event,**d:records.append((event,d)))
    assert capsys.readouterr().out==''
    capture=next(d for e,d in records if e=='gateway_input_received')
    assert capture['raw_input']==raw[:65536]
    assert capture['raw_input_truncated']==(len(raw)>65536)
    assert records[-1][1]['code']==expected_code
    assert len({d['invocation_id'] for e,d in records})==1

@pytest.mark.parametrize('observe',[False,True])
def test_gateway_logs_real_dispatch_chain_or_observation_bypass(observe,tmp_path,monkeypatch,capsys):
    import hooks.gateway as gateway
    from hooks.contracts import Noop
    from hooks.user_prompt_submit import dispatcher
    records=[]
    payload={'hook_event_name':'UserPromptSubmit','session_id':'audit-session',
             'cwd':str(tmp_path),'transcript_path':'unused','prompt':'hello',
             'future':{'nested':[True,1]}}
    raw=' \n'+json.dumps(payload)+'\n'
    monkeypatch.setattr(sys,'stdin',io.StringIO(raw))
    monkeypatch.setattr(gateway,'isolate_stdout',nullcontext)
    monkeypatch.setenv('CLAUDE_PROJECT_DIR',str(tmp_path))
    def handler(*args):
        assert not observe
        return Noop('no_match')
    monkeypatch.setattr(dispatcher,'_default_handler',handler)
    gateway.main(['--hook','UserPromptSubmit']+(['--observe-only'] if observe else []),
        logger=lambda level,event,**d:records.append((event,d)))
    assert capsys.readouterr().out==''
    names=[e for e,d in records]
    assert names[:3]==['gateway_started','gateway_input_received','observation_input_received' if observe else 'gateway_received']
    assert next(d for e,d in records if e=='gateway_input_received')['raw_input']==raw
    assert next(d for e,d in records if e=='gateway_received')['raw_payload']==payload
    chain=['gateway_dispatch_started','hook_dispatcher_started','hook_dispatcher_routed',
           'event_dispatcher_started','feature_started','feature_finished',
           'event_dispatcher_finished','hook_dispatcher_finished','gateway_dispatch_finished']
    if observe:
        assert not set(chain).intersection(names)
    else:
        assert [e for e in names if e in chain]==chain
    assert len({d['invocation_id'] for e,d in records})==1
    assert records[-1][0]=='gateway_finished'
    assert records[-1][1]['stdout_bytes_written']==0
