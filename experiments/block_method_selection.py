"""Run the existing method-selection building block on a synthetic outline."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
REPO_SRC = HERE.parent / "src"
if str(REPO_SRC) not in sys.path:
    sys.path.insert(0, str(REPO_SRC))

from answers.enrich import enrich_response
from building_blocks.questions.method_selection.block import run as run_block
from laya.config import RunConfig
from laya.registry import AgentRegistry
from support import allocate_result_dir, json_safe, start_record, write_report
from block_method_selection_summary import render_summary

INPUT_PATH = HERE / "inputs" / "block_method_selection.json"


class CapturingRegistry:
    """Observe the single SDK-bound prediction without adding a model call."""
    def __init__(self, registry, details):
        self.registry = registry
        self.details = details

    def get_agent(self, config):
        agent = self.registry.get_agent(config)
        owner = self

        class CapturingAgent:
            def predict(self, text, questions, **kwargs):
                owner.details["submitted_text"] = text
                owner.details["submitted_questions"] = json_safe(questions)
                owner.details["predict_kwargs"] = json_safe(kwargs)
                raw = agent.predict(text, questions, **kwargs)
                owner.details["raw_response"] = json_safe(raw)
                return raw

        return CapturingAgent()


def run(*, input_path=INPUT_PATH, loader=None, registry=None, model=None,
        temperature=None, temperature_set=False, lang=None, output_root=None,
        printer=print):
    started = time.monotonic()
    stamp = datetime.now().astimezone()
    mode = "real" if loader is None and registry is None else "injected"
    details = {
        "run": start_record("block_method_selection.py", "method_selection.block.run", mode),
        "input": None,
        "source_outline": None,
        "submitted_text": None,
        "submitted_questions": None,
        "predict_kwargs": None,
        "model_config": {"requested": None, "observed": "not_exposed"},
        "raw_response": None,
        "enriched_response": None,
        "result": None,
        "error": None,
    }
    stage = "input"
    printer("Starting method-selection block experiment (synthetic outline)")
    try:
        payload = json.loads(Path(input_path).read_text())
        if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
            raise ValueError("input must contain text as a string")
        outline = payload.get("source_outline")
        if not isinstance(outline, dict) or not isinstance(outline.get("callables"), list):
            raise ValueError("input must contain source_outline.callables")
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
        details["input"] = payload["text"]
        details["source_outline"] = outline
        details["model_config"] = {
            "requested": {"model": config.model, "temperature": config.temperature, "lang": config.lang},
            "observed": "not_exposed",
        }
        if registry is not None and loader is not None:
            raise ValueError("pass either registry or loader, not both")
        if registry is None:
            registry = AgentRegistry(loader=loader, real=(loader is None))
        observer = CapturingRegistry(registry, details)
        stage = "block"
        printer(f"Requested model: {config.model}")
        printer(f"Requested temperature: {config.temperature if config.temperature is not None else 'SDK default'}")
        printer("Running existing method-selection block")
        result = run_block(payload["text"], outline, config=config, registry=observer)
        details["result"] = json_safe(result)
        if details["raw_response"] is not None:
            try:
                details["enriched_response"] = json_safe(enrich_response(details["raw_response"]))
            except Exception as exc:
                details["enrichment_error"] = {"type": type(exc).__name__, "message": str(exc)}
        details["run"]["status"] = "success"
        printer(f"Block result: {json.dumps(json_safe(result), ensure_ascii=False)}")
    except Exception as exc:
        details["error"] = {"stage": stage, "type": type(exc).__name__, "message": str(exc)}
        details["run"]["status"] = "failed"
        printer(f"ERROR during {stage}: {type(exc).__name__}: {exc}")
    details["run"]["duration_seconds"] = round(time.monotonic() - started, 3)
    try:
        out_root = Path(output_root) if output_root else HERE / "results" / "block_method_selection"
        out_dir = allocate_result_dir(out_root, stamp)
        details["run"]["result_directory"] = str(out_dir)
        write_report(out_dir, details, render_summary(details))
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
