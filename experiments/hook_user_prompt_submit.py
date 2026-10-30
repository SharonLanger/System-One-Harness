"""Replay a saved UserPromptSubmit event through the existing hook subprocess."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
from support import LOG_PATH, log, allocate_result_dir, start_record, write_report
from hook_trace import read_trace, collect_calls, render_summary, gateway_outcome
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_INPUT = HERE / "inputs/hook_user_prompt_submit.json"


def classify(stderr, decoded):
    specific = decoded.get("hookSpecificOutput") if isinstance(decoded, dict) else None
    if isinstance(specific, dict) and isinstance(specific.get("additionalContext"), str):
        return "context"
    if decoded is not None: return "technical_error"
    if not stderr.strip(): return "technical_error"
    prefix = "laya hook noop:"
    noop_line = next((line.strip() for line in reversed(stderr.splitlines()) if prefix in line), None)
    if noop_line is not None:
        reason = noop_line.split(prefix, 1)[1].strip()
        benign = {"missing", "not_file", "ambiguous", "inaccessible", "outside_repository",
                  "no_file", "multiple_files", "unsupported_request", "ineligible_request", "excluded",
                  "method_undecided", "no_single_match", "multiple_undecided", "multiple_relevant",
                  "ambiguous_candidates", "input_budget_exceeded", "candidate_budget_exceeded"}
        return "noop" if reason in benign else "technical_error"
    return "technical_error"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="saved hook event JSON")
    parser.add_argument("--deadline", type=float, default=10.0, help="hook deadline in seconds (default: 10)")
    parser.add_argument("--config", type=Path, help="optional RunConfig JSON passed to the real hook")
    args = parser.parse_args(argv)
    stamp, started = datetime.now().astimezone(), datetime.now().astimezone()
    details = {"run": start_record("hook_user_prompt_submit.py", "laya_context_router.hooks.gateway subprocess", "real"),
               "input_path": str(args.input), "event": None, "exit_code": None,
               "stdout": "", "stderr": "", "parsed_output": None, "observed_status": "technical_error",
               "deadline_seconds": args.deadline, "error": None, "hook_pid": None,
               "trace": [], "trace_warnings": [], "laya_calls": [],
               "config_path": str(args.config.resolve()) if args.config else None}
    log_offset = 0
    try:
        if not 0 < args.deadline <= 290: raise ValueError("deadline must be greater than 0 and at most 290 seconds")
        event = json.loads(args.input.read_text())
        if not isinstance(event, dict): raise ValueError("event must be a JSON object")
        if event.get("cwd") == "__REPOSITORY_ROOT__": event["cwd"] = str(ROOT)
        details["event"] = event
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
        command = [sys.executable, "-m", "laya_context_router.hooks.gateway", "--hook", "UserPromptSubmit",
                   "--repository-root", str(ROOT), "--real", "--deadline", str(args.deadline)]
        if args.config:
            command.extend(["--config", str(args.config.resolve())])
        try:
            log_offset = LOG_PATH.stat().st_size
        except FileNotFoundError:
            pass
        except OSError as exc:
            details["trace_warnings"].append(f"Could not locate log start: {exc}")
        log("INFO", "hook_replay", "launching", command=command, event_input=event)
        print(f"Starting real hook replay. Debug log: {LOG_PATH}", flush=True)
        with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, cwd=ROOT, env=env) as proc:
            details["hook_pid"] = proc.pid
            log("INFO", "hook_replay", "child_started", hook_pid=proc.pid)
            print(f"Hook PID: {proc.pid}. Full questions and responses will print when it finishes.", flush=True)
            try:
                stdout, stderr = proc.communicate(json.dumps(event), timeout=args.deadline + 10)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
                details.update(exit_code=proc.returncode, stdout=stdout, stderr=stderr)
                raise
            details.update(exit_code=proc.returncode, stdout=stdout, stderr=stderr)
        if stdout.strip():
            try:
                decoded = json.loads(stdout)
                details["parsed_output"] = decoded
            except json.JSONDecodeError:
                decoded = None
                details["error"] = {"type": "InvalidJSON", "message": "hook stdout was not valid JSON"}
        else:
            decoded = None
        specific = decoded.get("hookSpecificOutput") if isinstance(decoded, dict) else None
        if decoded is not None and not (isinstance(specific, dict) and isinstance(specific.get("additionalContext"), str)):
            details["error"] = {"type": "InvalidOutputShape", "message": "hook stdout did not contain hookSpecificOutput"}
        details["observed_status"] = classify(stderr, decoded)
        if details["error"] is not None: details["observed_status"] = "technical_error"
        if proc.returncode != 0: details["observed_status"] = "technical_error"
    except subprocess.TimeoutExpired as exc:
        details["observed_status"] = "technical_error"
        details["error"] = {"type": "TimeoutExpired", "message": f"hook subprocess exceeded {args.deadline + 10:g} seconds"}
    except Exception as exc:
        details["observed_status"] = "technical_error"
        details["error"] = {"type": type(exc).__name__, "message": str(exc)}
    trace, warnings = read_trace(LOG_PATH, log_offset, details["hook_pid"])
    details["trace"] = trace
    details["trace_warnings"].extend(warnings)
    details["laya_calls"] = collect_calls(trace)
    final=gateway_outcome(details)
    details['application_outcome']=final or None
    if final and details['error'] is None and details['exit_code']==0:
        if final.get('outcome')=='error':details['observed_status']='technical_error'
        elif final.get('outcome')=='noop' and not details['stdout']:details['observed_status']='noop'
        elif final.get('outcome')!='context' or details['parsed_output'] is None:
            details['observed_status']='technical_error' 
    details["run"]["status"] = "failed" if details["observed_status"] == "technical_error" else "completed"
    details["run"]["duration_seconds"] = round((datetime.now().astimezone() - started).total_seconds(), 3)
    out = allocate_result_dir(HERE / "results/hook_user_prompt_submit", stamp)
    details["run"]["result_directory"] = str(out)
    summary = render_summary(details)
    (out / "trace.jsonl").write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in trace), encoding="utf-8")
    write_report(out, details, summary)
    print(summary, end="")
    print(f"Saved: {out}")
    return 1 if details["run"]["status"] == "failed" else 0

if __name__ == "__main__": raise SystemExit(main())
