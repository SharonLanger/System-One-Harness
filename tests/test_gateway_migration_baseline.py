"""Characterize the active hook before replacing its process boundary."""
import json
from pathlib import Path
import subprocess
import sys
import pytest

HOOK = Path(__file__).resolve().parents[1] / 'hooks/user_prompt_submit.py'

@pytest.mark.parametrize('payload', ['', '{', 'null', '[]', '{}'])
def test_invalid_payload_never_emits_protocol_output(tmp_path, payload):
    result = subprocess.run([sys.executable, str(HOOK), '--repository-root', str(tmp_path)],
                            input=payload, text=True, capture_output=True, timeout=15)
    assert result.returncode == 0
    assert result.stdout == ''
    assert result.stderr

def test_unrelated_event_is_empty_success(tmp_path):
    result = subprocess.run([sys.executable, str(HOOK), '--repository-root', str(tmp_path)],
                            input=json.dumps({'hook_event_name': 'Stop'}),
                            text=True, capture_output=True, timeout=15)
    assert result.returncode == 0
    assert result.stdout == ''

@pytest.mark.parametrize('outcome', ['context', 'multiple_relevant'])
def test_active_hook_context_and_multiple_relevant(tmp_path, outcome):
    import os
    shim = tmp_path / 'shim'
    shim.mkdir()
    (shim / 'sitecustomize.py').write_text('''import sys, types, os
flow = types.ModuleType('laya_context_router.flows.file_method_context')
def run(*args, **kwargs):
    if os.environ['BASELINE_OUTCOME'] == 'context':
        return {'status':'context', 'reason':None, 'context':{}}
    return {'status':'noop', 'reason':'multiple_relevant', 'context':None}
flow.run = run
sys.modules[flow.__name__] = flow
formatter = types.ModuleType('laya_context_router.context_format')
formatter.format_context = lambda *args, **kwargs: 'Known context: 😀'
sys.modules[formatter.__name__] = formatter
''')
    event = {'session_id':'baseline', 'hook_event_name':'UserPromptSubmit',
             'cwd':str(tmp_path), 'prompt':'Explain `a.ts`: method?'}
    env = {**os.environ, 'BASELINE_OUTCOME':outcome,
           'PYTHONPATH':os.pathsep.join([str(shim), str(HOOK.parents[1] / 'src')])}
    result = subprocess.run([sys.executable, str(HOOK), '--repository-root',str(tmp_path),'--real'],
                            input=json.dumps(event), text=True,capture_output=True,env=env,timeout=15)
    assert result.returncode == 0
    if outcome == 'context':
        assert result.stdout == '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"Known context: 😀"}}\n'
    else:
        assert result.stdout == ''
        assert 'laya hook noop: multiple_relevant' in result.stderr
