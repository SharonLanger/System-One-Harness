"""F06: preserve a referenced declaration and explicitly flag absent implementation.

User decision: declaration signatures are useful context, like global variables.
Both local and project collectors should include the declaration with a
declaration_only gap. Implementation changes are deferred.
"""

import json

import pytest

from building_blocks.typescript import (
    collect_local_context,
    collect_project_context,
    outline,
)


@pytest.mark.parametrize("project", [False, True], ids=["local", "project"])
def test_referenced_declaration_is_included_with_missing_implementation_gap(tmp_path, project):
    declaration = "declare function getPrice(): number;"
    source = tmp_path / "main.ts"
    source.write_text(
        declaration + "\nfunction calculateTotal() { return getPrice() * 2; }",
        encoding="utf-8",
    )
    if project:
        (tmp_path / "tsconfig.json").write_text(json.dumps({
            "compilerOptions": {"module": "commonjs", "moduleResolution": "node"},
            "include": ["*.ts"],
        }), encoding="utf-8")
    selected = next(item for item in outline(source)["callables"] if item["name"] == "calculateTotal")
    if project:
        result = collect_project_context(source, selected["id"], repository_root=tmp_path)
    else:
        result = collect_local_context(source, selected["id"])

    assert declaration in [item["code"] for item in result["dependencies"]], result
    assert any(item["code"] == "declaration_only" for item in result["gaps"]), result
