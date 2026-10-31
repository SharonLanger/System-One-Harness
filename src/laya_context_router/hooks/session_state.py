"""Bounded Python-to-Node adapter; the TypeScript store owns persistence."""
import fcntl
import json
import re
import shutil
import subprocess
from pathlib import Path
from time import monotonic, sleep

ROOT = Path(__file__).resolve().parents[3]


def save_event(session_id, event, *, deadline, logs_root=None, node=None, helper=None):
    if not isinstance(session_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', session_id):
        raise ValueError('invalid_session_id')
    root = Path(logs_root) if logs_root is not None else ROOT / 'logs'
    helper = Path(helper) if helper is not None else ROOT / 'build/typescript/session-state-cli.js'
    node = node or shutil.which('node')
    if not node:
        raise FileNotFoundError('session_state_node_missing')
    if not helper.is_file():
        raise FileNotFoundError('session_state_build_missing')
    def remaining():
        value = deadline - monotonic()
        if value <= 0:
            raise TimeoutError('session_state_deadline')
        return value
    remaining()
    lock_dir = root / 'session-state-locks'
    lock_dir.mkdir(parents=True, exist_ok=True)
    with (lock_dir / (session_id + '.lock')).open('a') as lock:
        while True:
            remaining()
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                sleep(min(0.02, remaining()))
        try:
            request = json.dumps({'logsRoot': str(root.resolve()), 'sessionId': session_id,
                                  'event': event}, allow_nan=False)
            process = subprocess.Popen([str(node), str(helper)], stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                stdout, stderr = process.communicate(request, timeout=remaining())
                if process.returncode:
                    raise RuntimeError('session_state_write_failed: ' + stderr[:1000])
                if stdout:
                    raise RuntimeError('session_state_unexpected_output')
            except BaseException:
                if process.poll() is None:
                    process.kill()
                process.communicate()
                raise
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
