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
    assert not pointer.is_remote


def test_write_and_load_path_pointer_relative(tmp_path: Path):
    project = tmp_path / "proj"
    project.mkdir()
    cairn = tmp_path / "proj-cairn"
    cairn.mkdir()
    written = write_pointer(project, path=cairn)
    pointer = load_pointer(written)
    assert pointer.name is None
    assert pointer.path == cairn.resolve()
    assert pointer.endpoint is None
    # Confirm the on-disk content uses a relative path for portability.
    content = written.read_text()
    assert "../proj-cairn" in content
    assert not pointer.is_remote


def test_write_and_load_remote_mcp_pointer(tmp_path: Path):
    """endpoint + name together → remote-MCP mode."""
    project = tmp_path / "proj"
    project.mkdir()
    written = write_pointer(
        project,
        endpoint="https://mcp.example.com/mcp",
        name="my-cairn",
    )
    assert written.is_file()
    pointer = load_pointer(written)
    assert pointer.endpoint == "https://mcp.example.com/mcp"
    assert pointer.name == "my-cairn"
    assert pointer.path is None
    assert pointer.is_remote
    # Both fields should appear in the file.
    content = written.read_text()
    assert 'endpoint = "https://mcp.example.com/mcp"' in content
    assert 'name = "my-cairn"' in content


def test_load_remote_mcp_pointer(tmp_path: Path):
    """Loading a hand-written remote-MCP cairn.toml."""
    target = tmp_path / "cairn.toml"
    target.write_text(
        '[cairn]\nendpoint = "https://mcp.example.com/mcp"\nname = "my-cairn"\n',
        encoding="utf-8",
    )
    pointer = load_pointer(target)
    assert pointer.endpoint == "https://mcp.example.com/mcp"
    assert pointer.name == "my-cairn"
    assert pointer.is_remote


def test_write_requires_valid_combination(tmp_path: Path):
    project = tmp_path / "proj"
    project.mkdir()
    # Nothing → error
    with pytest.raises(CairnTomlError, match="one of"):
        write_pointer(project)
    # path + name → error
    with pytest.raises(CairnTomlError, match="cannot be combined"):
        write_pointer(project, path=tmp_path, name="demo")
    # path + endpoint → error
    with pytest.raises(CairnTomlError, match="cannot be combined"):
        write_pointer(project, path=tmp_path, endpoint="https://x.test/mcp")
    # endpoint alone → error
    with pytest.raises(CairnTomlError, match="requires name"):
        write_pointer(project, endpoint="https://x.test/mcp")


def test_load_rejects_endpoint_without_name(tmp_path: Path):
    target = tmp_path / "cairn.toml"
    target.write_text(
        '[cairn]\nendpoint = "https://mcp.example.com/mcp"\n', encoding="utf-8"
    )
    with pytest.raises(CairnTomlError, match=r"requires.*name"):
        load_pointer(target)


def test_load_rejects_path_with_name(tmp_path: Path):
    target = tmp_path / "cairn.toml"
    target.write_text(
        '[cairn]\npath = "../cairn"\nname = "demo"\n', encoding="utf-8"
    )
    with pytest.raises(CairnTomlError, match="cannot be combined"):
        load_pointer(target)


def test_load_rejects_empty_table(tmp_path: Path):
    target = tmp_path / "cairn.toml"
    target.write_text("[cairn]\n", encoding="utf-8")
    with pytest.raises(CairnTomlError, match="must specify"):
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


def test_is_remote_false_for_local_modes(tmp_path: Path):
    """CairnPointer.is_remote is False for both local modes."""
    proj = tmp_path / "proj"
    proj.mkdir()
    cairn = tmp_path / "cairn"
    cairn.mkdir()

    name_ptr = load_pointer(write_pointer(proj, name="demo"))
    assert not name_ptr.is_remote

    # Overwrite for the path test
    (proj / "cairn.toml").unlink()
    path_ptr = load_pointer(write_pointer(proj, path=cairn))
    assert not path_ptr.is_remote
