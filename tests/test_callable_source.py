import json
from pathlib import Path
import sys

import pytest

from laya_context_router.building_blocks.typescript import TypeScriptError, outline, extract_callable


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_exact_raw_unicode_comments_and_no_writes(tmp_path, newline):
    raw = 'export function same(): string {\n  // interior 😀\n  return "🙃"; /* keep */\n}'
    raw = raw.replace("\n", newline)
    text = '// 😀 before\n/** attached excluded */\n'.replace("\n", newline) + raw + ' // trailing excluded\n'.replace("\n", newline)
    source = tmp_path / "source with spaces.ts"
    source.write_bytes(text.encode())
    before = source.read_bytes()
    candidate = outline(source)["callables"][0]
    result = extract_callable(source, candidate["id"])
    assert result["code"] == raw
    assert result["callable"] == candidate
    assert result["path"] == str(source)
    assert result["source_hash"] == candidate["id"].split(":")[0]
    assert result["display_code"].startswith("3: export function same()")
    assert "4:   // interior 😀" in result["display_code"]
    assert "attached" not in result["code"] and "trailing" not in result["code"]
    assert "3: " not in result["code"]
    assert result["limitations"]
    assert source.read_bytes() == before


def test_same_named_functions_in_separate_files_and_empty_body(tmp_path):
    a, b = tmp_path / "a.ts", tmp_path / "b.ts"
    a.write_text("function same() {}")
    b.write_text("function same() { return 2; }")
    aa, bb = outline(a)["callables"][0], outline(b)["callables"][0]
    assert aa["id"] != bb["id"]
    assert extract_callable(a, aa["id"])["code"] == "function same() {}"
    assert extract_callable(b, bb["id"])["code"] == "function same() { return 2; }"
    with pytest.raises(TypeScriptError, match="stale|unknown"):
        extract_callable(a, bb["id"])


def test_changed_source_invalid_ids_and_unsupported_forms(tmp_path):
    source = tmp_path / "a.ts"
    source.write_text("function first() {}")
    candidate = outline(source)["callables"][0]
    source.write_text("function other() {}")
    for bad_id in [candidate["id"], "unknown", "0" * 64 + ":0:1"]:
        with pytest.raises(TypeScriptError, match="stale|unknown"):
            extract_callable(source, bad_id)
    source.write_text("class C { method() {} } const f = () => 1;")
    result = outline(source)
    assert not result["callables"] and len(result["diagnostics"]) == 2
    unsupported = result["diagnostics"][0]
    with pytest.raises(TypeScriptError, match="unknown"):
        extract_callable(source, f'{result["source_hash"]}:{unsupported["start"]}:{unsupported["end"]}')


def test_malformed_extraction_schema(tmp_path):
    source = tmp_path / "a.ts"
    script = tmp_path / "fake.py"
    script.write_text('print(\'{"schema_version":1,"code":"incorrect"}\')')
    with pytest.raises(TypeScriptError, match="schema"):
        extract_callable(source, "x", node=sys.executable, helper=script)


def test_valid_outline_wrapped_as_extraction_is_not_enough(tmp_path):
    source = tmp_path / "a.ts"
    source.write_text("function f() {}")
    candidate = outline(source)["callables"][0]
    response = {"schema_version": 1, "path": str(source), "source_hash": candidate["id"].split(":")[0],
                "callable": candidate, "code": "x", "display_code": "1: x", "diagnostics": [], "limitations": []}
    script = tmp_path / "fake.py"
    script.write_text(f"print({json.dumps(json.dumps(response))})")
    with pytest.raises(TypeScriptError, match="schema"):
        extract_callable(source, candidate["id"], node=sys.executable, helper=script)
