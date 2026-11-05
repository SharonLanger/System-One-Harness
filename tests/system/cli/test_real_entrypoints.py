"""Public process protocol through real blocks, extraction and session persistence."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from tests.support.offline_scenarios import PROMPT, SOURCE

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def invoke(tmp_path):
    project = tmp_path / 'project'
    project.mkdir()
    (project / 'sample.ts').write_text(SOURCE)
    state = tmp_path / 'state'

    def run(entry='cli', scenario='success', session='one', hook='UserPromptSubmit'):
        payload = {'hook_event_name': hook, 'session_id': session, 'cwd': str(project),
                   'transcript_path': '/unused', 'prompt': PROMPT, 'trigger': 'manual'}
        if scenario == 'missing':
            payload['prompt'] = 'Explain `missing.ts`: calculateTotal'
        elif scenario == 'empty':
            payload['prompt'] = ''
        elif scenario == 'no_candidates':
            (project / 'sample.ts').write_text('export const value = 1;\n')
        raw = '{bad json' if scenario == 'malformed' else json.dumps(payload)
        args = ['--hook', hook, '--repository-root', str(project), '--deadline', '30',
                '--log-state' if hook == 'PostCompact' else '--real']
        if scenario == 'budget':
            args += ['--max-context-chars', '1']
        # PostCompact does not call Laya.
        script = 'empty' if hook == 'PostCompact' else scenario
        env = {**os.environ, 'PYTHONPATH': os.pathsep.join([str(ROOT / 'src'), str(ROOT)])}
        env.pop('CLAUDE_PROJECT_DIR', None)
        result = subprocess.run([sys.executable, '-m', 'tests.support.cli_runner', entry, script,
                                 str(project), str(state), *args], input=raw, text=True,
                                capture_output=True, cwd=tmp_path, env=env, timeout=40)
        evidence = [line for line in result.stderr.splitlines() if line.startswith('TEST_EVIDENCE:')]
        assert len(evidence) == 1, result.stderr
        diagnostic = json.loads(evidence[0].removeprefix('TEST_EVIDENCE:'))
        stderr = '\n'.join(line for line in result.stderr.splitlines() if not line.startswith('TEST_EVIDENCE:'))
        return result, diagnostic, stderr
    return run


@pytest.mark.parametrize('entry', ['cli', 'gateway'])
def test_real_entrypoint_context_and_session_lifecycle(invoke, entry):
    first, details, stderr = invoke(entry)
    assert first.returncode == 0 and stderr == ''
    output = json.loads(first.stdout)
    assert set(output) == {'hookSpecificOutput'}
    context = output['hookSpecificOutput']
    assert context['hookEventName'] == 'UserPromptSubmit'
    assert SOURCE.strip() in context['additionalContext']
    assert first.stdout.endswith('\n') and first.stdout.count('\n') == 1
    assert details['calls'] == 2
    duplicate, _, _ = invoke(entry)
    assert duplicate.returncode == 0 and duplicate.stdout == ''
    compact, details, stderr = invoke(entry, hook='PostCompact')
    assert compact.returncode == 0 and compact.stdout == ''
    assert stderr == 'laya hook noop: session_state_logged'
    assert details['calls'] == 0
    after, _, _ = invoke(entry)
    other, _, _ = invoke(entry, session='two')
    assert after.returncode == other.returncode == 0
    assert after.stdout == other.stdout == first.stdout


@pytest.mark.parametrize('entry', ['cli', 'gateway'])
@pytest.mark.parametrize('scenario,calls', [('unsupported', 1), ('ambiguous', 2), ('missing', 0),
    ('empty', 0), ('invalid', 1), ('failure', 1), ('no_candidates', 1), ('source_removed', 2), ('budget', 2)])
def test_real_entrypoint_noncontext_never_emits_context(invoke, entry, scenario, calls):
    result, details, stderr = invoke(entry, scenario)
    assert result.returncode == 0, stderr
    assert result.stdout == ''
    assert details['calls'] == calls
    finished = [r for r in details['records'] if r['event'] == 'flow_finished']
    assert len(finished) == 1
    outcome = finished[0]['details']
    if scenario in {'invalid', 'failure', 'source_removed'}:
        assert outcome['outcome'] == 'Failure'
        assert outcome['stage'] == ('extraction' if scenario == 'source_removed' else 'requested_action')
    else:
        assert outcome['outcome'] == 'Noop'
        assert outcome['reason'] == {'unsupported': 'modify_code', 'ambiguous': 'no_single_match',
            'missing': 'missing', 'empty': 'ineligible_request', 'no_candidates': 'no_candidates',
            'budget': 'output_budget_exceeded'}[scenario]


@pytest.mark.parametrize('entry', ['cli', 'gateway'])
def test_malformed_input_never_calls_model(invoke, entry):
    result, details, stderr = invoke(entry, 'malformed')
    assert result.returncode == 0 and result.stdout == ''
    assert 'invalid_json' in stderr and details['calls'] == 0


@pytest.mark.parametrize('entry', ['cli', 'gateway'])
def test_sdk_noise_cannot_corrupt_public_json(invoke, entry):
    result, details, stderr = invoke(entry, 'noise')
    assert result.returncode == 0
    assert 'additionalContext' in json.loads(result.stdout)['hookSpecificOutput']
    assert 'scripted SDK stdout noise' in stderr and 'scripted SDK fd noise' in stderr
    assert details['calls'] == 2
