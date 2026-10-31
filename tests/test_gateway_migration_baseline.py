"""Public hook wrapper rejects invalid payloads and ignores unrelated events."""
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
