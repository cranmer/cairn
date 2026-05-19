"""Tests for project-repo cairn.toml pointer files (cairn_toml.py)."""

from __future__ import annotations

from pathlib import Path

import pytest

from cairn.cairn_toml import (
    CairnTomlError,
    find_pointer,
    load_pointer,
    write_pointer,
)


def test_write_and_load_name_pointer(tmp_path: Path):
    project = tmp_path / "proj"
    project.mkdir()
    written = write_pointer(project, name="demo")
    assert written.is_file()
    pointer = load_pointer(written)
    assert pointer.name == "demo"
    assert pointer.path is None
    assert pointer.endpoint is None


def test_write_and_load_path_pointer_relative(tmp_path: Path):
    project = tmp_path / "proj"
    project.mkdir()
    cairn = tmp_path / "proj-cairn"
    cairn.mkdir()
    written = write_pointer(project, path=cairn)
    pointer = load_pointer(written)
    assert pointer.name is None
    assert pointer.path == cairn.resolve()
    # Confirm the on-disk content uses a relative path for portability.
    content = written.read_text()
    assert "../proj-cairn" in content


def test_write_and_load_endpoint_pointer(tmp_path: Path):
    project = tmp_path / "proj"
    project.mkdir()
    written = write_pointer(project, endpoint="stdio:cairn mcp")
    pointer = load_pointer(written)
    assert pointer.endpoint == "stdio:cairn mcp"
    assert pointer.name is None
    assert pointer.path is None


def test_write_requires_exactly_one_target(tmp_path: Path):
    project = tmp_path / "proj"
    project.mkdir()
    with pytest.raises(CairnTomlError, match="exactly one"):
        write_pointer(project)  # nothing
    with pytest.raises(CairnTomlError, match="exactly one"):
        write_pointer(project, name="demo", endpoint="x")


def test_load_rejects_multiple_targets(tmp_path: Path):
    target = tmp_path / "cairn.toml"
    target.write_text(
        "[cairn]\nname = \"demo\"\nendpoint = \"x\"\n", encoding="utf-8"
    )
    with pytest.raises(CairnTomlError, match="exactly one"):
        load_pointer(target)


def test_load_rejects_missing_section(tmp_path: Path):
    target = tmp_path / "cairn.toml"
    target.write_text("# nothing here\n", encoding="utf-8")
    with pytest.raises(CairnTomlError, match="missing required"):
        load_pointer(target)


def test_load_rejects_invalid_toml(tmp_path: Path):
    target = tmp_path / "cairn.toml"
    target.write_text("this : is = not valid\n", encoding="utf-8")
    with pytest.raises(CairnTomlError, match="invalid TOML"):
        load_pointer(target)


def test_find_pointer_walks_upward(tmp_path: Path):
    proj = tmp_path / "proj"
    deep = proj / "src" / "module" / "deep"
    deep.mkdir(parents=True)
    write_pointer(proj, name="demo")
    found = find_pointer(deep)
    assert found is not None
    assert found == (proj / "cairn.toml").resolve()


def test_find_pointer_returns_none_when_absent(tmp_path: Path):
    nowhere = tmp_path / "nowhere"
    nowhere.mkdir()
    assert find_pointer(nowhere) is None


def test_pointer_project_repo_root(tmp_path: Path):
    proj = tmp_path / "proj"
    proj.mkdir()
    written = write_pointer(proj, name="demo")
    pointer = load_pointer(written)
    assert pointer.project_repo_root == proj.resolve()
