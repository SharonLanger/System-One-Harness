"""Replay a saved UserPromptSubmit event through the existing hook subprocess."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
from support import allocate_result_dir, start_record, write_report
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
                  "ambiguous_candidates", "input_budget_exceeded", "invalid_reference"}
        return "noop" if reason in benign else "technical_error"
    return "technical_error"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="saved hook event JSON")
    parser.add_argument("--deadline", type=float, default=10.0, help="hook deadline in seconds (default: 10)")
    args = parser.parse_args(argv)
    stamp, started = datetime.now().astimezone(), datetime.now().astimezone()
    details = {"run": start_record("hook_user_prompt_submit.py", "hooks/user_prompt_submit.py subprocess", "real"),
               "input_path": str(args.input), "event": None, "exit_code": None,
               "stdout": "", "stderr": "", "parsed_output": None, "observed_status": "technical_error",
               "deadline_seconds": args.deadline, "error": None}
    try:
        if not 0 < args.deadline <= 290: raise ValueError("deadline must be greater than 0 and at most 290 seconds")
        event = json.loads(args.input.read_text())
        if not isinstance(event, dict): raise ValueError("event must be a JSON object")
        if event.get("cwd") == "__REPOSITORY_ROOT__": event["cwd"] = str(ROOT)
        details["event"] = event
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
        proc = subprocess.run([sys.executable, str(ROOT / "hooks/user_prompt_submit.py"),
                               "--repository-root", str(ROOT), "--real", "--deadline", str(args.deadline)],
                              input=json.dumps(event), text=True, capture_output=True,
                              timeout=args.deadline + 10, cwd=ROOT, env=env)
        details.update(exit_code=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)
        if proc.stdout.strip():
            try:
                decoded = json.loads(proc.stdout)
                details["parsed_output"] = decoded
            except json.JSONDecodeError:
                decoded = None
                details["error"] = {"type": "InvalidJSON", "message": "hook stdout was not valid JSON"}
        else:
            decoded = None
        specific = decoded.get("hookSpecificOutput") if isinstance(decoded, dict) else None
        if decoded is not None and not (isinstance(specific, dict) and isinstance(specific.get("additionalContext"), str)):
            details["error"] = {"type": "InvalidOutputShape", "message": "hook stdout did not contain hookSpecificOutput"}
        details["observed_status"] = classify(proc.stderr, decoded)
        if details["error"] is not None: details["observed_status"] = "technical_error"
        if proc.returncode != 0: details["observed_status"] = "technical_error"
    except subprocess.TimeoutExpired as exc:
        details["stdout"] = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        details["stderr"] = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        details["observed_status"] = "technical_error"
        details["error"] = {"type": "TimeoutExpired", "message": f"hook subprocess exceeded {args.deadline + 10:g} seconds"}
    except Exception as exc:
        details["observed_status"] = "technical_error"
        details["error"] = {"type": type(exc).__name__, "message": str(exc)}
    details["run"]["status"] = "failed" if details["observed_status"] == "technical_error" else "completed"
    details["run"]["duration_seconds"] = round((datetime.now().astimezone() - started).total_seconds(), 3)
    out = allocate_result_dir(HERE / "results/hook_user_prompt_submit", stamp)
    details["run"]["result_directory"] = str(out)
    output = details.get("parsed_output")
    specific = output.get("hookSpecificOutput") if isinstance(output, dict) else None
    context = specific.get("additionalContext") if isinstance(specific, dict) else None
    excerpt = str(context)[:500] if context else details.get("stderr", "").strip()[:500]
    summary = (f"# UserPromptSubmit replay\n\nObserved outcome: `{details['observed_status']}`; exit code: `{details['exit_code']}`.\n\n"
               f"Context excerpt or no-op/error reason: {excerpt or '(none)'}\n\n"
               "Only the placeholder cwd is replaced. A captured cwd outside this repository is preserved and the hook may no-op. This replay does not install or activate Claude hooks.\n")
    write_report(out, details, summary)
    print(summary, end="")
    print(f"Saved: {out}")
    return 1 if details["run"]["status"] == "failed" else 0

if __name__ == "__main__": raise SystemExit(main())
