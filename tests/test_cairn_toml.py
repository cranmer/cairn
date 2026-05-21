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
    assert pointer.mode == "local-registry"


def test_write_and_load_path_pointer_relative(tmp_path: Path):
    project = tmp_path / "proj"
    project.mkdir()
    cairn = tmp_path / "proj-cairn"
    cairn.mkdir()
    written = write_pointer(project, path=cairn)
    pointer = load_pointer(written)
    assert pointer.name is None
    assert pointer.path == cairn.resolve()
    assert pointer.mode == "local-path"
    # Confirm the on-disk content uses a relative path for portability.
    content = written.read_text()
    assert "../proj-cairn" in content


def test_write_and_load_remote_pointer(tmp_path: Path):
    """Remote mode requires both endpoint and name."""
    project = tmp_path / "proj"
    project.mkdir()
    written = write_pointer(
        project, endpoint="https://cairn.example.com", name="my-cairn"
    )
    pointer = load_pointer(written)
    assert pointer.endpoint == "https://cairn.example.com"
    assert pointer.name == "my-cairn"
    assert pointer.path is None
    assert pointer.mode == "remote"
    assert pointer.is_remote is True


def test_write_requires_at_least_one_target(tmp_path: Path):
    project = tmp_path / "proj"
    project.mkdir()
    with pytest.raises(CairnTomlError):
        write_pointer(project)  # nothing


def test_write_rejects_path_and_name(tmp_path: Path):
    project = tmp_path / "proj"
    project.mkdir()
    with pytest.raises(CairnTomlError, match="mutually exclusive"):
        write_pointer(project, path=tmp_path, name="demo")


def test_write_rejects_endpoint_without_name(tmp_path: Path):
    project = tmp_path / "proj"
    project.mkdir()
    with pytest.raises(CairnTomlError, match="endpoint requires name"):
        write_pointer(project, endpoint="https://example.com")


def test_write_rejects_path_and_endpoint(tmp_path: Path):
    project = tmp_path / "proj"
    project.mkdir()
    with pytest.raises(CairnTomlError, match="mutually exclusive"):
        write_pointer(project, path=tmp_path, endpoint="https://example.com")


def test_load_rejects_endpoint_alone(tmp_path: Path):
    """endpoint without name is invalid."""
    target = tmp_path / "cairn.toml"
    target.write_text(
        '[cairn]\nendpoint = "https://example.com"\n', encoding="utf-8"
    )
    with pytest.raises(CairnTomlError, match="name"):
        load_pointer(target)


def test_load_rejects_path_and_name(tmp_path: Path):
    """path + name together is invalid."""
    target = tmp_path / "cairn.toml"
    target.write_text(
        '[cairn]\npath = "/some/path"\nname = "demo"\n', encoding="utf-8"
    )
    with pytest.raises(CairnTomlError):
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


def test_load_rejects_empty_section(tmp_path: Path):
    target = tmp_path / "cairn.toml"
    target.write_text("[cairn]\n", encoding="utf-8")
    with pytest.raises(CairnTomlError, match="pointer"):
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


def test_remote_mode_pointer_is_remote_property(tmp_path: Path):
    proj = tmp_path / "proj"
    proj.mkdir()
    written = write_pointer(proj, endpoint="https://example.com", name="test")
    pointer = load_pointer(written)
    assert pointer.is_remote is True


def test_local_mode_pointer_is_not_remote(tmp_path: Path):
    proj = tmp_path / "proj"
    proj.mkdir()
    written = write_pointer(proj, name="test")
    pointer = load_pointer(written)
    assert pointer.is_remote is False
