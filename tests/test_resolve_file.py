from pathlib import Path

import pytest

from laya_context_router.building_blocks.resolve_file import resolve_file


def make(root, name, content="export function x() {}"):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path.resolve()


def test_exact_paths_win_over_duplicate_basename_and_nested_cwd(tmp_path):
    wanted = make(tmp_path, "src/a.ts")
    make(tmp_path, "other/a.ts")
    cwd = tmp_path / "src"
    for reference in ["a.ts", "./a.ts", str(wanted), "../src/a.ts"]:
        result = resolve_file(reference, cwd=cwd, repository_root=tmp_path)
        assert result.status == "resolved"
        assert result.selected_path == wanted
        assert result.candidates == (wanted,)


def test_basename_search_unique_ambiguous_and_stable(tmp_path):
    first = make(tmp_path, "a/x.ts")
    assert resolve_file("x.ts", cwd=tmp_path, repository_root=tmp_path).selected_path == first
    second = make(tmp_path, "z/x.ts")
    for _ in range(2):
        result = resolve_file("x.ts", cwd=tmp_path, repository_root=tmp_path)
        assert result.status == "ambiguous"
        assert result.selected_path is None
        assert result.candidates == (first, second)


def test_missing_explicit_path_never_falls_back_and_directories(tmp_path):
    make(tmp_path, "actual/x.ts")
    for reference, status in [("missing/x.ts", "missing"), ("absent.ts", "missing"), ("actual", "not_file")]:
        result = resolve_file(reference, cwd=tmp_path, repository_root=tmp_path)
        assert result.status == status
        assert result.selected_path is None
    (tmp_path / "dir.ts").mkdir()
    assert resolve_file("dir.ts", cwd=tmp_path, repository_root=tmp_path).status == "not_file"


@pytest.mark.parametrize("suffix", ["spec.ts", "test.ts", "d.ts", "tsx", "js", "json", "TS"])
def test_generic_resolver_accepts_all_explicit_file_types(tmp_path, suffix):
    path = make(tmp_path, f"src/a.{suffix}")
    for reference in [path.name, str(path)]:
        result = resolve_file(reference, cwd=tmp_path, repository_root=tmp_path)
        assert result.status == "resolved"
        assert result.selected_path == path


def test_traversal_symlink_escape_and_in_root_symlink(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    outside = make(tmp_path, "outside.ts")
    inside = make(root, "src/inside.ts")
    (root / "escape.ts").symlink_to(outside)
    (root / "alias.ts").symlink_to(inside)
    for ref in ["../outside.ts", str(outside), "escape.ts"]:
        result = resolve_file(ref, cwd=root, repository_root=root)
        assert result.status == "outside_repository"
        assert result.selected_path is None
    assert resolve_file("alias.ts", cwd=root, repository_root=root).selected_path == inside


@pytest.mark.parametrize("target_name", ["target.spec.ts", "target.test.ts", "target.d.ts", "target.txt", "target.TS"])
def test_exact_symlink_accepts_generic_canonical_targets(tmp_path, target_name):
    target = make(tmp_path, f"src/{target_name}")
    alias = tmp_path / "alias.ts"
    alias.symlink_to(target)
    for reference in ["alias.ts", "./alias.ts", str(alias)]:
        result = resolve_file(reference, cwd=tmp_path, repository_root=tmp_path)
        assert result.status == "resolved"
        assert result.selected_path == target
        assert result.candidates == (target,)


@pytest.mark.parametrize("target_name", ["target.spec.ts", "target.test.ts", "target.d.ts", "target.txt", "target.TS"])
def test_basename_scan_accepts_and_deduplicates_generic_canonical_targets(tmp_path, target_name):
    target = make(tmp_path, f"targets/{target_name}")
    alias = tmp_path / "aliases" / "alias.ts"
    alias.parent.mkdir()
    alias.symlink_to(target)
    result = resolve_file("alias.ts", cwd=tmp_path, repository_root=tmp_path)
    assert result.status == "resolved"
    assert result.selected_path == target
    assert result.candidates == (target,)

    valid = make(tmp_path, "production/alias.ts")
    result = resolve_file("alias.ts", cwd=tmp_path, repository_root=tmp_path)
    assert result.status == "ambiguous"
    assert result.selected_path is None
    assert result.candidates == tuple(sorted((target, valid)))


def test_basename_scan_preserves_and_deduplicates_production_symlink_targets(tmp_path):
    target = make(tmp_path, "production/target.ts")
    for directory in ["a", "b"]:
        alias = tmp_path / directory / "alias.ts"
        alias.parent.mkdir()
        alias.symlink_to(target)
    result = resolve_file("alias.ts", cwd=tmp_path, repository_root=tmp_path)
    assert result.status == "resolved"
    assert result.selected_path == target
    assert result.candidates == (target,)


def test_symlink_directory_not_traversed_and_basename_outside_file_not_selected(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    outside = make(tmp_path, "elsewhere/secret.ts")
    (root / "escape").symlink_to(outside.parent, target_is_directory=True)
    assert resolve_file("secret.ts", cwd=root, repository_root=root).status == "missing"


def test_unicode_spaces_and_no_mutation(tmp_path):
    path = make(tmp_path, "some dir/מספר my file.ts", "// 😀\r\nexport function f() {}")
    before = {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    for reference in ["some dir/מספר my file.ts", "מספר my file.ts", str(path)]:
        assert resolve_file(reference, cwd=tmp_path, repository_root=tmp_path).selected_path == path
    after = {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert after == before


def test_helper_io_failure_maps_to_inaccessible(tmp_path, monkeypatch):
    # Filesystem failure injection belongs in the TS suite. This proves adapter mapping.
    monkeypatch.setattr("laya_context_router.building_blocks.typescript.resolve_reference",
        lambda *args, **kwargs: {"status": "error", "data": None,
            "diagnostics": [{"code": "io_error", "message": "controlled scan failure"}]})
    result = resolve_file("a.ts", cwd=tmp_path, repository_root=tmp_path)
    assert result.status == "inaccessible"
    assert result.selected_path is None


def test_configuration_and_invalid_reference(tmp_path):
    for reference in ["", " ", r'C:\x.ts', "a\x00.ts"]:
        with pytest.raises(ValueError):
            resolve_file(reference, cwd=tmp_path, repository_root=tmp_path)
    with pytest.raises(ValueError):
        resolve_file("a.ts", cwd=tmp_path.parent, repository_root=tmp_path)
