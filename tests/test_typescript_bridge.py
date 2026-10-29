import json
from pathlib import Path
import sys
import time

import pytest

from laya_context_router.building_blocks.typescript import TypeScriptError, outline

ROOT = Path(__file__).resolve().parents[1]


def test_real_helper_fixture_and_path_spaces(tmp_path):
    text = (ROOT / "tests/fixtures/typescript/basic.ts").read_bytes()
    source = tmp_path / "source directory" / "my file.ts"
    source.parent.mkdir()
    source.write_bytes(text)
    result = outline(source)
    assert result["path"] == str(source)
    assert [c["name"] for c in result["callables"]] == ["greet", "twice"]
    assert result["callables"][0]["signature"] == "export function greet(name: string): string"
    assert result["callables"][0]["location"] == {"line": 2, "column": 1}
    assert result["callables"][0]["start"] == text.decode().index("export") + 1  # astral UTF16
    assert result["diagnostics"] == []


def fake(tmp_path, body):
    script = tmp_path / "fake helper.py"
    script.write_text(body)
    return script


def test_missing_node_and_missing_build(tmp_path):
    with pytest.raises(TypeScriptError, match="Node"):
        outline(tmp_path / "a.ts", node="missing-node-executable", helper=fake(tmp_path, ""))
    with pytest.raises(TypeScriptError, match="build"):
        outline(tmp_path / "a.ts", helper=tmp_path / "missing.js")


@pytest.mark.parametrize("body,match", [
    ('import sys; print("diagnostic",file=sys.stderr); sys.exit(7)', "diagnostic"),
    ('print("not json")', "JSON"),
    ('print("{}")', "schema"),
    ('print("[]")', "schema"),
    ('print(\'{"schema_version":true}\')', "schema"),
])
def test_process_protocol_failures(tmp_path, body, match):
    with pytest.raises(TypeScriptError, match=match):
        outline(tmp_path / "a.ts", node=sys.executable, helper=fake(tmp_path, body))


def test_bounded_timeout(tmp_path):
    start = time.monotonic()
    with pytest.raises(TypeScriptError, match="timed out"):
        outline(tmp_path / "a.ts", node=sys.executable,
                helper=fake(tmp_path, "import time; time.sleep(10)"), timeout=0.1)
    assert time.monotonic() - start < 3


def test_array_args_request_and_stdout_fidelity(tmp_path):
    script = fake(tmp_path, '''import json,sys
request=json.load(sys.stdin)
assert len(sys.argv)==1
print(json.dumps({"schema_version":1,"path":request["path"],"source_hash":"a"*64,"callables":[],"diagnostics":[],"limitations":["fixture"]}))
''')
    source = tmp_path / "a $(bad); file.ts"
    result = outline(source, node=sys.executable, helper=script)
    assert result["path"] == str(source)


def test_real_parser_error_and_no_execution(tmp_path):
    source = tmp_path / "bad.ts"
    source.write_text("function broken( {")
    with pytest.raises(TypeScriptError, match="parse"):
        outline(source)
    marker = tmp_path / "marker"
    source.write_text(f'require("fs").writeFileSync({json.dumps(str(marker))}, "bad"); function safe() {{}}')
    assert outline(source)["callables"][0]["name"] == "safe"
    assert not marker.exists()


@pytest.mark.parametrize("replacement", [
    {"path": "/wrong/path.ts"}, {"source_hash": "invalid"},
    {"callables": [{"name": "missing fields"}]},
    {"diagnostics": [{"code": "unsupported_callable", "message": "x", "start": True, "end": 4}]},
    {"limitations": [3]},
])
def test_malformed_helper_schema_rejected(tmp_path, replacement):
    source = tmp_path / "a.ts"
    response = {"schema_version": 1, "path": str(source), "source_hash": "a" * 64,
                "callables": [], "diagnostics": [], "limitations": ["fixture"]}
    response.update(replacement)
    script = fake(tmp_path, f"print({json.dumps(json.dumps(response))})")
    with pytest.raises(TypeScriptError, match="schema"):
        outline(source, node=sys.executable, helper=script)


@pytest.mark.parametrize("timeout", [0, -1, True, float("inf"), float("nan"), 61])
def test_timeout_configuration_is_bounded(tmp_path, timeout):
    with pytest.raises(ValueError):
        outline(tmp_path / "a.ts", timeout=timeout)
