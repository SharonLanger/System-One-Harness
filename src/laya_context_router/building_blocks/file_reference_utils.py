"""Pure lexical file mentions; the caller owns the complete path expression."""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class FileReference:
    path: str
    filename: str
    kind: str
    start: int
    end: int


def detect_file_references(text: str, pattern: str | re.Pattern[str]) -> list[FileReference]:
    """Return ordered captures, preserving duplicates and spelling.

    ``pattern`` must have a named ``path`` group containing the entire POSIX
    path, without delimiters or line/column suffixes. Spaces are supported when
    the expression captures them. Expressions determine syntax, not task intent;
    callers must avoid expressions that capture only a suffix of a spaced path.
    Windows backslash paths and control characters are explicitly unsupported.
    No filesystem operations or normalization are performed.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if not isinstance(pattern, (str, re.Pattern)):
        raise TypeError("pattern must be a string or compiled text regex")
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        raise ValueError(f"invalid file-reference regex: {exc}") from exc
    if not isinstance(compiled.pattern, str):
        raise TypeError("pattern must be a text regex")
    if "path" not in compiled.groupindex:
        raise ValueError("file-reference regex requires a named 'path' capture")
    references = []
    for match in compiled.finditer(text):
        path = match.group("path")
        if not path or not path.strip() or "\\" in path or any(ord(c) < 32 for c in path):
            raise ValueError("path capture must be a nonempty POSIX path without control characters")
        filename = path.rsplit("/", 1)[-1]
        if not filename:
            raise ValueError("path capture must contain a filename")
        if filename.endswith(".d.ts"):
            kind = "declaration"
        elif filename.endswith((".spec.ts", ".test.ts")):
            kind = "test_code"
        elif filename.endswith((".ts", ".tsx", ".js", ".jsx")):
            kind = "production_code"
        else:
            kind = "non_code"
        start, end = match.span("path")
        references.append(FileReference(path, filename, kind, start, end))
    return references
