"""Deterministic, repository-confined production TypeScript path resolution."""
from dataclasses import dataclass
import os
from pathlib import Path

from .file_reference_utils import FileReference


@dataclass(frozen=True)
class Resolution:
    status: str
    selected_path: Path | None = None
    candidates: tuple[Path, ...] = ()


def _is_production_typescript(path: Path) -> bool:
    return path.name.endswith(".ts") and not path.name.endswith((".spec.ts", ".test.ts", ".d.ts"))


def resolve_file(reference: str | FileReference, *, cwd: str | Path,
                 repository_root: str | Path) -> Resolution:
    """Resolve exact paths first; search only missing basename-only references.

    Outputs are canonical absolute Paths. Only case-sensitive production `.ts`
    files are eligible, including the canonical targets of symlinks. Search
    excludes `.git`, `node_modules`, and symlink directories. Any scan failure
    prevents selection (an unseen duplicate may exist). No source contents are
    read or written.
    """
    raw = reference.path if isinstance(reference, FileReference) else reference
    if not isinstance(raw, str):
        raise TypeError("reference must be a string or FileReference")
    if not raw.strip() or "\\" in raw or any(ord(c) < 32 for c in raw):
        raise ValueError("reference must be a nonempty POSIX path without control characters")
    root = Path(repository_root).resolve(strict=True)
    current = Path(cwd).resolve(strict=True)
    if not root.is_dir() or not current.is_dir() or not current.is_relative_to(root):
        raise ValueError("cwd must be a directory within repository_root")
    requested = Path(raw)
    name = requested.name
    if not _is_production_typescript(requested):
        return Resolution("excluded")
    try:
        exact = (requested if requested.is_absolute() else current / requested).resolve()
        if not exact.is_relative_to(root):
            return Resolution("outside_repository")
        if not _is_production_typescript(exact):
            return Resolution("excluded")
        try:
            stat = exact.stat()
        except FileNotFoundError:
            stat = None
        if stat is not None:
            if not exact.is_file():
                return Resolution("not_file")
            if not os.access(exact, os.R_OK):
                return Resolution("inaccessible")
            return Resolution("resolved", exact, (exact,))
        # Explicit paths never fall back to an unrelated same-named file.
        if requested.is_absolute() or "/" in raw:
            return Resolution("missing")
        matches: set[Path] = set()
        errors: list[OSError] = []
        outside = False
        for directory, dirs, files in os.walk(root, topdown=True, onerror=errors.append, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in {".git", "node_modules"}
                             and not (Path(directory) / d).is_symlink())
            if name not in files:
                continue
            candidate = (Path(directory) / name).resolve()
            if not candidate.is_relative_to(root):
                outside = True
                continue
            if not _is_production_typescript(candidate):
                continue
            if candidate.is_file() and os.access(candidate, os.R_OK):
                matches.add(candidate)
            else:
                errors.append(PermissionError(str(candidate)))
        candidates = tuple(sorted(matches))
        if errors:
            return Resolution("inaccessible", candidates=candidates)
        if len(candidates) > 1:
            return Resolution("ambiguous", candidates=candidates)
        if candidates:
            return Resolution("resolved", candidates[0], candidates)
        return Resolution("outside_repository" if outside else "missing")
    except (OSError, RuntimeError):
        return Resolution("inaccessible")
