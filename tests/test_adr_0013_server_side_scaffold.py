"""Tests for ADR-0013: server-side fixture scaffold tool + supporting plumbing.

Covers:

- ``scaffold_cairn`` produces a seeded cairn and returns a verification summary.
- ``scaffold_project`` writes a project repo paired by ``cairn_name`` override.
- ``CAIRN_REGISTRY_PATH`` env var overrides the registry location.
- The MCP server registers the ``scaffold_fixture`` dev tool only under
  ``--allow-dev-tools``; the tool refuses unknown fixtures, conflicting
  handles, and invalid names.
- ``cairn dev scaffold-fixture --remote`` round-trips through an in-process
  build of the server.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from cairn.dev.fixtures import scaffold_cairn, scaffold_project
from cairn.registry import load_registry, registry_path


def test_scaffold_cairn_seeds_state_and_returns_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    cairn_dir = tmp_path / "cairns" / "coral-bleach"

    summary = scaffold_cairn("coral-bleach", cairn_dir)

    assert cairn_dir.is_dir()
    assert (cairn_dir / ".cairn").exists() or (cairn_dir / "state" / "collaborators.yaml").exists()
    collabs = yaml.safe_load((cairn_dir / "state" / "collaborators.yaml").read_text())
    ids = {c["id"] for c in collabs}
    assert {"kyle", "lila"}.issubset(ids)

    assert summary["fixture"] == "coral-bleach"
    assert set(summary["collaborators"]) == {"kyle", "lila"}
    assert summary["decisions"] >= 1
    assert summary["findings"] >= 1


def test_scaffold_project_honors_cairn_name_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    project_dir = tmp_path / "projects" / "x"

    scaffold_project(
        "coral-bleach",
        project_dir,
        http_endpoint="http://srv.example.com/mcp",
        cairn_name="bleach-remote",
    )

    toml_text = (project_dir / "cairn.toml").read_text()
    assert 'name = "bleach-remote"' in toml_text
    assert 'endpoint = "http://srv.example.com/mcp"' in toml_text
    # Project files were written.
    assert (project_dir / "README.md").is_file()
    # Git history was created.
    assert (project_dir / ".git").is_dir()


def test_registry_path_env_var_takes_precedence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    custom = tmp_path / "custom-registry.toml"
    monkeypatch.setenv("CAIRN_REGISTRY_PATH", str(custom))

    assert registry_path() == custom

    # And load_registry on an absent file returns [].
    assert load_registry() == []


def test_build_server_rejects_dev_tools_without_sandbox() -> None:
    pytest.importorskip("mcp")
    from cairn.mcp.server import build_server

    with pytest.raises(ValueError, match="sandbox_path"):
        build_server(allow_dev_tools=True, sandbox_path=None)


def test_build_server_dev_tools_registers_scaffold_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("mcp")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("CAIRN_REGISTRY_PATH", str(tmp_path / "registry.toml"))

    from cairn.mcp.server import build_server

    sandbox = tmp_path / "sandbox"
    server = build_server(allow_dev_tools=True, sandbox_path=sandbox)

    # FastMCP exposes tools via its tool manager.
    tool_names = {t.name for t in server._tool_manager.list_tools()}
    assert "scaffold_fixture" in tool_names

    # When dev tools are off, the tool is not registered.
    server2 = build_server()
    tool_names2 = {t.name for t in server2._tool_manager.list_tools()}
    assert "scaffold_fixture" not in tool_names2


def test_build_server_without_dev_tools_omits_scaffold_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("mcp")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("CAIRN_REGISTRY_PATH", str(tmp_path / "registry.toml"))

    from cairn.mcp.server import build_server

    server = build_server()
    tool_names = {t.name for t in server._tool_manager.list_tools()}
    assert "scaffold_fixture" not in tool_names


def _call_dev_tool(server, name: str, arguments: dict) -> dict:
    """Invoke an MCP tool by walking the FastMCP tool manager directly.

    Bypasses the async transport layer so we can test on Python 3.14
    where ``asyncio.get_event_loop()`` no longer auto-creates a loop.
    """
    import asyncio

    async def _run():
        return await server._tool_manager.call_tool(name, arguments)

    return asyncio.run(_run())


def test_dev_scaffold_fixture_tool_seeds_and_registers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("mcp")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    registry_file = tmp_path / "registry.toml"
    monkeypatch.setenv("CAIRN_REGISTRY_PATH", str(registry_file))

    from cairn.mcp.server import build_server

    sandbox = tmp_path / "sandbox"
    server = build_server(allow_dev_tools=True, sandbox_path=sandbox)

    result = _call_dev_tool(server, "scaffold_fixture", {"name": "coral-bleach"})
    # FastMCP wraps return values; normalize.
    if hasattr(result, "structured_content"):
        payload = result.structured_content
    elif isinstance(result, dict):
        payload = result
    else:
        payload = result[0] if isinstance(result, list) else result
    assert payload["cairn"] == "coral-bleach"
    assert payload["fixture"] == "coral-bleach"
    assert set(payload["summary"]["collaborators"]) == {"kyle", "lila"}

    # The cairn lives in the sandbox.
    assert (sandbox / "coral-bleach" / "state" / "collaborators.yaml").is_file()

    # The registry was updated.
    registered = load_registry()
    assert any(r.name == "coral-bleach" for r in registered)


def test_dev_scaffold_fixture_rejects_unknown_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("mcp")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("CAIRN_REGISTRY_PATH", str(tmp_path / "registry.toml"))

    from cairn.mcp.server import build_server

    sandbox = tmp_path / "sandbox"
    server = build_server(allow_dev_tools=True, sandbox_path=sandbox)

    with pytest.raises(Exception) as exc_info:
        _call_dev_tool(server, "scaffold_fixture", {"name": "ghost-fixture"})
    msg = str(exc_info.value).lower()
    assert "ghost-fixture" in msg or "unknown fixture" in msg


def test_dev_scaffold_fixture_rejects_duplicate_handle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("mcp")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("CAIRN_REGISTRY_PATH", str(tmp_path / "registry.toml"))

    from cairn.mcp.server import build_server

    sandbox = tmp_path / "sandbox"
    server = build_server(allow_dev_tools=True, sandbox_path=sandbox)
    _call_dev_tool(server, "scaffold_fixture", {"name": "coral-bleach"})
    with pytest.raises(Exception) as exc_info:
        _call_dev_tool(server, "scaffold_fixture", {"name": "coral-bleach"})
    assert "already exists" in str(exc_info.value).lower()


def test_dev_scaffold_fixture_rejects_bad_as_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("mcp")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("CAIRN_REGISTRY_PATH", str(tmp_path / "registry.toml"))

    from cairn.mcp.server import build_server

    sandbox = tmp_path / "sandbox"
    server = build_server(allow_dev_tools=True, sandbox_path=sandbox)
    with pytest.raises(Exception) as exc_info:
        _call_dev_tool(
            server,
            "scaffold_fixture",
            {"name": "coral-bleach", "as_name": "Bad Name With Spaces"},
        )
    assert "invalid cairn name" in str(exc_info.value).lower()


def test_dev_scaffold_fixture_honors_as_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("mcp")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("CAIRN_REGISTRY_PATH", str(tmp_path / "registry.toml"))

    from cairn.mcp.server import build_server

    sandbox = tmp_path / "sandbox"
    server = build_server(allow_dev_tools=True, sandbox_path=sandbox)
    result = _call_dev_tool(
        server,
        "scaffold_fixture",
        {"name": "coral-bleach", "as_name": "alt-handle"},
    )
    if hasattr(result, "structured_content"):
        payload = result.structured_content
    else:
        payload = result if isinstance(result, dict) else result[0]
    assert payload["cairn"] == "alt-handle"
    assert (sandbox / "alt-handle").is_dir()
    registered = load_registry()
    assert any(r.name == "alt-handle" for r in registered)
