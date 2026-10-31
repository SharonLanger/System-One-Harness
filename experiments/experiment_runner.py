"""Shared runner for direct Laya SDK experiments."""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sys
import time

# Also work when this helper is opened directly from an IDE. The experiment
# entry points add this path themselves, but direct execution starts here.
HERE = Path(__file__).resolve().parent
REPO_SRC = HERE.parent / "src"
if str(REPO_SRC) not in sys.path:
    sys.path.insert(0, str(REPO_SRC))

from laya_context_router.laya.config import RunConfig
from laya_context_router.laya.predict import predict
from laya_context_router.laya.registry import AgentRegistry
from support import ObservingRegistry, allocate_result_dir, json_safe, start_record, write_report
from summary import render_summary


def execute(stem, label, input_path, *, loader=None, inspection_provider=None, registry=None, model=None,
            temperature=None, temperature_set=False, lang=None, output_root=None,
            printer=print, compare_model=None, compare_temperature=None,
            compare_temperature_set=False, compare_lang=None):
    started, stamp = time.monotonic(), datetime.now().astimezone()
    record = start_record(f"{stem}.py", "laya_context_router.laya.predict.predict", "real" if loader is None and registry is None else "injected")
    details = {"run": record, "input": None, "questions": None,
               "model_config": {"requested": None, "observed": "not_exposed"},
               "raw_response": None, "processing": {"enrichment": "not_run", "rules": "not_run"},
               "result": None, "error": None}
    observer = None
    first_raw_response = None
    comparison_started = False
    stage = "input"
    printer(f"Starting {label} experiment")
    try:
        payload = json.loads(Path(input_path).read_text())
        if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
            raise ValueError("input must contain text as a string")
        questions = payload.get("questions")
        if not isinstance(questions, dict) or not questions:
            raise ValueError("input must contain a nonempty questions object")
        cfgdata = payload.get("config", {})
        if not isinstance(cfgdata, dict):
            raise ValueError("config must be an object")
        if model is not None: cfgdata["model"] = model
        if temperature_set: cfgdata["temperature"] = temperature
        if lang is not None: cfgdata["lang"] = lang
        config = RunConfig.from_dict(cfgdata)
        details["input"], details["questions"] = payload["text"], questions
        requested = {"model": config.model, "temperature": config.temperature, "lang": config.lang}
        details["model_config"]["requested"] = requested
        printer(f"Requested model: {config.model}")
        printer(f"Requested temperature: {config.temperature if config.temperature is not None else 'SDK default'}")
        printer(f"Requested language: {config.lang}")
        if registry is None: registry = AgentRegistry(inspection_provider=inspection_provider, loader=loader, real=(loader is None))
        elif loader is not None or inspection_provider is not None: raise ValueError("pass either registry or loader, not both")
        observer = ObservingRegistry(registry)
        stage = "load"
        printer("Loading or reusing agent")
        first_agent = registry.get_agent(config)
        stage = "inference"
        printer("Sending question payload")
        response = predict(payload["text"], questions, config=config, registry=observer)
        first_raw_response = json_safe(observer.raw_response)
        details["raw_response"] = first_raw_response
        details["result"] = response.get("answers")
        results = [{"configuration": requested, "response": response}]

        if stem == "laya_compare_models":
            compare_cfg_data = payload.get("comparison_config")
            if compare_cfg_data is None:
                compare_cfg_data = dict(cfgdata)
            elif not isinstance(compare_cfg_data, dict):
                raise ValueError("comparison_config must be an object or null")
            if compare_model is not None: compare_cfg_data["model"] = compare_model
            if compare_temperature_set: compare_cfg_data["temperature"] = compare_temperature
            if compare_lang is not None: compare_cfg_data["lang"] = compare_lang
            compare_cfg = RunConfig.from_dict(compare_cfg_data)
            compare_requested = {"model": compare_cfg.model, "temperature": compare_cfg.temperature, "lang": compare_cfg.lang}
            details["model_config"]["comparison_requested"] = compare_requested
            comparison_started = True
            observer.raw_response = None
            comparison_agent = registry.get_agent(compare_cfg)
            same_agent = comparison_agent is first_agent
            details["model_config"]["same_agent_object_reused"] = same_agent
            printer(f"Same agent object reused: {same_agent}")
            printer(f"Comparison model: {compare_cfg.model}")
            printer(f"Comparison temperature: {compare_cfg.temperature if compare_cfg.temperature is not None else 'SDK default'}")
            printer("Sending the same questions with comparison configuration")
            response2 = predict(payload["text"], questions, config=compare_cfg, registry=observer)
            results.append({"configuration": compare_requested, "response": response2})
            details["raw_response"] = [json_safe(x) for x in (details["raw_response"], observer.raw_response)]
            details["result"] = [x["response"].get("answers") for x in results]
        details["run"]["status"] = "success"
        printer("Received response")
        printer(f"Raw response: {json.dumps(details['raw_response'], ensure_ascii=False)}")
        printer(f"Outcome: {json.dumps(details['result'], ensure_ascii=False)}")
    except Exception as exc:
        if observer is not None and observer.raw_response is not None:
            latest_raw = json_safe(observer.raw_response)
            if comparison_started and first_raw_response is not None:
                details["raw_response"] = [first_raw_response, latest_raw]
            elif details["raw_response"] is None:
                details["raw_response"] = latest_raw
        details["error"] = {"stage": stage, "type": type(exc).__name__, "message": str(exc)}
        record["status"] = "failed"
        printer(f"ERROR during {stage}: {type(exc).__name__}: {exc}")
    record["duration_seconds"] = round(time.monotonic() - started, 3)
    try:
        out_root = Path(output_root) if output_root else Path(__file__).resolve().parent / "results" / stem
        out_dir = allocate_result_dir(out_root, stamp)
        record["result_directory"] = str(out_dir)
        summary = render_summary(details)
        write_report(out_dir, details, summary)
        printer(f"Saved summary: {out_dir / 'summary.md'}")
        printer(f"Saved details: {out_dir / 'details.json'}")
    except Exception as exc:
        printer(f"ERROR saving results: {type(exc).__name__}: {exc}")
        return 1
    return 0 if record["status"] == "success" else 1


if __name__ == "__main__":
    print("This is a shared helper. Run laya_choice.py, laya_noul.py, "
          "laya_score.py, laya_multiple_questions.py, or laya_compare_models.py instead.")
