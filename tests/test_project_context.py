import hashlib
import json
import sys

import pytest

from laya_context_router.building_blocks.typescript import TypeScriptError, outline, collect_project_context


def fixture(tmp_path):
    main = tmp_path / "main.ts"
    dep = tmp_path / "dep.ts"
    main.write_text('import { work } from "./dep"; function selected(){return work();}')
    dep.write_bytes('const value="😀";\r\nexport function work(){return value;}'.encode())
    (tmp_path / "tsconfig.json").write_text('{"compilerOptions":{"moduleResolution":"node"},"include":["*.ts"]}')
    return main, dep, outline(main)["callables"][0]["id"]


def test_actual_project_source_provenance_and_explicit_partial_gaps(tmp_path):
    main, dep, selected = fixture(tmp_path)
    before = dep.read_bytes()
    result = collect_project_context(main, selected, repository_root=tmp_path)
    foreign = [d for d in result["dependencies"] if d["path"] == str(dep)]
    assert [d["code"] for d in foreign] == ['const value="😀";', 'export function work(){return value;}']
    assert all(d["source_hash"] == hashlib.sha256(before).hexdigest() for d in foreign)
    assert result["code"] == 'function selected(){return work();}'
    assert result["project"]["repository_root"] == str(tmp_path)
    assert result["project"]["config_sources"]
    assert result["coverage"] == "partial"
    assert any(g["code"] == "caller_coverage" for g in result["gaps"])
    assert dep.read_bytes() == before


@pytest.mark.parametrize("change", ["root", "config", "hash", "path", "length", "order", "gap", "gap_hash", "selected_hash", "symbol", "total"])
def test_project_bridge_rejects_invalid_cross_file_protocol(tmp_path, change):
    main, dep, selected = fixture(tmp_path)
    response = collect_project_context(main, selected, repository_root=tmp_path)
    if change == "root": response["project"]["repository_root"] = "/other"
    if change == "config": response["project"]["config_sources"][0]["source_hash"] = "bad"
    foreign = next(d for d in response["dependencies"] if d["path"] == str(dep))
    if change == "hash": foreign["source_hash"] = "bad"
    if change == "path": foreign["path"] = str(tmp_path.parent / "outside.ts")
    if change == "length": foreign["code"] = "x"
    if change == "order": response["dependencies"].reverse()
    if change == "gap": response["gaps"][0]["path"] = "/outside.ts"
    if change == "gap_hash": response["gaps"][0]["source_hash"] = "b" * 64
    if change == "selected_hash":
        local = next(d for d in response["dependencies"] if d["path"] == str(main))
        old = local["source_hash"]
        local["source_hash"] = "b" * 64
        local["id"] = local["id"].replace(old, "b" * 64)
        local["symbol_ids"] = [x.replace(old, "b" * 64) for x in local["symbol_ids"]]
    if change == "symbol": foreign["symbol_ids"] = ["bad"]
    if change == "total": response["collection"]["dependency_chars"] += 1
    helper = tmp_path / "fake.py"
    helper.write_text(f"print({json.dumps(json.dumps(response))})")
    with pytest.raises(TypeScriptError, match="schema"):
        collect_project_context(main, selected, repository_root=tmp_path, node=sys.executable, helper=helper)


def test_project_missing_config_fallback_and_invalid_limits(tmp_path):
    main, _, selected = fixture(tmp_path)
    (tmp_path / "tsconfig.json").unlink()
    result = collect_project_context(main, selected, repository_root=tmp_path)
    assert result["project"]["config_path"] is None
    assert any(g["code"] == "missing_config" for g in result["gaps"])
    for kwargs in [{"max_depth": True}, {"max_dependency_chars": 0}]:
        with pytest.raises(ValueError):
            collect_project_context(main, selected, repository_root=tmp_path, **kwargs)
