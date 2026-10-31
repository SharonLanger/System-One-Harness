"""F03 contract for the pending default-regex improvement.

V1 supported filename suffixes: [".ts"], case-sensitive.
Extract every matching path in prompt order, preserving duplicate mentions and
directory components. Detection does not read files or decide flow eligibility.
Test/declaration files remain detectable; the flow separately excludes them.
The existing detector returns FileReference records; their .path values define
the filename list below. Keep its external-pattern API and metadata intact.
Multiple detected files are returned by the detector even though V1 enrichment
supports only one. Do not treat member access or decimals as file references.
Implementation fix pending; failing cases are intentional regressions.
"""
from examples._plumbing_inspection import plumbing_provider

import pytest

from laya_context_router.building_blocks.file_reference_utils import detect_file_references
from laya_context_router.flows import file_method_context as flow
from laya_context_router.laya.config import RunConfig
from laya_context_router.laya.registry import AgentRegistry
from test_method_selection import raw_for


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
    actual = detect_file_references(prompt, flow.DEFAULT_REFERENCE_PATTERN)
    assert [reference.path for reference in actual] == expected


@pytest.mark.parametrize("question", [
    "how does Parser.parse work?",
    "what does Object.keys return?",
    "why does it return 1.5?",
])
def test_single_ts_file_with_dotted_expression_can_produce_context(tmp_path, question):
    (tmp_path / "main.ts").write_text("function chosen(){return 1.5;}", encoding="utf-8")
    calls = []

    class Spy:
        def predict(self, text, questions, **kwargs):
            calls.append(questions)
            selected = next(iter(questions["method"]["criteria"]))
            return raw_for(questions, selected)

    result = flow.run(
        "Explain `main.ts`: " + question,
        cwd=tmp_path, repository_root=tmp_path, config=RunConfig(),
        registry=AgentRegistry(inspection_provider=plumbing_provider, loader=lambda *args, **kwargs: Spy()),
    )
    assert result["status"] == "context", result
    assert len(calls) == 1


def test_multiple_real_files_still_skip_enrichment(tmp_path):
    def forbidden_loader(*args, **kwargs):
        raise AssertionError("Multiple files must not load a model")

    result = flow.run(
        "Explain `main.ts`: compare with `other.ts`",
        cwd=tmp_path, repository_root=tmp_path, config=RunConfig(),
        registry=AgentRegistry(inspection_provider=plumbing_provider, loader=forbidden_loader),
    )
    assert result == {"status": "noop", "reason": "multiple_files", "context": None}
