#!/usr/bin/env python3
"""Opt-in POSIX command hook; protocol only, no installation or activation."""
import argparse
from contextlib import contextmanager, redirect_stdout
import json
import math
import os
from pathlib import Path
import signal
import sys

MAX_INPUT_CHARS = 65536
MAX_CONTEXT_CHARS = 8000


def _log(level, event, **details):
    # Preserve the hook's handled no-op if the package is not installed.
    try:
        from laya_context_router.log_utils import log
    except ImportError:
        return
    log(level, 'hook', event, **details)


def _expired(signum, frame):
    raise TimeoutError('hook deadline exceeded')


@contextmanager
def _isolate_protocol_stdout():
    """Send Python and file-descriptor stdout chatter to stderr during work.

    Restore the original descriptor before writing the single hook response.
    This covers native writes to fd 1 as well as sys.__stdout__ writes in this
    synchronous process; uncontrolled background writers remain unverified.
    """
    sys.stdout.flush()
    saved_stdout = os.dup(1)
    try:
        os.dup2(2, 1)
        with redirect_stdout(sys.stderr):
            yield
    finally:
        try:
            sys.__stdout__.flush()
        finally:
            os.dup2(saved_stdout, 1)
            os.close(saved_stdout)


def main(argv=None):
    output = None
    previous_handler = None
    try:
        _log('INFO', 'invoked')
        # All Python and native SDK progress output belongs on stderr.
        with _isolate_protocol_stdout():
            parser = argparse.ArgumentParser(description=__doc__)
            parser.add_argument('--repository-root', required=True)
            parser.add_argument('--config')
            parser.add_argument('--real', action='store_true', help='explicit lazy live adapter opt-in; unverified until Phase20')
            parser.add_argument('--deadline', type=float, default=10.0)
            parser.add_argument('--max-context-chars', type=int, default=MAX_CONTEXT_CHARS,
                                help='warning threshold for formatted context; source is sent unchanged')
            parser.add_argument('--max-dependency-depth', type=int, default=2)
            parser.add_argument('--max-dependency-chars', type=int, default=12000)
            args = parser.parse_args(argv)
            if (not math.isfinite(args.deadline) or not 0 < args.deadline <= 300
                    or not 0 < args.max_context_chars
                    or not 0 <= args.max_dependency_depth <= 20
                    or not 1 <= args.max_dependency_chars <= 1000000):
                raise ValueError('invalid hook budget')
            previous_handler = signal.signal(signal.SIGALRM, _expired)
            signal.setitimer(signal.ITIMER_REAL, args.deadline)
            text = sys.stdin.read(MAX_INPUT_CHARS + 1)
            if len(text) > MAX_INPUT_CHARS:
                raise ValueError('input_budget_exceeded')
            from laya_context_router.json_utils import _unique_pairs
            event = json.loads(text, object_pairs_hook=_unique_pairs)
            if not isinstance(event, dict):
                raise ValueError('hook input must be an object')
            if not isinstance(event.get('hook_event_name'), str):
                raise ValueError('invalid hook_event_name')
            if event['hook_event_name'] != 'UserPromptSubmit':
                return 0
            if not isinstance(event.get('prompt'), str) or not isinstance(event.get('cwd'), str):
                raise ValueError('invalid prompt or cwd')
            root = Path(args.repository_root)
            cwd = Path(event['cwd'])
            if not root.is_absolute() or not cwd.is_absolute():
                raise ValueError('repository root and cwd must be absolute')
            root = root.resolve(strict=True)
            cwd = cwd.resolve(strict=True)
            if not root.is_dir() or not cwd.is_dir() or not cwd.is_relative_to(root):
                raise ValueError('cwd outside repository or not a directory')
            if not args.real:
                raise ValueError('model disabled: explicit --real required; live compatibility unverified')
            from laya_context_router.laya.config import RunConfig, load_config
            from laya_context_router.laya.registry import AgentRegistry
            from laya_context_router.flows.file_method_context import run
            config = load_config(args.config) if args.config else RunConfig()
            result = run(event['prompt'], cwd=cwd, repository_root=root, config=config,
                         registry=AgentRegistry(real=True), max_dependency_depth=args.max_dependency_depth,
                         max_dependency_chars=args.max_dependency_chars)
            if result['status'] != 'context':
                _log('INFO', 'noop', reason=result['reason'], response=None)
                print(f"laya hook noop: {result['reason']}", file=sys.stderr)
                return 0
            from laya_context_router.context_format import format_context
            context = format_context(result['context'], project_root=root)
            response = {'hookSpecificOutput': {
                'hookEventName': 'UserPromptSubmit', 'additionalContext': context}}
            _log('DEBUG', 'response_prepared', response=response,
                 context_chars=len(context), max_context_chars=args.max_context_chars)
            if len(context) > args.max_context_chars:
                _log('WARNING', 'context_size_warning',
                     context_chars=len(context), max_context_chars=args.max_context_chars,
                     action='send_unchanged')
            output = json.dumps(response,
                ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    except SystemExit:
        # argparse uses exit2 for errors, which would block the user's prompt.
        return 0
    except Exception as exc:
        _log('ERROR', 'failed', error=exc, returned_response=None)
        print(f'laya hook noop: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 0
    finally:
        if previous_handler is not None:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous_handler)
    if output is not None:
        print(output, flush=True)
        _log('INFO', 'response_emitted', response=response)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
