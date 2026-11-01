"""Repeat one named choice question over a small explicit set of prompts."""
from datetime import datetime
import json
from pathlib import Path
import sys
import time
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))
from laya.config import RunConfig
from laya.predict import predict
from laya.registry import AgentRegistry
from support import ObservingRegistry, allocate_result_dir, json_safe, start_record, write_report
MAX_RUNS = 5


def choice_from(response):
    answer = response.get("answers", {}).get("fruit") if isinstance(response, dict) else None
    if isinstance(answer, dict): return answer.get("choice", answer.get("answer", json_safe(answer)))
    return answer


def main():
    started, stamp = time.monotonic(), datetime.now().astimezone()
    details = {"run": start_record("repeat_scenario.py", "laya.predict.predict repeated", "real"),
               "input": None, "requested_model_config": None, "named_question": None,
               "max_runs": MAX_RUNS, "same_registry_used": True, "outcomes": [], "aggregate": None, "error": None}
    try:
        payload = json.loads((HERE / "inputs/repeat_scenario.json").read_text())
        if not isinstance(payload, dict): raise ValueError("input must be an object")
        prompts, question = payload.get("prompts"), payload.get("question")
        if not isinstance(prompts, list) or not 1 <= len(prompts) <= MAX_RUNS or not all(isinstance(p, str) for p in prompts):
            raise ValueError(f"prompts must contain 1..{MAX_RUNS} strings")
        if not isinstance(question, dict): raise ValueError("question must be an object")
        details["input"] = payload
        config = RunConfig.from_dict(payload.get("config", {}))
        details["requested_model_config"] = {"model": config.model, "temperature": config.temperature, "lang": config.lang}
        details["named_question"] = {"fruit": question}
        observer = ObservingRegistry(AgentRegistry(real=True))
        for index, prompt in enumerate(prompts, 1):
            entry = {"index": index, "prompt": prompt, "raw_response": None, "result": None, "choice": None, "error": None}
            observer.raw_response = None
            try:
                response = predict(prompt, {"fruit": question}, config=config, registry=observer)
                entry["result"] = json_safe(response)
                entry["raw_response"] = json_safe(observer.raw_response)
                entry["choice"] = choice_from(response)
            except Exception as exc:
                entry["raw_response"] = json_safe(observer.raw_response) if observer.raw_response is not None else None
                entry["error"] = {"type": type(exc).__name__, "message": str(exc)}
            details["outcomes"].append(entry)
        successes = sum(item["error"] is None for item in details["outcomes"])
        details["aggregate"] = {"runs": len(details["outcomes"]), "responses_received": successes,
                                "errors": len(details["outcomes"]) - successes}
        details["run"]["status"] = "completed" if successes == len(details["outcomes"]) else "partial"
    except Exception as exc:
        details["error"] = {"type": type(exc).__name__, "message": str(exc)}
        details["run"]["status"] = "failed"
    details["run"]["duration_seconds"] = round(time.monotonic() - started, 3)
    aggregate = details["aggregate"] or {"runs": 0, "responses_received": 0, "errors": 1}
    lines = ["# Repeated scenario", "", f"Runs: {aggregate['runs']}; responses received: {aggregate['responses_received']}; errors: {aggregate['errors']}.", "",
             "Each prompt used the same named `fruit` choice question through the same registry instance.", "",
             "| Run | Prompt | Choice or error |", "|---:|---|---|"]
    for item in details["outcomes"]:
        value = f"error: {item['error']['type']}: {item['error']['message']}" if item["error"] else str(item["choice"])
        prompt_cell = item["prompt"].replace("|", "\\|").replace("\n", " ")
        value_cell = value.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {item['index']} | {prompt_cell} | {value_cell} |")
    if details["error"]: lines.extend(["", f"Experiment error: `{details['error']['type']}: {details['error']['message']}`."])
    out = allocate_result_dir(HERE / "results/repeat_scenario", stamp)
    details["run"]["result_directory"] = str(out)
    write_report(out, details, "\n".join(lines))
    print("\n".join(lines))
    print(f"Saved: {out}")
    return 1 if details["run"]["status"] == "failed" or aggregate["errors"] else 0

if __name__ == "__main__": raise SystemExit(main())
