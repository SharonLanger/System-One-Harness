"""Missing TypeScript file-reference no-op; makes no model call."""
from datetime import datetime
import json
from pathlib import Path
import sys
import time
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))
from laya_context_router.flows.file_method_context import run
from laya_context_router.laya.config import RunConfig
from support import allocate_result_dir, start_record, write_report


def main():
    started, stamp = time.monotonic(), datetime.now().astimezone()
    payload = json.loads((HERE / "inputs/flow_missing_file.json").read_text())
    result = run(payload["text"], cwd=ROOT, repository_root=ROOT,
                 config=RunConfig(), registry=None)
    # The prompt references a missing .ts path, so this is a deterministic
    # pre-inference no-op; registry is never consulted by the flow.
    details = {"run": start_record("flow_missing_file.py", "flows.file_method_context.run", "no_model"),
               "input": payload, "result": result,
               "model_call": "not_made"}
    details["run"]["status"] = "success"
    details["run"]["duration_seconds"] = round(time.monotonic() - started, 3)
    out = allocate_result_dir(HERE / "results/flow_missing_file", stamp)
    details["run"]["result_directory"] = str(out)
    write_report(out, details, f"# Missing file reference\n\nFlow outcome: `{result['status']}` (`{result['reason']}`).\n\nNo model call was made.\n")
    print(f"Flow status: {result['status']} ({result['reason']}); no model call made")
    print(f"Saved: {out}")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
