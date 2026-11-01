"""The hook package owns transport and contracts; the outer script only forwards."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_outer_launcher_forwards_arguments_once(monkeypatch):
    from hooks import gateway
    spec = importlib.util.spec_from_file_location('outer_hook_launcher', ROOT / 'hooks/user_prompt_submit.py')
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    calls = []
    monkeypatch.setattr(gateway, 'main', lambda args: calls.append(args) or 0)
    assert launcher.main(['--repository-root', '/explicit/root']) == 0
    assert calls == [['--hook', 'UserPromptSubmit', '--repository-root', '/explicit/root']]


@pytest.mark.parametrize('command', [
    ['-m', 'hooks.gateway', '--hook', 'UserPromptSubmit'],
    [str(ROOT / 'hooks/user_prompt_submit.py')],
])
def test_package_and_outer_launcher_keep_empty_failure_protocol(command):
    result = subprocess.run([sys.executable, *command], input='{}', text=True,
                            capture_output=True, timeout=15,
                            env={**os.environ, 'PYTHONPATH': os.pathsep.join(
                                [str(ROOT / 'src'), os.environ.get('PYTHONPATH', '')])})
    assert result.returncode == 0
    assert result.stdout == ''
    assert 'invalid_field' in result.stderr
