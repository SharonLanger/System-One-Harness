"""Run the saved choice question against the real Laya adapter."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
import time

# Make the checkout's src layout available when this file is run directly from
# an IDE or by absolute path. This does not install or provide the Laya SDK.
HERE = Path(__file__).resolve().parent
REPO_SRC = HERE.parent / "src"
if str(REPO_SRC) not in sys.path:
    sys.path.insert(0, str(REPO_SRC))

from laya_context_router.laya.config import RunConfig
from laya_context_router.laya.predict import predict
from laya_context_router.laya.registry import AgentRegistry
from support import ObservingRegistry, allocate_result_dir, json_safe, start_record, write_report

INPUT_PATH = HERE / "inputs" / "laya_choice.json"


def run(*, input_path=INPUT_PATH, loader=None, registry=None, model=None,
        temperature=None, temperature_set=False, lang=None, output_root=None,
        printer=print):
    started = time.monotonic()
    stamp = datetime.now().astimezone()
    mode = "real" if loader is None and registry is None else "injected"
    record = start_record("laya_choice.py", "laya_context_router.laya.predict.predict", mode)
    details = {
        "run": record,
        "input": None,
        "questions": None,
        "model_config": {"requested": None, "observed": "not_exposed"},
        "raw_response": None,
        "processing": {"enrichment": "not_run", "rules": "not_run"},
        "result": None,
        "error": None,
    }
    observer = None
    stage = "input"
    printer("Starting Laya choice experiment")
    try:
        payload = json.loads(Path(input_path).read_text())
        if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
            raise ValueError("input must contain text as a string")
        if not isinstance(payload.get("questions"), dict):
            raise ValueError("input must contain a questions object")
        if not isinstance(payload.get("config", {}), dict):
            raise ValueError("config must be an object")
        cfg = dict(payload.get("config", {}))
        if model is not None:
            cfg["model"] = model
        if temperature_set:
            cfg["temperature"] = temperature
        if lang is not None:
            cfg["lang"] = lang
        config = RunConfig.from_dict(cfg)
        text = payload["text"]
        questions = payload["questions"]
        details["input"] = text
        details["questions"] = questions
        details["model_config"] = {
            "requested": {"model": config.model, "temperature": config.temperature, "lang": config.lang},
            "observed": "not_exposed",
        }
        printer(f"Requested model: {config.model}")
        printer(f"Requested temperature: {config.temperature if config.temperature is not None else 'SDK default'}")
        if registry is None:
            registry = AgentRegistry(loader=loader, real=(loader is None))
        elif loader is not None:
            raise ValueError("pass either registry or loader, not both")
        observer = ObservingRegistry(registry)
        stage = "load"
        printer("Loading or reusing agent")
        observer.get_agent(config)
        stage = "inference"
        printer("Sending choice question")
        response = predict(text, questions, config=config, registry=observer)
        details["raw_response"] = json_safe(observer.raw_response)
        answer = response["answers"].get(next(iter(questions)))
        details["result"] = {"answer": answer}
        details["run"]["status"] = "success"
        printer("Received response")
        printer(f"Raw response: {json.dumps(response, ensure_ascii=False)}")
        printer(f"Outcome: {json.dumps(answer, ensure_ascii=False)}")
    except Exception as exc:
        if observer is not None and observer.raw_response is not None:
            details["raw_response"] = json_safe(observer.raw_response)
        details["error"] = {"stage": stage, "type": type(exc).__name__, "message": str(exc)}
        details["run"]["status"] = "failed"
        printer(f"ERROR during {stage}: {type(exc).__name__}: {exc}")
    details["run"]["duration_seconds"] = round(time.monotonic() - started, 3)
    try:
        out_root = Path(output_root) if output_root else HERE / "results" / "laya_choice"
        out_dir = allocate_result_dir(out_root, stamp)
        details["run"]["result_directory"] = str(out_dir)
        requested = details["model_config"]["requested"]
        if requested is None:
            requested = {"model": "unavailable", "temperature": None, "lang": "unavailable"}
        summary = "\n".join([
            "# Laya choice experiment", "",
            f"- Status: **{details['run']['status']}**",
            f"- Started: {record['started_local']} ({record['timezone_offset']})",
            f"- UTC: {record['started_utc']}",
            f"- Requested model: `{requested['model']}`",
            f"- Requested temperature: {requested['temperature'] if requested['temperature'] is not None else 'SDK default'}",
            f"- Language: `{requested['lang']}`",
            f"- Input text: {details['input']!r}",
            f"- Questions: `{json.dumps(details['questions'], ensure_ascii=False)}`",
            f"- Response: `{json.dumps(details['raw_response'], ensure_ascii=False)}`",
            f"- Outcome: `{json.dumps(details['result'], ensure_ascii=False)}`",
            f"- Processing: enrichment {details['processing']['enrichment']}; rules {details['processing']['rules']}",
            f"- Duration: {details['run']['duration_seconds']} seconds",
            f"- Error: `{json.dumps(details['error'], ensure_ascii=False)}`",
        ])
        write_report(out_dir, details, summary)
        printer(f"Saved summary: {out_dir / 'summary.md'}")
        printer(f"Saved details: {out_dir / 'details.json'}")
    except Exception as exc:
        printer(f"ERROR saving results: {type(exc).__name__}: {exc}")
        return 1
    return 0 if details["run"]["status"] == "success" else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model")
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--lang")
    args = parser.parse_args(argv)
    return run(model=args.model, temperature=args.temperature,
               temperature_set=args.temperature is not None, lang=args.lang)


if __name__ == "__main__":
    raise SystemExit(main())
