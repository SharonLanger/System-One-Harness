"""Actual source/flow/hook integration; only the Laya SDK boundary is simulated."""
import json

import pytest

from laya_context_router.building_blocks.typescript import outline
from laya_context_router.flows import file_method_context as flow
from test_file_method_context import CONFIG, forbidden_registry, source
from test_method_selection import questions_for, raw_for, registry_for
from test_prompt_hook import HEADER, hook_case, invoke, assert_noop


def run_selected(tmp_path, path, **kwargs):
    data = outline(path)
    selected = next(c for c in data["callables"] if c["name"] == "selected")
    questions = questions_for(data)
    assert "SECRET_PAYLOAD" not in json.dumps(questions)
    prompt = f"Explain `{path.name}`: how does selected work?"
    calls = []
    result = flow.run(prompt, cwd=tmp_path, repository_root=tmp_path, config=CONFIG,
        registry=registry_for(prompt, questions, raw_for(questions, selected["id"]), calls), **kwargs)
    assert len(calls) == 1
    return result


@pytest.mark.parametrize("limits,units,gap", [({}, 2, None),
    ({"max_dependency_depth": 0}, 0, "depth_limit"),
    ({"max_dependency_depth": 1}, 1, "depth_limit"),
    ({"max_dependency_chars": 1}, 0, "size_limit"),
    ({"max_dependency_depth": 20, "max_dependency_chars": 1000000}, 2, None)])
def test_flow_collects_exact_dependencies_with_independent_source_limits(tmp_path, limits, units, gap):
    value = 'const value = "SECRET_PAYLOAD😀";'
    helper = 'function helper() { return value; }'
    raw = 'function selected() { return helper(); }'
    path = source(tmp_path, "a.ts", value + '\r\n' + helper + '\r\n' + raw)
    before = path.read_bytes()
    result = run_selected(tmp_path, path, **limits)
    assert result["status"] == "context"
    context = result["context"]
    assert context["code"] == raw and context["coverage"] == "partial"
    assert len(context["dependencies"]) == units
    if units == 2: assert [d["code"] for d in context["dependencies"]] == [value, helper]
    if units == 1: assert context["dependencies"][0]["code"] == helper
    if gap: assert any(g["code"] == gap for g in context["gaps"])
    for dependency in context["dependencies"]:
        assert dependency["source_hash"] == context["source_hash"]
        assert dependency["path"] == context["path"]
        assert dependency["symbol_ids"]
    assert path.read_bytes() == before


@pytest.mark.parametrize("limits", [{"max_dependency_depth": -1}, {"max_dependency_depth": True},
    {"max_dependency_depth": 21}, {"max_dependency_depth": 1.0},
    {"max_dependency_chars": 0}, {"max_dependency_chars": 1000001},
    {"max_dependency_chars": False}, {"max_dependency_chars": float("nan")}])
def test_invalid_source_limits_refuse_before_source_or_model(tmp_path, monkeypatch, limits):
    def forbidden(*args, **kwargs): raise AssertionError("source must not be read")
    monkeypatch.setattr(flow, "outline", forbidden)
    result = flow.run("Explain `a.ts`: selected", cwd=tmp_path, repository_root=tmp_path,
                      config=CONFIG, registry=forbidden_registry(), **limits)
    assert result == {"status": "noop", "reason": "invalid_dependency_budget", "context": None}


def decode(result):
    assert result.returncode == 0
    additional = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert additional.startswith(HEADER)
    return additional, json.loads(additional[len(HEADER):])


def test_large_dependency_bundle_final_overflow_or_explicit_whole_unit_omission(tmp_path):
    dependency = 'const payload = "' + 'x' * 9000 + '";'
    selected = 'function selected() { return payload; }'
    case = hook_case(tmp_path, dependency + '\n' + selected)
    before = case["path"].read_bytes()
    overflow = invoke(case)
    assert_noop(overflow)
    assert "context_budget_exceeded" in overflow.stderr
    limited = invoke(case, args=case["args"] + ["--max-dependency-chars", "32"])
    text, context = decode(limited)
    assert len(text) <= 8000
    assert context["code"] == selected
    assert context["dependencies"] == []
    assert context["collection"]["dependency_chars"] == 0
    assert context["collection"]["max_dependency_chars"] == 32
    assert any(g["code"] == "size_limit" for g in context["gaps"])
    assert context["coverage"] == "partial" and case["path"].read_bytes() == before


@pytest.mark.parametrize("delta", [0, -1])
def test_unicode_dependency_source_and_exact_final_render_budgets(tmp_path, delta):
    dependency = 'const payload = "😀";'
    selected = 'function selected() {\r\n  return payload;\r\n}'
    case = hook_case(tmp_path, dependency + '\r\n' + selected)
    size = len(dependency.encode("utf-16-le")) // 2
    assert size > len(dependency)
    args = case["args"] + ["--max-dependency-chars", str(size), "--max-dependency-depth", "1"]
    text, context = decode(invoke(case, args=args))
    assert context["dependencies"][0]["code"] == dependency
    assert context["dependencies"][0]["source_hash"] == context["source_hash"]
    assert context["code"] == selected
    assert context["collection"]["dependency_chars"] == size
    exact = invoke(case, args=args + ["--max-context-chars", str(len(text) + delta)])
    if delta: assert_noop(exact); assert "context_budget_exceeded" in exact.stderr
    else: assert decode(exact)[0] == text
    _, omitted = decode(invoke(case, args=case["args"] + ["--max-dependency-chars", str(size - 1)]))
    assert omitted["dependencies"] == []
    assert any(g["code"] == "size_limit" for g in omitted["gaps"])


@pytest.mark.parametrize("args", [["--max-dependency-depth", "-1"], ["--max-dependency-depth", "21"],
    ["--max-dependency-depth", "1.5"], ["--max-dependency-chars", "0"],
    ["--max-dependency-chars", "1000001"]])
def test_hook_invalid_source_limits_before_sdk(tmp_path, args):
    case = hook_case(tmp_path)
    assert_noop(invoke(case, args=case["args"] + args))
    assert not case["log"].exists()
