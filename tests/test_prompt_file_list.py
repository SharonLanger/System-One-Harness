"""Configured detector preserves complete filenames independently of flow eligibility."""
import pytest

from building_blocks.file_reference_utils import detect_configured_references


@pytest.mark.parametrize("prompt,expected", [
    ("Explain this code", []),
    ("Parser.parse uses Object.keys and returns 1.5", []),
    ("Explain `main.ts`: how does Parser.parse work?", ["main.ts"]),
    ("Explain `main.ts`: what does Object.keys return?", ["main.ts"]),
    ("Explain `main.ts`: why does it return 1.5?", ["main.ts"]),
    ("Compare main.ts and src/parser.ts", ["main.ts", "src/parser.ts"]),
    ("Read a.ts, b.ts; then (src/c.ts).", ["a.ts", "b.ts", "src/c.ts"]),
    ('Compare "src/my file.ts" with `other.ts`', ["src/my file.ts", "other.ts"]),
    ("Read /repo/src/a.ts:12:3 and ./b.ts:7", ["/repo/src/a.ts", "./b.ts"]),
    ("main.ts and main.ts again", ["main.ts", "main.ts"]),
    ("a.spec.ts a.test.ts types.d.ts", ["a.spec.ts", "a.test.ts", "types.d.ts"]),
    ("a.tsx b.js c.json d.TS", []),
    ("a.ts.bak b.tsx", []),
], ids=["none", "dotted-expressions", "member", "builtin", "decimal",
        "multiple", "punctuation", "quoted-spaces", "line-locations",
        "duplicates", "eligibility-is-separate", "unsupported-suffixes", "no-partial-suffix"])
def test_default_prompt_filename_list(prompt, expected):
    actual = detect_configured_references(prompt, {"include_patterns": [r"\.ts$"], "exclude_patterns": []})
    assert [reference.path for reference in actual] == expected
