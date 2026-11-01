"""F01: object shorthand must retain value dependencies. Implementation fix pending."""

import json

import pytest

from building_blocks.typescript import (
    collect_local_context,
    collect_project_context,
    outline,
)


@pytest.mark.parametrize("project", [False, True], ids=["local", "project"])
@pytest.mark.parametrize("kind", ["constant", "function", "import"])
def test_shorthand_keeps_referenced_declaration(tmp_path, project, kind):
    declaration = {
        "constant": "const value=42;",
        "function": "function value(){return 42;}",
        "import": 'import {value} from "./dep";',
    }[kind]
    source = tmp_path / "main.ts"
    source.write_text(declaration + " function chosen(){return {value};}", encoding="utf-8")
    (tmp_path / "dep.ts").write_text("export const value=42;", encoding="utf-8")
    if project:
        (tmp_path / "tsconfig.json").write_text(json.dumps({
            "compilerOptions": {"module": "commonjs", "moduleResolution": "node"},
            "include": ["*.ts"],
        }), encoding="utf-8")

    candidate = next(item for item in outline(source)["callables"] if item["name"] == "chosen")
    if project:
        result = collect_project_context(source, candidate["id"], repository_root=tmp_path)
    else:
        result = collect_local_context(source, candidate["id"])
    dependencies = [item["code"] for item in result["dependencies"]]
    assert declaration in dependencies, result
    if project and kind == "import":
        assert "export const value=42;" in dependencies, result
