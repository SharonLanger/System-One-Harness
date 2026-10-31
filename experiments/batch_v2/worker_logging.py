"""Bounded error diagnostics for experiment workers; no production logging changes."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import traceback

MAX_BYTES = 1024 * 1024
BACKUPS = 2
POLICY = {'level': 'ERROR', 'max_file_bytes': MAX_BYTES, 'backup_files': BACKUPS,
          'embedded_traces': False, 'record_text_limit': 2048}


class ErrorLog:
    def __init__(self, path, max_bytes=MAX_BYTES, backups=BACKUPS):
        self.path = Path(path)
        self.max_bytes = max_bytes
        self.backups = backups
        self.context = {}

    def __call__(self, level, component, event, *, error=None, raise_on_error=False, **details):
        if level not in ('ERROR', 'CRITICAL', 'FATAL') and error is None:
            return
        try:
            record = {'time': datetime.now(timezone.utc).isoformat(), 'level': str(level)[:40],
                      'component': str(component)[:120], 'event': str(event)[:120],
                      'context': dict(self.context)}
            # Payloads and predictions already have authoritative checkpoints. Do not
            # duplicate arbitrary details, full prompts or probability arrays here.
            if error is not None:
                record['error'] = {'type': type(error).__name__, 'message': str(error)[:2048],
                                   'traceback': ''.join(traceback.format_tb(error.__traceback__))[-2048:]}
            line = (json.dumps(record, ensure_ascii=True, separators=(',', ':')) + '\n').encode()
            if len(line) > self.max_bytes:
                line = (json.dumps({'level': 'ERROR', 'event': 'oversized_error_record',
                                    'message': 'See the case/inference checkpoint for details.'}) + '\n').encode()
            if len(line) > self.max_bytes:
                return
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self.path.exists() and self.path.stat().st_size + len(line) > self.max_bytes:
                for index in range(self.backups, 0, -1):
                    source = self.path if index == 1 else Path(str(self.path) + f'.{index-1}')
                    if source.exists():
                        source.replace(Path(str(self.path) + f'.{index}'))
                if self.backups == 0:
                    self.path.unlink()
            with self.path.open('ab') as stream:
                stream.write(line)
        except TimeoutError:
            raise
        except Exception:
            if raise_on_error:
                raise


def _replace_aliases(old, new):
    # Production modules use `from log_utils import log`; cover modules imported
    # both before and during the scope, without patching any production files.
    for name, module in list(sys.modules.items()):
        if name.startswith('laya_context_router.') and module is not None:
            if getattr(module, 'log', None) is old:
                module.log = new


@contextmanager
def worker_errors(path):
    from laya_context_router import log_utils
    original = log_utils.log
    sink = ErrorLog(path)
    _replace_aliases(original, sink)
    try:
        yield sink
    finally:
        _replace_aliases(sink, original)
