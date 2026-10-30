import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "experiments"))
import laya_choice


RAW = {"answers": {"fruit": {
    "type": "choice", "choice": "apple",
    "probabilities": {"apple": 0.8, "pear": 0.2},
}}}


class Agent:
    def __init__(self, raw=RAW):
        self.raw = copy.deepcopy(raw)
        self.calls = []

    def predict(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return copy.deepcopy(self.raw)


def test_choice_runs_adapter_writes_truthful_report(tmp_path):
    agent = Agent()
    loads = []

    def loader(model, **kwargs):
        loads.append((model, kwargs))
        return agent

    output = tmp_path / "results" / "laya_choice"
    messages = []
    status = laya_choice.run(loader=loader, output_root=output, printer=messages.append)
    assert status == 0
    assert loads == [("aac6fef/laya-typed-decisions-mlx", {})]
    source = json.loads(laya_choice.INPUT_PATH.read_text())
    assert agent.calls == [((source["text"], source["questions"]), {})]
    run_dir, = list(output.iterdir())
    report = json.loads((run_dir / "details.json").read_text())
    assert report["questions"] == source["questions"]
    assert report["raw_response"] == RAW
    assert report["model_config"]["requested"] == {
        "model": "aac6fef/laya-typed-decisions-mlx", "temperature": None, "lang": "en"
    }
    summary = (run_dir / "summary.md").read_text()
    assert "SDK default" in summary and "apple" in summary
    assert report["run"]["status"] == "success"
    assert report["run"]["execution_mode"] == "injected"
    assert any("Saved summary:" in line for line in messages)


def test_overrides_use_existing_run_config_mapping(tmp_path):
    agent = Agent()
    seen = []
    def loader(model, **kwargs):
        seen.append((model, kwargs))
        return agent
    status = laya_choice.run(loader=loader, model="demo/model", temperature=0.25,
                             temperature_set=True, lang="fr", output_root=tmp_path,
                             printer=lambda _: None)
    assert status == 0
    assert seen == [("demo/model", {"lang_temperatures": {"fr": {"temperature": [0.25] * 3}}})]
    assert agent.calls[0][1] == {"lang": "fr"}


def test_invalid_response_is_saved_as_failed_and_nonzero(tmp_path):
    messages = []
    status = laya_choice.run(loader=lambda *_a, **_k: Agent({"answers": {}}),
                             output_root=tmp_path, printer=messages.append)
    assert status == 1
    run_dir, = list(tmp_path.iterdir())
    report = json.loads((run_dir / "details.json").read_text())
    assert report["run"]["status"] == "failed"
    assert report["error"]["stage"] == "inference"
    assert report["raw_response"] == {"answers": {}}
    assert any("ERROR during inference" in line for line in messages)


def test_result_directory_collision_does_not_overwrite(tmp_path):
    from support import allocate_result_dir
    from datetime import datetime, timezone
    stamp = datetime(2026, 10, 30, 14, 32, 5, tzinfo=timezone.utc)
    first = allocate_result_dir(tmp_path, stamp)
    second = allocate_result_dir(tmp_path, stamp)
    assert first.name == "2026-10-30_14-32-05"
    assert second.name == "2026-10-30_14-32-05_001"


def test_invalid_input_still_saves_failed_report(tmp_path):
    input_path = tmp_path / "bad.json"
    input_path.write_text('{"text":"hello","questions":{},"config":[]}', encoding="utf-8")
    output = tmp_path / "results"
    messages = []
    assert laya_choice.run(input_path=input_path, output_root=output,
                           loader=lambda *_a, **_k: None, printer=messages.append) == 1
    run_dir, = output.iterdir()
    details = json.loads((run_dir / "details.json").read_text())
    assert details["error"]["stage"] == "input"
    assert "config must be an object" in details["error"]["message"]
    assert "unavailable" in (run_dir / "summary.md").read_text()
    assert any("Saved summary" in message for message in messages)
