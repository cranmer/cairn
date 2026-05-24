"""Tests for the user-level MCP registry (registry.py)."""

from __future__ import annotations

from pathlib import Path

import pytest

from cairn.registry import (
    RegisteredCairn,
    RegistryError,
    load_registry,
    register,
    resolve_single_or_named,
    save_registry,
    unregister,
)


@pytest.fixture
def isolated_registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point XDG_CONFIG_HOME at tmp so registry tests don't touch real config."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return tmp_path / "xdg" / "cairn" / "server.toml"


def _make_cairn_root(path: Path) -> None:
    """Create a minimal cairn root (just the marker is enough)."""
    path.mkdir(parents=True, exist_ok=True)
    (path / ".cairn").write_text("name = \"x\"\n", encoding="utf-8")


def test_empty_registry_returns_empty_list(isolated_registry: Path):
    assert load_registry() == []


def test_register_validates_name(isolated_registry: Path, tmp_path: Path):
    cairn = tmp_path / "demo-cairn"
    _make_cairn_root(cairn)
    with pytest.raises(RegistryError, match="invalid cairn name"):
        register("Bad Name", cairn)
    with pytest.raises(RegistryError, match="invalid cairn name"):
        register("UPPER", cairn)


def test_register_requires_existing_cairn_root(isolated_registry: Path, tmp_path: Path):
    nonexistent = tmp_path / "nope"
    with pytest.raises(RegistryError, match="is not a directory"):
        register("demo", nonexistent)
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(RegistryError, match="is not a cairn root"):
        register("demo", plain)


def test_register_and_lookup_roundtrip(isolated_registry: Path, tmp_path: Path):
    cairn = tmp_path / "demo-cairn"
    _make_cairn_root(cairn)
    register("demo", cairn)
    cairns = load_registry()
    assert len(cairns) == 1
    assert cairns[0].name == "demo"
    assert cairns[0].path == cairn.resolve()


def test_register_overwrites_same_name(isolated_registry: Path, tmp_path: Path):
    a = tmp_path / "a-cairn"
    b = tmp_path / "b-cairn"
    _make_cairn_root(a)
    _make_cairn_root(b)
    register("demo", a)
    register("demo", b)
    cairns = load_registry()
    assert len(cairns) == 1
    assert cairns[0].path == b.resolve()


def test_unregister_returns_true_when_removed(isolated_registry: Path, tmp_path: Path):
    cairn = tmp_path / "demo-cairn"
    _make_cairn_root(cairn)
    register("demo", cairn)
    assert unregister("demo") is True
    assert load_registry() == []
    assert unregister("demo") is False


def test_resolve_single_or_named_single_cairn_convenience(
    isolated_registry: Path, tmp_path: Path
):
    cairn = tmp_path / "only-cairn"
    _make_cairn_root(cairn)
    register("only", cairn)
    # No name passed → returns the single registered cairn.
    result = resolve_single_or_named(None)
    assert result.name == "only"


def test_resolve_single_or_named_requires_name_when_multiple(
    isolated_registry: Path, tmp_path: Path
):
    for name in ("a", "b"):
        c = tmp_path / f"{name}-cairn"
        _make_cairn_root(c)
        register(name, c)
    with pytest.raises(RegistryError) as exc_info:
        resolve_single_or_named(None)
    msg = str(exc_info.value)
    assert "multiple cairns registered" in msg
    # The error must list the registered cairn names so the caller knows what
    # they can pass.
    assert "Known: a, b" in msg
    # And it must mention the cairn.toml-paired-cwd convention, which is the
    # canonical way an in-repo agent knows which cairn to choose.
    assert "cairn.toml" in msg


def test_resolve_single_or_named_unknown_name(isolated_registry: Path, tmp_path: Path):
    cairn = tmp_path / "demo-cairn"
    _make_cairn_root(cairn)
    register("demo", cairn)
    with pytest.raises(RegistryError, match="no cairn named 'ghost'"):
        resolve_single_or_named("ghost")


def test_resolve_when_no_cairns_registered(isolated_registry: Path):
    with pytest.raises(RegistryError, match="no cairns registered"):
        resolve_single_or_named(None)


def test_corrupt_registry_file_raises(isolated_registry: Path):
    isolated_registry.parent.mkdir(parents=True)
    isolated_registry.write_text("this is not = valid TOML : at all\n")
    with pytest.raises(RegistryError, match="not valid TOML"):
        load_registry()


def test_save_and_load_preserves_paths(isolated_registry: Path, tmp_path: Path):
    a = tmp_path / "a-cairn"
    b = tmp_path / "b-cairn"
    _make_cairn_root(a)
    _make_cairn_root(b)
    save_registry(
        [RegisteredCairn("a", a), RegisteredCairn("b", b)]
    )
    loaded = load_registry()
    assert {c.name for c in loaded} == {"a", "b"}
    # Sorted alphabetically
    assert [c.name for c in loaded] == ["a", "b"]
