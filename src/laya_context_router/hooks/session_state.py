"""Bounded Python-to-Node adapter; the TypeScript store owns persistence."""
from contextlib import contextmanager
import fcntl
import json
import re
import shutil
import subprocess
from pathlib import Path
from time import monotonic, sleep

ROOT = Path(__file__).resolve().parents[3]


class _Bridge:
    def __init__(self, session_id, deadline, logs_root, node, helper):
        if not isinstance(session_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', session_id):
            raise ValueError('invalid_session_id')
        self.root = Path(logs_root) if logs_root is not None else ROOT / 'logs'
        self.helper = Path(helper) if helper is not None else ROOT / 'build/typescript/session-state-cli.js'
        self.node = node or shutil.which('node')
        self.session_id, self.deadline = session_id, deadline
        if not self.node:
            raise FileNotFoundError('session_state_node_missing')
        if not self.helper.is_file():
            raise FileNotFoundError('session_state_build_missing')

    def remaining(self):
        value = self.deadline - monotonic()
        if value <= 0:
            raise TimeoutError('session_state_deadline')
        return value

    @contextmanager
    def locked(self):
        self.remaining()
        lock_dir = self.root / 'session-state-locks'
        lock_dir.mkdir(parents=True, exist_ok=True)
        with (lock_dir / (self.session_id + '.lock')).open('a') as lock:
            while True:
                self.remaining()
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    sleep(min(0.02, self.remaining()))
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def call(self, operation, event=None):
        request = {'logsRoot': str(self.root.resolve()), 'sessionId': self.session_id}
        if operation == 'load':
            request['operation'] = 'load'
        else:
            request['event'] = event
        encoded = json.dumps(request, allow_nan=False)
        self.remaining()
        process = subprocess.Popen([str(self.node), str(self.helper)], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            try:
                stdout, stderr = process.communicate(encoded, timeout=self.remaining())
            except subprocess.TimeoutExpired as exc:
                raise TimeoutError('session_state_deadline') from exc
            if process.returncode:
                raise RuntimeError('session_state_' + operation + '_failed: ' + stderr[:1000])
            if operation == 'load':
                try:
                    response = json.loads(stdout)
                except (ValueError, TypeError) as exc:
                    raise RuntimeError('session_state_invalid_response') from exc
                if (not isinstance(response, dict) or set(response) != {'events'}
                        or not isinstance(response['events'], list)
                        or not all(isinstance(e, dict) for e in response['events'])):
                    raise RuntimeError('session_state_invalid_response')
                return response['events']
            if stdout:
                raise RuntimeError('session_state_unexpected_output')
        except BaseException:
            if process.poll() is None:
                process.kill()
            process.communicate()
            raise


def save_event(session_id, event, *, deadline, logs_root=None, node=None, helper=None):
    bridge = _Bridge(session_id, deadline, logs_root, node, helper)
    with bridge.locked():
        bridge.call('save', event)


def inspect_and_save_event(session_id, decide, *, deadline, logs_root=None, node=None, helper=None):
    """Read, decide once, and optionally append under the cooperating session lock."""
    bridge = _Bridge(session_id, deadline, logs_root, node, helper)
    with bridge.locked():
        history = bridge.call('load')
        result = decide(history)
        if not isinstance(result, tuple) or len(result) != 2:
            raise ValueError('invalid_session_state_decision')
        decision, event = result
        allow = getattr(decision, 'allow', None)
        if type(allow) is not bool or (allow and not isinstance(event, dict)) or (not allow and event is not None):
            raise ValueError('invalid_session_state_decision')
        bridge.remaining()
        if allow:
            bridge.call('save', event)
        return decision
