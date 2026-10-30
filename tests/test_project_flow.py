"""Complete project-source-to-hook scenarios, with only the SDK boundary mocked."""
import hashlib
import json

import pytest

from laya_context_router.building_blocks.typescript import outline
from laya_context_router.flows import file_method_context as flow
from laya_context_router.laya.registry import AgentRegistry
from test_dependency_flow import decode
from test_file_method_context import CONFIG, source
from test_method_selection import questions_for, raw_for
from test_prompt_hook import hook_case, invoke


def configure(case, files, *, paths=True):
    config = {"compilerOptions": {"module": "commonjs", "moduleResolution": "node"}, "include": ["**/*.ts"]}
    if paths: config["compilerOptions"].update({"baseUrl": ".", "paths": {"@context/*": ["deps/*"]}})
    (case["repo"] / "tsconfig.json").write_text(json.dumps(config))
    for name, text in files.items():
        path = case["repo"] / name
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_bytes(text.encode())


def project_case(tmp_path, *, missing=False):
    imp = 'import {work as alias} from "@context/entry";'
    missing_imp = 'import {missing} from "./absent";'
    raw = 'function selected() {\r\n  return alias()' + (' + missing()' if missing else '') + ';\r\n}'
    case = hook_case(tmp_path, imp + '\r\n' + (missing_imp + '\r\n' if missing else '') + raw)
    entry = 'export {work} from "./barrel";'
    barrel = 'export {work} from "./data";'
    work = 'export function work() { return "😀"; }'
    marker = case["repo"] / "must-not-exist"
    effect = 'require("fs").writeFileSync(' + json.dumps(str(marker)) + ', "bad");\r\n'
    configure(case, {"deps/entry.ts": entry, "deps/barrel.ts": barrel, "deps/data.ts": effect + work})
    return case, raw, [barrel, work, entry, imp] + ([missing_imp] if missing else []), marker


def test_cross_file_routes_and_provenance_survive_real_hook_without_execution(tmp_path):
    case, raw, units, marker = project_case(tmp_path)
    before = {p: p.read_bytes() for p in case["repo"].rglob("*.ts")}
    text, context = decode(invoke(case),case)
    assert len(text) <= 8000 and context["code"] == raw and context["coverage"] == "partial"
    assert "project" in context
    assert context["project"]["repository_root"] == str(case["repo"])
    assert context["project"]["config_path"] == str(case["repo"] / "tsconfig.json")
    assert [d["code"] for d in context["dependencies"]] == units
    for dependency in context["dependencies"]:
        content = before[next(p for p in before if str(p) == dependency["path"])]
        assert dependency["source_hash"] == hashlib.sha256(content).hexdigest()
        assert content.decode().encode("utf-16-le")[dependency["start"] * 2:dependency["end"] * 2].decode("utf-16-le") == dependency["code"]
        assert dependency["symbol_ids"]
    assert any(g["code"] == "caller_coverage" for g in context["gaps"])
    assert any(g["code"] == "module_side_effects" and g["path"].endswith("data.ts") for g in context["gaps"])
    assert not marker.exists()
    assert all(p.read_bytes() == content for p, content in before.items())
    events = [json.loads(line) for line in case["log"].read_text().splitlines()]
    assert len(events) == 2 and "writeFileSync" not in json.dumps(events[1]["questions"])


def test_cross_file_final_warning_and_explicit_complete_route_omission(tmp_path):
    imp = 'import {payload} from "@context/barrel";'
    route = 'export {payload} from "./data";'
    raw = 'function selected() { return payload; }'
    case = hook_case(tmp_path, imp + '\n' + raw)
    configure(case, {"deps/barrel.ts": route, "deps/data.ts": 'export const payload = "' + 'x' * 9000 + '";'})
    overflow = invoke(case)
    full, full_context = decode(overflow,case)
    assert len(full)>8000 and "x"*9000 in full
    assert full_context["code"] == raw
    text, context = decode(invoke(case, args=case["args"] + ["--max-dependency-chars", "100"]),case,max_dependency_chars=100)
    assert len(text) <= 8000 and context["code"] == raw
    assert [d["code"] for d in context["dependencies"]] == [route, imp]
    assert context["collection"]["dependency_chars"] == len(route) + len(imp)
    assert any(g["code"] == "size_limit" for g in context["gaps"])
    assert context["coverage"] == "partial"
    assert len(case["log"].read_text().splitlines()) == 4


@pytest.mark.parametrize("delta", [0, -1])
def test_project_hook_exact_unicode_crlf_render_boundary_with_unresolved_gap(tmp_path, delta):
    case, raw, units, marker = project_case(tmp_path, missing=True)
    text, context = decode(invoke(case),case)
    assert context["code"] == raw
    assert [d["code"] for d in context["dependencies"]] == units
    assert any(g["code"] == "missing_module" for g in context["gaps"])
    assert any(g["code"] == "caller_coverage" for g in context["gaps"])
    assert context["collection"]["dependency_chars"] > sum(len(d["code"]) for d in context["dependencies"])
    result = invoke(case, args=case["args"] + ["--max-context-chars", str(len(text) + delta)])
    assert decode(result,case)[0] == text
    assert not marker.exists()


@pytest.mark.parametrize("mode,reason", [("missing", "missing_config"), ("modern", "unsupported_resolution_mode")])
def test_project_hook_local_fallback_has_explicit_configuration_gap(tmp_path, mode, reason):
    raw = 'function selected(){return "😀";}'
    case = hook_case(tmp_path, raw)
    if mode == "modern": (case["repo"] / "tsconfig.json").write_text('{"compilerOptions":{"module":"nodenext"},"include":["**/*.ts"]}')
    _, context = decode(invoke(case),case)
    assert context["code"] == raw and context["coverage"] == "partial"
    assert any(g["code"] == reason for g in context["gaps"])
    assert context["dependencies"] == []


def test_foreign_snapshot_is_taken_after_selection_with_unchanged_selected_source(tmp_path):
    imp = 'import {work} from "./dep";'
    raw = 'function selected(){return work();}'
    main = source(tmp_path, "main.ts", imp + raw)
    dep = source(tmp_path, "dep.ts", 'export function work(){return 1;}')
    updated = 'export function work(){return 2;}'
    (tmp_path / "tsconfig.json").write_text('{"compilerOptions":{"moduleResolution":"node"},"include":["*.ts"]}')
    data = outline(main); questions = questions_for(data)
    prompt = "Explain `main.ts`: selected"
    before = main.read_bytes()
    class Fake:
        def predict(self, text, payloads, **kwargs):
            assert (text, payloads, kwargs) == (prompt, questions, {"lang": "fr"})
            dep.write_text(updated)
            return raw_for(questions, data["callables"][0]["signature"])
    result = flow.run(prompt, cwd=tmp_path, repository_root=tmp_path, config=CONFIG,
                      registry=AgentRegistry(loader=lambda *args, **kwargs: Fake()))
    assert result["status"] == "context"
    context = result["context"]
    assert context["code"] == raw
    foreign = [d for d in context["dependencies"] if d["path"] == str(dep)]
    assert [d["code"] for d in foreign] == [updated]
    assert foreign[0]["source_hash"] == hashlib.sha256(updated.encode()).hexdigest()
    assert main.read_bytes() == before
