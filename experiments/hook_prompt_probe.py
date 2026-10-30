"""Replay a simple context response, or use --hook to receive Claude's stdin."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

from support import allocate_result_dir, start_record, write_report
from laya_context_router.log_utils import log

HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "inputs/hook_prompt_probe.json"


def make_response(event, additional_context):
    """Return context for UserPromptSubmit without a model or selection rules."""
    if not isinstance(event, dict) or event.get("hook_event_name") != "UserPromptSubmit":
        raise ValueError("expected a UserPromptSubmit event")
    if not isinstance(event.get("prompt"), str) or not isinstance(event.get("cwd"), str):
        raise ValueError("event needs string prompt and cwd fields")
    if not isinstance(additional_context, str) or not additional_context.strip():
        raise ValueError("additional_context must be a nonempty string")
    return {"hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": additional_context,
    }}


def main(argv=None):
    # Log before argument parsing, config loading, or waiting for Claude's stdin.
    log("INFO", "hook_prompt_probe", "invoked")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hook", action="store_true", help="read real event JSON from stdin; emit protocol JSON only")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args(argv)
    stamp = datetime.now().astimezone()
    details = {"run": start_record("hook_prompt_probe.py", "make_response", "live-hook" if args.hook else "synthetic-replay"),
               "config_path": str(args.config.resolve()), "event": None,
               "additional_context": None, "hook_response": None, "error": None}
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        if args.hook:
            text = sys.stdin.read(65537)
            if len(text) > 65536:
                raise ValueError("hook input exceeds 65536 characters")
            event = json.loads(text)
        else:
            event = config["replay_event"]
            if isinstance(event, dict) and event.get("cwd") == "__REPOSITORY_ROOT__":
                event["cwd"] = str(HERE.parent)
        details["event"] = event
        details["additional_context"] = config["additional_context"]
        log("INFO", "hook_prompt_probe", "received", event_input=event)
        response = make_response(event, config["additional_context"])
        details["hook_response"] = response
        details["run"]["status"] = "completed"
    except Exception as exc:
        details["error"] = {"type": type(exc).__name__, "message": str(exc)}
        log("ERROR", "hook_prompt_probe", "failed", error=exc)

    details["run"]["duration_seconds"] = round((datetime.now().astimezone() - stamp).total_seconds(), 3)
    summary = ("# Prompt hook connection probe\n\n"
               f"Mode: {details['run']['execution_mode']}. Outcome: {details['run']['status']}.\n\n"
               "This probe returns configured context. It does not call Laya, load questions, apply rules, or extract code.\n\n"
               f"Context: {details['additional_context']}\n\n"
               f"Error: {details['error'] or 'none'}.\n")
    out = None
    try:
        out = allocate_result_dir(HERE / "results/hook_prompt_probe", stamp)
        details["run"]["result_directory"] = str(out)
        write_report(out, details, summary)
    except Exception as exc:
        log("ERROR", "hook_prompt_probe", "report_failed", error=exc)
        print(f"Hook probe could not save report: {exc}", file=sys.stderr)

    if args.hook:
        if details["hook_response"] is not None:
            log("INFO", "hook_prompt_probe", "emitting_context", response=details["hook_response"])
            print(json.dumps(details["hook_response"], ensure_ascii=False))
        else:
            print(f"Hook probe failed: {details['error']}", file=sys.stderr)
        # Never block the user's prompt when the debugging probe fails.
        return 0
    print(summary)
    print(json.dumps(details["hook_response"], indent=2, ensure_ascii=False))
    if out is not None:
        print(f"Saved: {out}")
    return 0 if details["error"] is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
