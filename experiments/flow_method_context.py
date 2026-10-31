"""Run the existing file-method flow on the synthetic TypeScript fixture."""
from datetime import datetime
import json
import argparse
from pathlib import Path
import sys
import time
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))
from laya_context_router.flows.file_method_context import run as run_flow
from laya_context_router.laya.config import RunConfig
from laya_context_router.laya.registry import AgentRegistry
from support import ObservingRegistry, allocate_result_dir, json_safe, start_record, write_report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, help='alternate saved JSON prompt/config input')
    args = parser.parse_args()
    input_path = args.input.resolve() if args.input else HERE / 'inputs/flow_method_context.json'
    stem = 'flow_method_context' if not args.input else input_path.stem
    return run(input_path, stem, script_name=Path(__file__).name)


def run(input_path, stem, script_name='flow_method_context.py'):
    started, stamp = time.monotonic(), datetime.now().astimezone()
    details = {"run": start_record(script_name, "flows.file_method_context.run", "real"),
               "input": None, "submitted_text": None, "submitted_questions": None,
               "raw_response": None, "result": None, "error": None}
    config = None
    try:
        payload = json.loads(Path(input_path).read_text())
        if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
            raise ValueError("input must contain text as a string")
        details["input"] = payload
        config = RunConfig.from_dict(payload.get("config", {}))

        class CaptureRegistry:
            def __init__(self): self.observer = ObservingRegistry(AgentRegistry(real=True))
            def get_agent(self, cfg):
                agent = self.observer.get_agent(cfg)
                owner = self
                class CaptureAgent:
                    def predict(self, text, questions, **kwargs):
                        details["submitted_text"] = text
                        details["submitted_questions"] = json_safe(questions)
                        raw = agent.predict(text, questions, **kwargs)
                        # The observing wrapper retains raw output before downstream validation.
                        details["raw_response"] = json_safe(owner.observer.raw_response)
                        return raw
                return CaptureAgent()

        result = run_flow(payload["text"], cwd=ROOT, repository_root=ROOT,
                          config=config, registry=CaptureRegistry())
        details["result"] = json_safe(result)
        details["run"]["status"] = "completed"
    except Exception as exc:
        details["error"] = {"type": type(exc).__name__, "message": str(exc)}
        details["run"]["status"] = "failed"
    details["run"]["duration_seconds"] = round(time.monotonic() - started, 3)
    status = details.get("result")
    if isinstance(status, dict):
        outcome = status.get("status")
        if outcome == "context":
            context = status.get("context", {})
            selected = context.get("callable", {})
            code = context.get("code", "")
            excerpt = code[:2000]
            if len(code) > 2000: excerpt += "\n… (excerpt truncated)"
            dependencies = context.get('dependencies', [])
            dependency_lines = []
            for dependency in dependencies:
                path = dependency.get('path', 'unknown')
                try:
                    path = str(Path(path).resolve().relative_to(ROOT.resolve()))
                except (OSError, ValueError):
                    pass
                declaration = dependency.get('code', '').strip().replace('\n', ' ')
                if len(declaration) > 240:
                    declaration = declaration[:237] + '…'
                dependency_lines.append(f"- `{path}` — `{declaration or dependency.get('kind', 'dependency')}`")
            gaps = context.get('gaps', [])
            gap_lines = []
            for gap in gaps:
                path = gap.get('path', 'unknown')
                try:
                    path = str(Path(path).resolve().relative_to(ROOT.resolve()))
                except (OSError, ValueError):
                    pass
                message = gap.get('message', '')
                if len(message) > 240:
                    message = message[:237] + '…'
                gap_lines.append(f"- `{gap.get('code', 'unknown')}` at `{path}`: {message}")
            dependency_section = '\n'.join(dependency_lines) if dependency_lines else '- None collected.'
            gap_section = '\n'.join(gap_lines) if gap_lines else '- None reported.'
            desc = (f"Context selected: `{selected.get('name', 'unknown')}` from `{context.get('path', 'unknown')}`.\n\n"
                    f"Dependencies ({len(dependencies)}):\n{dependency_section}\n\n"
                    f"Gaps ({len(gaps)}):\n{gap_section}\n\n"
                    "Selected source excerpt:\n\n```typescript\n" + excerpt + "\n```")
        else:
            desc = f"Flow no-op reason: `{status.get('reason', 'unknown')}`."
    else:
        desc = f"Experiment error: `{details['error']['type']}: {details['error']['message']}`."
    config_desc = (f"Requested model: `{config.model}`; temperature: `{config.temperature if config.temperature is not None else 'SDK default'}`."
                   if config is not None else "Requested model configuration could not be loaded.")
    summary = ("# File method context flow\n\n" + desc + "\n\n" + config_desc + "\n\n"
               "The flow result and raw response/question payload (when observed) are in `details.json`. A no-op is a valid flow result.\n")
    try:
        out = allocate_result_dir(HERE / f"results/{stem}", stamp)
        details["run"]["result_directory"] = str(out)
        write_report(out, details, summary)
        print(summary, end="")
        print(f"Saved: {out}")
    except Exception as exc:
        print(f"ERROR saving report: {type(exc).__name__}: {exc}")
        return 1
    return 1 if details["run"]["status"] == "failed" else 0

if __name__ == "__main__": raise SystemExit(main())
