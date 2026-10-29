"""Phase08 lexical references: external expressions define the supported syntax."""
import re
from pathlib import Path

import pytest

from laya_context_router.building_blocks.file_reference_utils import detect_file_references

# Full quoted paths (including spaces), or whitespace-delimited unquoted paths.
PATTERN = r'''(?:["'`](?P<path>[^"'`\r\n]+\.[A-Za-z0-9]+)["'`])'''
PLAIN = r'(?<![\w/])(?P<path>/?[\w./-]+\.[A-Za-z0-9]+)(?::\d+(?::\d+)?)?'


def test_no_mentions_and_types():
    assert detect_file_references("explain this", PLAIN) == []
    for text, pattern in [(None, PLAIN), ("a.ts", None)]:
        with pytest.raises(TypeError):
            detect_file_references(text, pattern)


def test_order_duplicates_paths_and_capture_spans():
    text = "a.ts, src/a.ts:12:3 and /repo/a.ts; a.ts"
    refs = detect_file_references(text, PLAIN)
    assert [r.path for r in refs] == ["a.ts", "src/a.ts", "/repo/a.ts", "a.ts"]
    assert [r.filename for r in refs] == ["a.ts"] * 4
    assert all(text[r.start:r.end] == r.path for r in refs)
    with pytest.raises(AttributeError):
        refs[0].path = "other.ts"


@pytest.mark.parametrize("delimiter", ['"', "'", '`'])
def test_explicit_quoted_space_syntax(delimiter):
    text = f"See {delimiter}src/my file.ts{delimiter}:10, now."
    refs = detect_file_references(text, PATTERN)
    assert [r.path for r in refs] == ["src/my file.ts"]
    assert refs[0].filename == "my file.ts"


@pytest.mark.parametrize("path,kind", [
    ("a.ts", "production_code"), ("a.tsx", "production_code"),
    ("a.js", "production_code"), ("a.jsx", "production_code"),
    ("a.spec.ts", "test_code"), ("a.test.ts", "test_code"),
    ("a.d.ts", "declaration"), ("a.spec.d.ts", "declaration"),
    ("a.json", "non_code"), ("a.log", "non_code"), ("a.TS", "non_code"),
])
def test_lexical_classification(path, kind):
    refs = detect_file_references(path, re.compile(PLAIN))
    assert len(refs) == 1
    assert refs[0].kind == kind


def test_external_regex_is_authoritative_and_log_is_only_mention(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("filesystem read")
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(Path, "exists", forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    text = "log: failed parsing FILE[src/foo.ts]"
    refs = detect_file_references(text, r'FILE\[(?P<path>[^\]]+)\]')
    assert [(r.path, r.kind) for r in refs] == [("src/foo.ts", "production_code")]
    assert not hasattr(refs[0], "intent")
    assert detect_file_references("src/foo.ts", r'FILE\[(?P<path>[^\]]+)\]') == []


@pytest.mark.parametrize("pattern", ["[", r'(foo)', r'(?P<filename>.+)'])
def test_invalid_pattern_or_missing_capture(pattern):
    with pytest.raises(ValueError):
        detect_file_references("foo.ts", pattern)


@pytest.mark.parametrize("text,pattern", [
    ("x", r'(?P<path>)'), ("x", r'(?P<path>foo)?x'),
    ("a\x00.ts", r'(?P<path>.+)'), ("a\n.ts", r'(?P<path>[\s\S]+)'),
    (r'C:\src\a.ts', r'(?P<path>.+)'),
])
def test_invalid_or_unsupported_captured_path_explicitly_rejected(text, pattern):
    with pytest.raises(ValueError):
        detect_file_references(text, pattern)


def test_regex_can_capture_full_space_path_without_truncation():
    refs = detect_file_references("<my directory/my file.ts>", r'<(?P<path>[^>]+)>')
    assert refs[0].path == "my directory/my file.ts"
