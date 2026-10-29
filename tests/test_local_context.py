import json
import sys

import pytest

from laya_context_router.building_blocks.typescript import (
    TypeScriptError, collect_local_context, outline,
)


def test_semantic_local_context_and_complete_selected_source(tmp_path):
    source = tmp_path / "source with spaces.ts"
    text = '// 😀\r\nconst value = "🙃";\r\nfunction selected() { return value; }'
    source.write_bytes(text.encode())
    selected = outline(source)["callables"][0]
    result = collect_local_context(source, selected["id"])
    assert result["code"] == 'function selected() { return value; }'
    assert result["dependencies"][0]["code"] == 'const value = "🙃";'
    assert result["dependencies"][0]["source_hash"] == result["source_hash"]
    assert result["coverage"] == "partial"
    assert result["gaps"]
    assert source.read_bytes() == text.encode()
    omitted = collect_local_context(source, selected["id"], max_dependency_chars=1)
    assert omitted["dependencies"] == []
    assert omitted["code"] == result["code"]
    assert any(g["code"] == "size_limit" for g in omitted["gaps"])


@pytest.mark.parametrize("kwargs", [{"max_depth": -1}, {"max_depth": True},
    {"max_depth": 21}, {"max_dependency_chars": 0},
    {"max_dependency_chars": float("inf")}, {"max_dependency_chars": 1000001}])
def test_invalid_collection_limits_before_process(tmp_path, kwargs):
    with pytest.raises(ValueError):
        collect_local_context(tmp_path / "absent.ts", "id", **kwargs)


@pytest.mark.parametrize("change", ["hash", "path", "length", "total", "symbol", "order", "gap", "coverage", "limits"])
def test_local_context_protocol_rejects_malformed_provenance(tmp_path, change):
    source = tmp_path / "a.ts"
    source.write_text("const x=1; const y=2; function f(){return x+y;}")
    selected = outline(source)["callables"][0]
    response = collect_local_context(source, selected["id"])
    if change == "hash": response["dependencies"][0]["source_hash"] = "b" * 64
    if change == "path": response["dependencies"][0]["path"] = "/other.ts"
    if change == "length": response["dependencies"][0]["code"] = "x"
    if change == "total": response["collection"]["dependency_chars"] += 1
    if change == "symbol": response["dependencies"][0]["symbol_ids"] = ["bad"]
    if change == "order": response["dependencies"].reverse()
    if change == "gap": response["gaps"] = [{"code": "bad", "message": "x", "start": True, "end": 2}]
    if change == "coverage": response["coverage"] = "complete"
    if change == "limits": response["collection"]["max_depth"] = 20
    script = tmp_path / "fake.py"
    script.write_text(f"print({json.dumps(json.dumps(response))})")
    with pytest.raises(TypeScriptError, match="schema"):
        collect_local_context(source, selected["id"], node=sys.executable, helper=script)
