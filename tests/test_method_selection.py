import copy
import json
from pathlib import Path

import pytest

from laya_context_router.blocks import QuestionBlock
from laya_context_router.building_blocks.questions.method_selection.block import run, BLOCK_DIR
from laya_context_router.building_blocks.typescript import outline, extract_callable
from laya_context_router.laya.config import RunConfig
from laya_context_router.laya.registry import AgentRegistry
from laya_context_router.laya.predict import ResponseError

METHOD = "Select exactly one callable that the request asks to explain. Choose none_or_unclear when no single callable is appropriate."
MULTIPLE = "Does the request require explaining more than one candidate callable?"
NONE = "No single matching callable, or unclear request."


def source_outline(tmp_path):
    source = tmp_path / "a.ts"
    source.write_text("function same() { return 1; }\nfunction same(value: number) { return 2; }")
    return outline(source)


def label_for(data, candidate):
    name = candidate['name']
    if sum(c['name'] == name for c in data['callables']) > 1 or name == 'none_or_unclear':
        name += f"@{candidate['location']['line']}:{candidate['location']['column']}"
    return name


def questions_for(data):
    return {"method": {"type": "choice", "instructions": METHOD,
                       "criteria": {**{label_for(data, c): c["signature"] for c in data["callables"]}, "none_or_unclear": NONE}},
            "multiple_relevant": {"type": "noul", "instructions": MULTIPLE}}


def raw_for(questions, selected, multiple=0.1, confidence=0.95):
    keys = list(questions["method"]["criteria"])
    if selected not in keys:
        # Test callers may select a unique description; the raw model answer
        # must use its readable criterion label.
        matches = [key for key, description in questions['method']['criteria'].items() if description == selected]
        if len(matches) == 1:
            selected = matches[0]
    probs = {key: (0.9 if key == selected else 0.1 / (len(keys)-1)) for key in keys}
    return {"answers": {"method": {"type": "choice", "choice": selected, "probabilities": probs, "answer_confidence": confidence},
                        "multiple_relevant": {"type": "noul", "noul": multiple, "answer_confidence": 0.95}}}


def registry_for(text, expected, response, calls):
    class Fake:
        def predict(self, actual_text, actual_questions, **kwargs):
            assert (actual_text, actual_questions, kwargs) == (text, expected, {"lang": "fr"})
            calls.append((actual_text, copy.deepcopy(actual_questions)))
            assert "rules_by_question" not in json.dumps(actual_questions)
            assert "candidate_map" not in json.dumps(actual_questions)
            return copy.deepcopy(response)
    def loader(model, **kwargs):
        assert (model, kwargs) == ("mock-selection", {"lang_temperatures": {"fr": {"temperature": [0.2]*3}}})
        return Fake()
    return AgentRegistry(loader=loader)


@pytest.mark.parametrize("text,index,multiple,reason", [
    ("Explain the second same function", 1, 0.1, None),
    ("unrelated noise 123", None, 0.1, "no_single_match"),
    ("Explain a missing operation", None, 0.1, "no_single_match"),
    ("Explain both functions", 0, 0.9, "multiple_relevant"),
])
def test_fixed_requests_real_outline_actual_pipeline(tmp_path, text, index, multiple, reason):
    data = source_outline(tmp_path)
    before = copy.deepcopy(data)
    payload = questions_for(data)
    selected = "none_or_unclear" if index is None else data["callables"][index]["id"]
    calls = []
    result = run(text, data, config=RunConfig("mock-selection", 0.2, "fr"),
                 registry=registry_for(text, payload, raw_for(payload, "none_or_unclear" if index is None else data["callables"][index]["signature"], multiple), calls))
    assert result["reason"] == reason
    expected_id = selected if reason is None else None
    assert result["selected_id"] == expected_id
    assert len(calls) == 1
    assert data == before
    assert list(result["candidate_map"]) == [c["id"] for c in data["callables"]]
    assert len({c["id"] for c in data["callables"]}) == 2  # same names, separate ranges
    if expected_id:
        assert result["candidate_map"][expected_id]["start"] == data["callables"][1]["start"]
        assert result["candidate_map"][expected_id]["path"] == data["path"]
        assert extract_callable(data["path"], expected_id)["code"] == "function same(value: number) { return 2; }"


def test_policy_rejections_and_unknown_choice_fail_closed(tmp_path):
    data = source_outline(tmp_path); payload = questions_for(data); selected = data["callables"][0]["signature"]
    for confidence, multiple, reason in [(0.1, 0.1, "method_undecided"), (0.95, 0.5, "multiple_relevant")]:
        response = raw_for(payload, selected, multiple, confidence)
        result = run("Explain same", data, config=RunConfig("mock-selection", 0.2, "fr"),
                     registry=registry_for("Explain same", payload, response, []))
        assert result["selected_id"] is None and result["reason"] == reason
    response = raw_for(payload, selected)
    response["answers"]["method"]["choice"] = "unknown-id"
    with pytest.raises(ResponseError, match="choice"):
        run("Explain same", data, config=RunConfig("mock-selection", 0.2, "fr"),
            registry=registry_for("Explain same", payload, response, []))


def test_empty_and_budgets_refuse_before_loader_with_no_truncation(tmp_path):
    data = source_outline(tmp_path)
    def forbidden(*args, **kwargs):
        raise AssertionError("must not load")
    registry = AgentRegistry(loader=forbidden)
    empty = {**data, "callables": []}
    assert run("x", empty, config=RunConfig(), registry=registry)["reason"] == "no_candidates"
    for max_candidates in [0, 1]:
        result = run("x", data, config=RunConfig(), registry=registry, max_candidates=max_candidates)
        assert result["reason"] == "candidate_budget_exceeded"
    payload = questions_for(data)
    size = len("x") + len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    assert run("x", data, config=RunConfig(), registry=registry, max_input_chars=size-1)["reason"] == "input_budget_exceeded"
    for budget in [size, size+1]:
        calls=[]
        result = run("x", data, config=RunConfig("mock-selection", 0.2, "fr"),
                     registry=registry_for("x", payload, raw_for(payload, data["callables"][0]["signature"]), calls),
                     max_input_chars=budget, max_candidates=2)
        assert result["selected_id"] == data["callables"][0]["id"] and len(calls)==1


def test_templates_and_exact_named_override_immutable(tmp_path):
    block = QuestionBlock(BLOCK_DIR)
    before = {name: question.to_dict() for name, question in block.questions.items()}
    data = source_outline(tmp_path); payload = questions_for(data); original = copy.deepcopy(payload)
    run("x", data, config=RunConfig("mock-selection", 0.2, "fr"),
        registry=registry_for("x", payload, raw_for(payload, "none_or_unclear"), []))
    assert {name: question.to_dict() for name, question in block.questions.items()} == before
    assert payload == original
    assert {p.name for p in BLOCK_DIR.iterdir() if p.is_file()} == {"questions.json", "rules.json", "block.py", "README.md"}
    for bad in [{}, {"wrong": payload["method"]}, {**payload, "method": {"type": "bad"}}]:
        with pytest.raises(ValueError):
            block.run("x", config=RunConfig(), registry=AgentRegistry(loader=lambda model: None), question_payloads=bad)


def test_duplicate_ids_and_invalid_budgets_rejected(tmp_path):
    data = source_outline(tmp_path)
    def forbidden(*args, **kwargs):
        raise AssertionError("must not load")
    registry = AgentRegistry(loader=forbidden)
    duplicated = {**data, "callables": [data["callables"][0]] * 2}
    with pytest.raises(ValueError, match="candidate"):
        run("x", duplicated, config=RunConfig(), registry=registry)
    for limits in [{"max_candidates": True}, {"max_candidates": -1}, {"max_input_chars": 0}]:
        with pytest.raises(ValueError, match="budget"):
            run("x", data, config=RunConfig(), registry=registry, **limits)


def test_low_multiple_answer_confidence_refuses_selection(tmp_path):
    data = source_outline(tmp_path)
    payload = questions_for(data)
    response = raw_for(payload, data['callables'][0]['signature'])
    response['answers']['multiple_relevant']['answer_confidence'] = 0.1
    result = run('Explain same', data, config=RunConfig('mock-selection', 0.2, 'fr'),
                 registry=registry_for('Explain same', payload, response, []))
    assert result['reason'] == 'multiple_undecided' and result['selected_id'] is None
