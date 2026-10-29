import copy
from pathlib import Path
import subprocess
import sys

import pytest

from laya_context_router.flows import file_method_context as flow
from laya_context_router.building_blocks.typescript import outline
from laya_context_router.laya.config import RunConfig
from laya_context_router.laya.registry import AgentRegistry
from test_method_selection import questions_for, raw_for, registry_for

ROOT = Path(__file__).resolve().parents[1]
CONFIG = RunConfig("mock-selection", 0.2, "fr")


def source(tmp_path, name="src/my file.ts", text='export function greet() { return "😀"; }'):
    path = tmp_path / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text)
    return path


def forbidden_registry():
    def fail(*args, **kwargs):
        raise AssertionError("must not load")
    return AgentRegistry(loader=fail)


@pytest.mark.parametrize("absolute", [False, True])
def test_complete_real_source_flow_exact_request_and_context(tmp_path, absolute):
    path = source(tmp_path)
    data = outline(path); candidate = data["callables"][0]
    target = str(path) if absolute else "src/my file.ts"
    prompt = f"Explain `{target}`: how does greet work?"
    original = copy.deepcopy(prompt); before = path.read_bytes(); calls=[]
    expected = questions_for(data)
    result = flow.run(prompt, cwd=tmp_path, repository_root=tmp_path, config=CONFIG,
                      registry=registry_for(prompt, expected, raw_for(expected, candidate["id"]), calls))
    assert result["status"] == "context" and result["reason"] is None
    context = result["context"]
    assert context["code"] == 'export function greet() { return "😀"; }'
    assert context["path"] == str(path) and context["callable"] == candidate
    assert context["coverage"] == "partial"
    assert any("Dependency" in line for line in context["limitations"])
    assert len(calls) == 1 and prompt == original and path.read_bytes() == before


@pytest.mark.parametrize("prompt,reason", [
    ("Explain this behavior", "no_file"), ("src/a.ts", "ineligible_request"),
    ("Create `output.ts`: write an implementation", "ineligible_request"),
    ("Log: failed parsing `src/a.ts`", "ineligible_request"),
    ("Explain log mention `src/a.ts`", "unsupported_request"),
    ("Explain `a.ts`: compare `b.ts`", "multiple_files"),
    ("Explain `a.ts`: compare b.ts", "multiple_files"),
    ("Explain `a.spec.ts`: what does f do?", "excluded"),
    ("Explain `a.d.ts`: what does f do?", "excluded"),
    ("Explain `a.tsx`: what does f do?", "excluded"),
    ("Explain `a.ts`", "unsupported_request"),
])
def test_ineligible_mentions_no_source_or_model(tmp_path, monkeypatch, prompt, reason):
    def no_helper(*args, **kwargs):
        raise AssertionError("must not read source")
    monkeypatch.setattr(flow, "outline", no_helper)
    result = flow.run(prompt, cwd=tmp_path, repository_root=tmp_path, config=CONFIG, registry=forbidden_registry())
    assert result == {"status": "noop", "reason": reason, "context": None}


def test_ambiguous_missing_and_outside_repository(tmp_path):
    root=tmp_path/"repo"; root.mkdir()
    source(root,"a/same.ts"); source(root,"b/same.ts")
    outside=source(tmp_path,"outside.ts")
    (root/"escape.ts").symlink_to(outside)
    for target, reason in [("same.ts","ambiguous"),("missing.ts","missing"),("../outside.ts","outside_repository"),("escape.ts","outside_repository")]:
        result=flow.run(f"Explain `{target}`: how does f work?",cwd=root,repository_root=root,config=CONFIG,registry=forbidden_registry())
        assert result["status"] == "noop" and result["context"] is None and result["reason"] == reason


@pytest.mark.parametrize("choice,confidence,reason", [("candidate",0.1,"method_undecided"),("none_or_unclear",0.95,"no_single_match")])
def test_rejected_and_abstained_selection(tmp_path, choice, confidence, reason):
    path=source(tmp_path,"a.ts"); data=outline(path); expected=questions_for(data)
    selected=data["callables"][0]["id"] if choice=="candidate" else choice
    prompt="Explain `a.ts`: explain greet"
    result=flow.run(prompt,cwd=tmp_path,repository_root=tmp_path,config=CONFIG,
                    registry=registry_for(prompt,expected,raw_for(expected,selected,confidence=confidence),[]))
    assert result["reason"] == reason and result["context"] is None


def test_model_failure_and_source_changed_after_selection(tmp_path):
    path=source(tmp_path,"a.ts"); data=outline(path); expected=questions_for(data); selected=data["callables"][0]["id"]
    prompt="Explain `a.ts`: explain greet"
    for mode in ["failure", "stale"]:
        class Fake:
            def predict(self,text,questions):
                assert text==prompt and questions==expected
                if mode=="failure": raise RuntimeError("planned model failure")
                path.write_text("export function changed() {}")
                return raw_for(expected,selected)
        result=flow.run(prompt,cwd=tmp_path,repository_root=tmp_path,config=RunConfig(),registry=AgentRegistry(loader=lambda model:Fake()))
        assert result["reason"] == ("model_error" if mode=="failure" else "extractor_error")
        assert result["context"] is None


def test_parser_malformed_outline_and_extraction_fail_closed(tmp_path, monkeypatch):
    path=source(tmp_path,"a.ts", "function broken( {")
    prompt="Explain `a.ts`: explain greet"
    assert flow.run(prompt,cwd=tmp_path,repository_root=tmp_path,config=CONFIG,registry=forbidden_registry())["reason"]=="extractor_error"
    helper=tmp_path/"bad_helper.py"; helper.write_text("print('{}')")
    assert flow.run(prompt,cwd=tmp_path,repository_root=tmp_path,config=CONFIG,registry=forbidden_registry(),node=sys.executable,helper=helper)["reason"]=="extractor_error"
    path.write_text("function greet() {}")
    data=outline(path); expected=questions_for(data)
    monkeypatch.setattr(flow,"extract_callable",lambda *args,**kwargs:{"bad":"shape"})
    result=flow.run(prompt,cwd=tmp_path,repository_root=tmp_path,config=CONFIG,
                    registry=registry_for(prompt,expected,raw_for(expected,data["callables"][0]["id"]),[]))
    assert result["reason"]=="extractor_error" and result["context"] is None


def test_external_regex_budget_and_missing_build(tmp_path):
    path=source(tmp_path,"a.ts"); prompt="Explain `a.ts`: explain greet"
    for kwargs,reason in [({"reference_pattern":r'FILE\[(?P<path>[^\]]+)\]'},"no_file"),
                          ({"reference_pattern":"["},"invalid_reference"),
                          ({"max_candidates":0},"candidate_budget_exceeded"),
                          ({"helper":tmp_path/"absent.js"},"extractor_error")]:
        result=flow.run(prompt,cwd=tmp_path,repository_root=tmp_path,config=CONFIG,registry=forbidden_registry(),**kwargs)
        assert result["reason"]==reason and result["context"] is None


def test_demo_uses_offline_real_flow():
    result=subprocess.run([sys.executable,str(ROOT/"examples/file_method_context.py")],cwd=ROOT,
                          env={**__import__('os').environ,"PYTHONPATH":str(ROOT/"src")},capture_output=True,text=True,check=True)
    import json
    output=json.loads(result.stdout)
    assert output["status"]=="context" and "function greet" in output["context"]["code"]
    assert result.stderr==""
