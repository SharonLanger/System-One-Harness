"""Append-only local debugging. No stdout output or logging configuration."""
from datetime import datetime
from contextlib import contextmanager
from contextvars import ContextVar
import json
import os
from pathlib import Path
import traceback

LOG_PATH = Path(__file__).resolve().parents[1] / "logs" / "debug.jsonl"
_record_sink = ContextVar('harness_log_sink', default=None)


@contextmanager
def capture_records(sink):
    """Route this context's records to a callable, without opening the log file."""
    token = _record_sink.set(sink)
    try:
        yield
    finally:
        _record_sink.reset(token)


def log(level, component, event, *, error=None, raise_on_error=False, **details):
    """Best-effort JSONL; capture exceptions before callers convert them to no-ops."""
    try:
        record = {
            "time": datetime.now().astimezone().isoformat(timespec="milliseconds"),
            "level": level, "pid": os.getpid(), "parent_pid": os.getppid(),
            "component": component, "event": event, "details": details,
        }
        if error is not None:
            record["error"] = {
                "type": type(error).__name__, "message": str(error),
                "traceback": "".join(traceback.format_exception(type(error), error, error.__traceback__)),
            }
        try:
            line = json.dumps(record, ensure_ascii=True, allow_nan=False, default=repr)
        except (ValueError, TypeError):
            record["details"] = {"representation": repr(details), "valid_json": False}
            line = json.dumps(record, ensure_ascii=True, allow_nan=False, default=repr)
        sink = _record_sink.get()
        if sink is not None:
            sink(record)
            return
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except TimeoutError:
        # Preserve the hook deadline if its signal interrupts logging.
        raise
    except Exception:
        if raise_on_error:
            raise
        # Debugging must not replace a flow result or corrupt hook stdout.
        pass

