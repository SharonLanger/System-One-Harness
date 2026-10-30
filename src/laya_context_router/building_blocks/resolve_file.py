"""Compatibility facade for the generic, repository-confined TypeScript resolver.

See typescript-helper/README.md, Resolution. Filename acceptance belongs to the
configured detector; this resolver accepts production, test and other files.
"""
from dataclasses import dataclass
from pathlib import Path

from .file_reference_utils import FileReference
from . import typescript


@dataclass(frozen=True)
class Resolution:
    status: str
    selected_path: Path | None = None
    candidates: tuple[Path, ...] = ()


def resolve_file(reference: str | FileReference, *, cwd: str | Path,
                 repository_root: str | Path, node: str = "node",
                 helper: str | Path = typescript.DEFAULT_HELPER,
                 timeout: float = 5.0) -> Resolution:
    """Return legacy Resolution fields using TypeScript's generic lookup policy.

    Exact cwd/root candidates precede whole-component suffix matches. Ambiguity
    never chooses an arbitrary path; I/O failures return ``inaccessible``.
    """
    raw = reference.path if isinstance(reference, FileReference) else reference
    if not isinstance(raw, str):
        raise TypeError("reference must be a string or FileReference")
    outcome = typescript.resolve_reference(raw, cwd=cwd, repository_root=repository_root,
                                          node=node, helper=helper, timeout=timeout)
    if outcome["status"] == "error":
        diagnostic = outcome["diagnostics"][0]
        if diagnostic["code"] == "invalid_input":
            raise ValueError(diagnostic["message"])
        return Resolution("inaccessible")
    data = outcome["data"]
    selected = Path(data["selected_path"]) if data["selected_path"] is not None else None
    return Resolution(data["resolution"], selected, tuple(Path(p) for p in data["candidates"]))
