"""Tests for cairn discovery via the ``.cairn`` marker (ADR-0006)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cairn.cli.app import app
from cairn.errors import NotACairnError
from cairn.paths import (
    MARKER_FILE,
    find_cairn_root,
    has_marker,
    is_cairn_root,
    resolve_cairn,
    write_marker,
)

runner = CliRunner()


def _make_legacy_cairn(root: Path) -> None:
    """Build a minimal pre-marker cairn (state/collaborators.yaml only)."""
    (root / "state").mkdir(parents=True)
    (root / "state" / "collaborators.yaml").write_text("[]\n", encoding="utf-8")


def _make_marker_cairn(root: Path, name: str = "demo") -> None:
    """Build a minimal post-marker cairn (just the .cairn file)."""
    root.mkdir(parents=True, exist_ok=True)
    write_marker(root, name)


def test_marker_file_identifies_cairn_root(tmp_path: Path):
    _make_marker_cairn(tmp_path / "c", name="c")
    assert is_cairn_root(tmp_path / "c") is True
    assert has_marker(tmp_path / "c") is True


def test_legacy_marker_still_identifies_cairn_root(tmp_path: Path):
    """Pre-marker cairns must remain discoverable (transitional fallback)."""
    _make_legacy_cairn(tmp_path / "c")
    assert is_cairn_root(tmp_path / "c") is True
    assert has_marker(tmp_path / "c") is False


def test_random_directory_is_not_a_cairn(tmp_path: Path):
    (tmp_path / "not-a-cairn").mkdir()
    assert is_cairn_root(tmp_path / "not-a-cairn") is False


def test_cwd_walk_finds_marker_cairn_from_subdirectory(tmp_path: Path):
    cairn = tmp_path / "c"
    _make_marker_cairn(cairn, name="c")
    deep = cairn / "knowledge" / "findings"
    deep.mkdir(parents=True)
    found = find_cairn_root(deep)
    assert found == cairn.resolve()


def test_cwd_walk_finds_legacy_cairn_from_subdirectory(tmp_path: Path):
    cairn = tmp_path / "c"
    _make_legacy_cairn(cairn)
    (cairn / "knowledge").mkdir()
    found = find_cairn_root(cairn / "knowledge")
    assert found == cairn.resolve()


def test_cwd_walk_raises_when_no_cairn_above(tmp_path: Path):
    (tmp_path / "elsewhere").mkdir()
    with pytest.raises(NotACairnError):
        find_cairn_root(tmp_path / "elsewhere")


def test_write_marker_is_idempotent(tmp_path: Path):
    tmp_path.joinpath(".cairn").unlink(missing_ok=True)
    write_marker(tmp_path, "demo")
    first = (tmp_path / MARKER_FILE).read_text(encoding="utf-8")
    write_marker(tmp_path, "demo")  # second call, same name
    second = (tmp_path / MARKER_FILE).read_text(encoding="utf-8")
    assert first == second
    assert 'name = "demo"' in first


def test_resolve_cairn_returns_paths_object(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    cairn = tmp_path / "c"
    _make_marker_cairn(cairn, name="c")
    monkeypatch.chdir(cairn)
    paths = resolve_cairn()
    assert paths.root == cairn.resolve()


# ---------------------------------------------------------------------------
# `cairn init` ships the marker, and is idempotent on existing cairn roots
# ---------------------------------------------------------------------------


def test_cairn_init_creates_marker_file(cwd: Path):
    result = runner.invoke(app, ["init", "with-marker"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    marker = cwd / "with-marker" / MARKER_FILE
    assert marker.is_file(), "cairn init must ship a .cairn marker"
    assert 'name = "with-marker"' in marker.read_text(encoding="utf-8")


def test_cairn_init_backfills_marker_on_pre_marker_cairn(cwd: Path):
    """Running `cairn init` on an existing legacy cairn is idempotent: it
    adds the marker and reports success rather than erroring on
    'directory already exists'."""
    legacy = cwd / "old-cairn"
    _make_legacy_cairn(legacy)
    assert not has_marker(legacy)

    result = runner.invoke(app, ["init", "old-cairn"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert has_marker(legacy)
    assert "Backfilled" in result.output


def test_cairn_init_no_op_on_complete_cairn(cwd: Path):
    """Running `cairn init` on an already-marker-equipped cairn is also
    idempotent: no error, no rewrite, clear message."""
    cairn = cwd / "done-cairn"
    _make_marker_cairn(cairn, name="done-cairn")

    result = runner.invoke(app, ["init", "done-cairn"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert "already a cairn" in result.output


def test_cairn_init_errors_on_non_cairn_existing_dir(cwd: Path):
    """A pre-existing directory that's NOT a cairn still errors (without --force)."""
    (cwd / "random").mkdir()
    (cwd / "random" / "stuff.txt").write_text("hi", encoding="utf-8")

    result = runner.invoke(app, ["init", "random"], catch_exceptions=False)
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# `cairn validate` warns when marker is missing
# ---------------------------------------------------------------------------


def test_validate_warns_on_missing_marker(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    """A legacy cairn (no marker) validates with a warning, not an error."""
    runner.invoke(app, ["init", "warn-target"], catch_exceptions=False)
    root = cwd / "warn-target"
    (root / MARKER_FILE).unlink()
    monkeypatch.chdir(root)

    result = runner.invoke(app, ["validate"], catch_exceptions=False)
    assert result.exit_code == 0, result.output  # warning, not error
    assert ".cairn" in result.output
    assert "Backfill" in result.output


def test_validate_clean_on_complete_cairn(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    runner.invoke(app, ["init", "clean-target"], catch_exceptions=False)
    monkeypatch.chdir(cwd / "clean-target")
    result = runner.invoke(app, ["validate"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert "OK" in result.output
