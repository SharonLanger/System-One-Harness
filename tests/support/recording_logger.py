"""Capture shared and hook diagnostics without creating log files."""
from contextlib import contextmanager

from log_utils import capture_records


class RecordingLogger:
    def __init__(self):
        self.records = []

    def __call__(self, level, event, **details):
        self.records.append({'level': level, 'event': event, 'details': details})

    @contextmanager
    def capture_shared(self):
        with capture_records(self.records.append):
            yield self
