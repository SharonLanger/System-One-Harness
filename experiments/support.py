"""Small reporting utilities for manually run experiments."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import os
import sys

# Hook replay also imports this helper directly from the experiments directory.
REPO_SRC = Path(__file__).resolve().parents[1] / "src"
if str(REPO_SRC) not in sys.path:
    sys.path.insert(0, str(REPO_SRC))
from laya_context_router.log_utils import LOG_PATH, log


class ObservingRegistry:
    """Wrap the existing registry and retain the SDK reply before validation."""
    def __init__(self, registry):
        self.registry = registry
        self.raw_response = None

    def get_agent(self, config):
        agent = self.registry.get_agent(config)
        owner = self

        class ObservedAgent:
            def predict(self, *args, **kwargs):
                raw = agent.predict(*args, **kwargs)
                owner.raw_response = raw
                return raw

        return ObservedAgent()


def start_record(script: str, entry_point: str, execution_mode: str) -> dict:
    now = datetime.now().astimezone()
    log("INFO", "experiment", "started", script=script, entry_point=entry_point,
        execution_mode=execution_mode)
    return {
        "pid": os.getpid(),
        "log_path": str(LOG_PATH),
        "script": script,
        "entry_point": entry_point,
        "schema_version": 1,
        "started_local": now.isoformat(timespec="seconds"),
        "started_utc": now.astimezone(timezone.utc).isoformat(timespec="seconds"),
        "timezone_offset": now.strftime("%z"),
        "execution_mode": execution_mode,
        "status": "failed",
    }


def allocate_result_dir(root: Path, stamp: datetime) -> Path:
    parent = root / stamp.strftime("%Y-%m-%d_%H-%M-%S")
    candidate = parent
    index = 1
    while True:
        try:
            candidate.mkdir(parents=True, exist_ok=False)
            return candidate
        except FileExistsError:
            candidate = parent.with_name(f"{parent.name}_{index:03d}")
            index += 1


def json_safe(value):
    try:
        json.dumps(value, allow_nan=False)
        return value
    except (TypeError, ValueError):
        return {"representation": repr(value), "valid_json": False}


def write_report(output_dir: Path, details: dict, summary: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "details.json").write_text(json.dumps(details, indent=2, ensure_ascii=False) + "\n")
    summary = summary.rstrip() + f"\n\nDebug log: `{LOG_PATH}`; experiment PID: `{os.getpid()}`.\n"
    (output_dir / "summary.md").write_text(summary)
    log("INFO", "experiment", "report_saved", script=details.get("run", {}).get("script"),
        output_dir=output_dir, status=details.get("run", {}).get("status"),
        error_details=details.get("error"), result=details.get("result"),
        hook_stderr=details.get("stderr"))

