"""Single synchronous command boundary. No model work at import time."""
import argparse
from contextlib import contextmanager, redirect_stdout
import json
import math
import os
import signal
import sys
from uuid import uuid4
from time import monotonic

from .contracts import Context, Noop, Failure, ValidationError, validate_result
from ..json_utils import _unique_pairs

MAX_INPUT_CHARS = 65536

class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValidationError('invalid_arguments', 'invocation', message)

def parse_args(argv):
    argv = list(sys.argv[1:] if argv is None else argv)
    if sum(x == '--hook' or x.startswith('--hook=') for x in argv) != 1:
        raise ValidationError('invalid_hook_argument', 'invocation', 'hook')
    p = Parser()
    p.add_argument('--hook', required=True)
    p.add_argument('--repository-root')
    p.add_argument('--config')
    p.add_argument('--real', action='store_true')
    p.add_argument('--deadline', type=float, default=10.0)
    p.add_argument('--max-context-chars', type=int, default=8000)
    p.add_argument('--max-dependency-depth', type=int, default=2)
    p.add_argument('--max-dependency-chars', type=int, default=12000)
    args = p.parse_args(argv)
    if not args.hook.strip():
        raise ValidationError('invalid_hook_argument', 'invocation', 'hook')
    if (not math.isfinite(args.deadline) or not 0 < args.deadline <= 300
            or args.max_context_chars <= 0 or not 0 <= args.max_dependency_depth <= 20
            or not 1 <= args.max_dependency_chars <= 1000000):
        raise ValidationError('invalid_budget', 'invocation')
    return args

def parse_payload(text, hook):
    if len(text) > MAX_INPUT_CHARS:
        raise ValidationError('input_budget_exceeded', 'input')
    try:
        payload = json.loads(text, object_pairs_hook=_unique_pairs,
                             parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (ValueError, TypeError) as exc:
        raise ValidationError('invalid_json', 'input') from exc
    if not isinstance(payload, dict):
        raise ValidationError('invalid_object', 'input')
    name = payload.get('hook_event_name')
    if not isinstance(name, str) or not name.strip():
        raise ValidationError('invalid_field', 'input', 'hook_event_name')
    if name != hook:
        raise ValidationError('event_mismatch', 'input', 'hook_event_name', command_hook=hook, payload_hook=name)
    return payload

def serialize_response(result, hook):
    validate_result(result)
    if not isinstance(result, Context):
        return ''
    return json.dumps({'hookSpecificOutput': {'hookEventName': hook,
                      'additionalContext': result.text}}, ensure_ascii=False,
                      allow_nan=False, separators=(',', ':')) + '\n'

@contextmanager
def isolate_stdout():
    sys.stdout.flush()
    saved = os.dup(1)
    try:
        os.dup2(2, 1)
        with redirect_stdout(sys.stderr):
            yield
    finally:
        try:
            sys.__stdout__.flush()
        finally:
            os.dup2(saved, 1)
            os.close(saved)

def _expired(signum, frame):
    raise TimeoutError('hook deadline exceeded')

def _default_dispatch(payload, args, invocation_id, logger):
    from .dispatcher import dispatch_hook
    from .project_context import enrich_project_context
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR')
    return dispatch_hook(payload, args, invocation_id, logger,
                         enricher=lambda envelope: enrich_project_context(envelope, project_dir, logger))

def _default_log(level, event, **details):
    from ..log_utils import log
    log(level, 'hook_gateway', event, raise_on_error=True, **details)

def main(argv=None, *, dispatcher=None, logger=None):
    started=monotonic()
    invocation_id=str(uuid4())
    log_impl=logger or _default_log
    args=None
    result=Failure('not_started','gateway')
    written=0
    timer_started=False
    previous_handler=None
    expired=False
    logging_disabled=False
    validated_session=None

    def expire(signum,frame):
        nonlocal expired
        expired=True
        raise TimeoutError('hook deadline exceeded')

    def log(level,event,**details):
        nonlocal validated_session
        if not timer_started or expired or logging_disabled:
            return
        if event=='common_input_validated':
            validated_session=details.get('session_id')
        metadata={'invocation_id':invocation_id,'hook_event_name':args.hook,
                  'session_id':validated_session,**details}
        try:
            with isolate_stdout():
                log_impl(level,event,**metadata)
        except TimeoutError:
            raise
        except Exception as exc:
            print(f'laya logging failed: {type(exc).__name__}',file=sys.stderr)

    def safe_log(level,event,**details):
        nonlocal logging_disabled
        try:
            log(level,event,**details)
        except TimeoutError:
            logging_disabled=True
            print(f'laya hook logging deadline exceeded [{invocation_id}]',file=sys.stderr)

    def recover_output():
        # Only used after a broken pipe or timeout interrupts protocol emission.
        try:
            null_fd=os.open(os.devnull,os.O_WRONLY)
            try:os.dup2(null_fd,1)
            finally:os.close(null_fd)
            sys.stdout.flush()
        except Exception:
            print('laya hook error: interrupted stdout cleanup failed',file=sys.stderr)

    try:
        try:
            with isolate_stdout():
                args=parse_args(argv)
                remaining=args.deadline-(monotonic()-started)
                if remaining<=0:
                    expired=True
                    raise TimeoutError('hook deadline exceeded during argument parsing')
                previous_handler=signal.signal(signal.SIGALRM,expire)
                signal.setitimer(signal.ITIMER_REAL,remaining)
                timer_started=True
                text=sys.stdin.read(MAX_INPUT_CHARS+1)
                payload=parse_payload(text,args.hook)
                log('INFO','gateway_received',input_chars=len(text),fields=sorted(payload))
                result=validate_result((dispatcher or _default_dispatch)(payload,args,invocation_id,log))
                if expired:
                    raise TimeoutError('hook deadline exceeded')
                output=serialize_response(result,args.hook)
                if isinstance(result,Failure):
                    log('ERROR','gateway_error',code=result.code,stage=result.stage,field=result.field)
                    print(f'laya hook error: {result.stage}: {result.code} {result.message}',file=sys.stderr)
                elif isinstance(result,Noop):
                    log('INFO','gateway_noop',reason=result.reason)
                    print(f'laya hook noop: {result.reason}',file=sys.stderr)
                if output:
                    log('DEBUG','response_prepared',serialized_bytes=len(output.encode('utf-8')))
            if output:
                written=None
                sys.stdout.write(output)
                sys.stdout.flush()
                written=len(output.encode('utf-8'))
        except (Exception,SystemExit) as exc:
            interrupted=written is None and isinstance(exc,(BrokenPipeError,TimeoutError))
            if interrupted:
                recover_output()
            if isinstance(exc,BrokenPipeError) and interrupted:
                result=Failure('stdout_write_failed','output',message=f'{type(exc).__name__}: {exc}')
            else:
                result=Failure(exc.code if isinstance(exc,ValidationError) else
                    ('deadline_exceeded' if isinstance(exc,TimeoutError) else 'gateway_error'),
                    getattr(exc,'stage','gateway'),getattr(exc,'field',None),f'{type(exc).__name__}: {exc}')
            safe_log('ERROR','gateway_error',code=result.code,stage=result.stage,field=result.field,
                     **getattr(exc,'evidence',{}))
            partial='; stdout_bytes_written=unknown' if written is None else ''
            print(f'laya hook error: {result.code}: {result.message}{partial} [{invocation_id}]',file=sys.stderr)
        safe_log('INFO','gateway_finished',outcome='error' if isinstance(result,Failure) else
            ('context' if isinstance(result,Context) else 'noop'),
            reason=result.reason if isinstance(result,Noop) else None,
            code=result.code if isinstance(result,Failure) else None,
            response_present=isinstance(result,Context) and bool(written),
            stdout_bytes_written=written,exit_code=0)
        return 0
    finally:
        if timer_started:
            signal.setitimer(signal.ITIMER_REAL,0)
            signal.signal(signal.SIGALRM,previous_handler)

if __name__=='__main__':
    raise SystemExit(main())
