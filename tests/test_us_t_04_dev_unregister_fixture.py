"""Tests for US-T-04 / ADR-0015: the `unregister_fixture` dev MCP tool and
its companion `cairn dev unregister-fixture` CLI.

The MCP tool is the inverse of ``scaffold_fixture`` (ADR-0013): it drops the
fixture cairn from the dev registry and removes its directory from the
server's sandbox. The CLI wraps the MCP call and optionally cleans up a
client-supplied project repo paired to that fixture.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _call_dev_tool(server, name: str, arguments: dict) -> dict:
    """Invoke an MCP tool via the FastMCP tool manager.

    Mirrors the helper in ``test_adr_0013_server_side_scaffold.py``.
    """
    import asyncio

    async def _run():
        return await server._tool_manager.call_tool(name, arguments)

    return asyncio.run(_run())


def _payload(result) -> dict:
    if hasattr(result, "structured_content"):
        return result.structured_content
    if isinstance(result, dict):
        return result
    return result[0] if isinstance(result, list) else result


# ---------------------------------------------------------------------------
# Server-side: MCP tool registration + gating
# ---------------------------------------------------------------------------


def test_build_server_dev_tools_registers_unregister_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("mcp")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("CAIRN_REGISTRY_PATH", str(tmp_path / "registry.toml"))

    from cairn.mcp.server import build_server

    sandbox = tmp_path / "sandbox"
    server = build_server(allow_dev_tools=True, sandbox_path=sandbox)
    tool_names = {t.name for t in server._tool_manager.list_tools()}
    assert "unregister_fixture" in tool_names


def test_unregister_fixture_absent_without_dev_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("mcp")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("CAIRN_REGISTRY_PATH", str(tmp_path / "registry.toml"))

    from cairn.mcp.server import build_server

    server = build_server()
    tool_names = {t.name for t in server._tool_manager.list_tools()}
    assert "unregister_fixture" not in tool_names


# ---------------------------------------------------------------------------
# Server-side: MCP tool behavior
# ---------------------------------------------------------------------------


def _build_server_and_scaffold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, fixture: str = "coral-bleach"
):
    """Build a dev-tools server and scaffold one fixture into its sandbox."""
    pytest.importorskip("mcp")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("CAIRN_REGISTRY_PATH", str(tmp_path / "registry.toml"))

    from cairn.mcp.server import build_server

    sandbox = tmp_path / "sandbox"
    server = build_server(allow_dev_tools=True, sandbox_path=sandbox)
    _call_dev_tool(server, "scaffold_fixture", {"name": fixture})
    return server, sandbox


def test_unregister_fixture_removes_registry_and_sandbox_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from cairn.registry import load_registry

    server, sandbox = _build_server_and_scaffold(tmp_path, monkeypatch)

    assert (sandbox / "coral-bleach" / "state" / "collaborators.yaml").is_file()
    assert any(r.name == "coral-bleach" for r in load_registry())

    payload = _payload(
        _call_dev_tool(server, "unregister_fixture", {"name": "coral-bleach"})
    )

    assert payload == {
        "unregistered": True,
        "cairn": "coral-bleach",
        "removed_path": str((sandbox / "coral-bleach").resolve()),
        "kept_files": False,
        "reason": None,
    }
    assert not (sandbox / "coral-bleach").exists()
    assert not any(r.name == "coral-bleach" for r in load_registry())


def test_unregister_fixture_idempotent_when_not_registered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("mcp")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("CAIRN_REGISTRY_PATH", str(tmp_path / "registry.toml"))

    from cairn.mcp.server import build_server

    server = build_server(allow_dev_tools=True, sandbox_path=tmp_path / "sandbox")

    payload = _payload(
        _call_dev_tool(server, "unregister_fixture", {"name": "ghost-fixture"})
    )

    assert payload["unregistered"] is False
    assert payload["cairn"] == "ghost-fixture"
    assert payload["removed_path"] is None
    assert payload["reason"] == "not_registered"


def test_unregister_fixture_idempotent_called_twice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    server, _ = _build_server_and_scaffold(tmp_path, monkeypatch)

    # First call removes.
    first = _payload(
        _call_dev_tool(server, "unregister_fixture", {"name": "coral-bleach"})
    )
    assert first["unregistered"] is True

    # Second call is a no-op success.
    second = _payload(
        _call_dev_tool(server, "unregister_fixture", {"name": "coral-bleach"})
    )
    assert second["unregistered"] is False
    assert second["reason"] == "not_registered"


def test_unregister_fixture_keep_files_preserves_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from cairn.registry import load_registry

    server, sandbox = _build_server_and_scaffold(tmp_path, monkeypatch)

    payload = _payload(
        _call_dev_tool(
            server,
            "unregister_fixture",
            {"name": "coral-bleach", "keep_files": True},
        )
    )

    assert payload["unregistered"] is True
    assert payload["kept_files"] is True
    assert payload["removed_path"] is None
    # Registry entry gone, but the directory still on disk.
    assert not any(r.name == "coral-bleach" for r in load_registry())
    assert (sandbox / "coral-bleach" / "state" / "collaborators.yaml").is_file()


def test_unregister_fixture_skips_dir_outside_sandbox(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If someone registers a cairn at a path outside the sandbox, the tool
    must unregister it but leave the directory alone."""
    pytest.importorskip("mcp")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("CAIRN_REGISTRY_PATH", str(tmp_path / "registry.toml"))

    from cairn.dev.fixtures import scaffold_cairn
    from cairn.mcp.server import build_server
    from cairn.registry import load_registry, register

    sandbox = tmp_path / "sandbox"
    server = build_server(allow_dev_tools=True, sandbox_path=sandbox)

    # Scaffold the cairn outside the sandbox and register it by hand.
    outside_dir = tmp_path / "outside" / "rogue"
    scaffold_cairn("coral-bleach", outside_dir)
    register("rogue", outside_dir)
    assert outside_dir.is_dir()

    payload = _payload(
        _call_dev_tool(server, "unregister_fixture", {"name": "rogue"})
    )

    assert payload["unregistered"] is True
    assert payload["kept_files"] is True
    assert payload["removed_path"] is None
    assert payload["reason"] == "path_outside_sandbox"
    # Registry entry gone, but the directory survives.
    assert not any(r.name == "rogue" for r in load_registry())
    assert outside_dir.is_dir()


def test_unregister_fixture_handles_already_missing_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import shutil

    from cairn.registry import load_registry

    server, sandbox = _build_server_and_scaffold(tmp_path, monkeypatch)

    # Simulate a crash that left the registry referencing a missing dir.
    shutil.rmtree(sandbox / "coral-bleach")

    payload = _payload(
        _call_dev_tool(server, "unregister_fixture", {"name": "coral-bleach"})
    )

    assert payload["unregistered"] is True
    assert payload["removed_path"] is None
    assert payload["kept_files"] is False
    assert not any(r.name == "coral-bleach" for r in load_registry())


# ---------------------------------------------------------------------------
# Client-side: CLI command
# ---------------------------------------------------------------------------


def _stub_call_tool(payloads: list[dict], calls: list[dict]):
    """A stub that pops payloads in order and records every call."""

    def _stub(endpoint, tool_name, arguments, *, token=None):
        calls.append(
            {
                "endpoint": endpoint,
                "tool_name": tool_name,
                "arguments": arguments,
                "token": token,
            }
        )
        return payloads.pop(0)

    return _stub


def test_dev_unregister_fixture_cli_via_remote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typer.testing import CliRunner

    from cairn.cli.app import app

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("CAIRN_BEARER_TOKEN", "tok")

    calls: list[dict] = []
    monkeypatch.setattr(
        "cairn.mcp.remote.call_tool",
        _stub_call_tool(
            [
                {
                    "unregistered": True,
                    "cairn": "shared-physics-paper",
                    "removed_path": "/srv/sandbox/shared-physics-paper",
                    "kept_files": False,
                    "reason": None,
                }
            ],
            calls,
        ),
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "dev",
            "unregister-fixture",
            "shared-physics-paper",
            "--remote",
            "http://srv.example.com/mcp",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "unregistered cairn=shared-physics-paper" in result.output
    assert "removed server sandbox dir" in result.output

    assert len(calls) == 1
    call = calls[0]
    assert call["endpoint"] == "http://srv.example.com/mcp"
    assert call["tool_name"] == "unregister_fixture"
    assert call["arguments"] == {
        "name": "shared-physics-paper",
        "keep_files": False,
    }


def test_dev_unregister_fixture_cli_env_var(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without --remote, the CLI falls back to CAIRN_DEV_REMOTE_URL."""
    from typer.testing import CliRunner

    from cairn.cli.app import app

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("CAIRN_DEV_REMOTE_URL", "http://env.example.com/mcp")
    monkeypatch.setenv("CAIRN_BEARER_TOKEN", "tok")

    calls: list[dict] = []
    monkeypatch.setattr(
        "cairn.mcp.remote.call_tool",
        _stub_call_tool(
            [
                {
                    "unregistered": True,
                    "cairn": "shared-physics-paper",
                    "removed_path": "/srv/x",
                    "kept_files": False,
                    "reason": None,
                }
            ],
            calls,
        ),
    )

    runner = CliRunner()
    result = runner.invoke(
        app, ["dev", "unregister-fixture", "shared-physics-paper"]
    )
    assert result.exit_code == 0, result.output
    assert calls[0]["endpoint"] == "http://env.example.com/mcp"


def test_dev_unregister_fixture_cli_requires_remote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No --remote and no env var → exit code 2 with a helpful message."""
    from typer.testing import CliRunner

    from cairn.cli.app import app

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.delenv("CAIRN_DEV_REMOTE_URL", raising=False)

    runner = CliRunner()
    result = runner.invoke(app, ["dev", "unregister-fixture", "anything"])
    assert result.exit_code == 2
    assert "--remote is required" in result.output


def test_dev_unregister_fixture_cli_forwards_keep_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typer.testing import CliRunner

    from cairn.cli.app import app

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("CAIRN_BEARER_TOKEN", "tok")

    calls: list[dict] = []
    monkeypatch.setattr(
        "cairn.mcp.remote.call_tool",
        _stub_call_tool(
            [
                {
                    "unregistered": True,
                    "cairn": "shared-physics-paper",
                    "removed_path": None,
                    "kept_files": True,
                    "reason": None,
                }
            ],
            calls,
        ),
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "dev",
            "unregister-fixture",
            "shared-physics-paper",
            "--remote",
            "http://srv.example.com/mcp",
            "--keep-files",
        ],
    )
    assert result.exit_code == 0, result.output
    assert calls[0]["arguments"]["keep_files"] is True
    assert "--keep-files" in result.output or "kept the cairn directory" in result.output


def test_dev_unregister_fixture_cli_cleans_project_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--project-dir wipes a local project paired to this fixture."""
    from typer.testing import CliRunner

    from cairn.cli.app import app

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("CAIRN_BEARER_TOKEN", "tok")

    project_dir = tmp_path / "alex-laptop" / "paper"
    project_dir.mkdir(parents=True)
    (project_dir / "cairn.toml").write_text(
        '[cairn]\nendpoint = "http://srv.example.com/mcp"\n'
        'name = "shared-physics-paper"\n'
    )
    (project_dir / "draft.md").write_text("hello")

    calls: list[dict] = []
    monkeypatch.setattr(
        "cairn.mcp.remote.call_tool",
        _stub_call_tool(
            [
                {
                    "unregistered": True,
                    "cairn": "shared-physics-paper",
                    "removed_path": "/srv/x",
                    "kept_files": False,
                    "reason": None,
                }
            ],
            calls,
        ),
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "dev",
            "unregister-fixture",
            "shared-physics-paper",
            "--remote",
            "http://srv.example.com/mcp",
            "--project-dir",
            str(project_dir),
        ],
    )
    assert result.exit_code == 0, result.output
    assert not project_dir.exists()
    assert "removed local project dir" in result.output


def test_dev_unregister_fixture_cli_refuses_mismatched_project_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If <project-dir>/cairn.toml names a different cairn, refuse to delete."""
    from typer.testing import CliRunner

    from cairn.cli.app import app

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("CAIRN_BEARER_TOKEN", "tok")

    project_dir = tmp_path / "wrong-paper"
    project_dir.mkdir()
    (project_dir / "cairn.toml").write_text(
        '[cairn]\nname = "lit-monitor"\n'
    )

    calls: list[dict] = []
    monkeypatch.setattr(
        "cairn.mcp.remote.call_tool",
        _stub_call_tool(
            [
                {
                    "unregistered": True,
                    "cairn": "shared-physics-paper",
                    "removed_path": "/srv/x",
                    "kept_files": False,
                    "reason": None,
                }
            ],
            calls,
        ),
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "dev",
            "unregister-fixture",
            "shared-physics-paper",
            "--remote",
            "http://srv.example.com/mcp",
            "--project-dir",
            str(project_dir),
        ],
    )
    assert result.exit_code == 1
    # Server-side step still happened — the refusal is purely client-side.
    assert len(calls) == 1
    # Local dir is untouched.
    assert project_dir.exists()
    assert "does not match" in result.output


def test_dev_unregister_fixture_cli_refuses_project_dir_without_cairn_toml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A --project-dir with no cairn.toml is refused, not silently treated as ok."""
    from typer.testing import CliRunner

    from cairn.cli.app import app

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("CAIRN_BEARER_TOKEN", "tok")

    project_dir = tmp_path / "untagged"
    project_dir.mkdir()
    (project_dir / "notes.md").write_text("nothing here")

    calls: list[dict] = []
    monkeypatch.setattr(
        "cairn.mcp.remote.call_tool",
        _stub_call_tool(
            [
                {
                    "unregistered": True,
                    "cairn": "shared-physics-paper",
                    "removed_path": "/srv/x",
                    "kept_files": False,
                    "reason": None,
                }
            ],
            calls,
        ),
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "dev",
            "unregister-fixture",
            "shared-physics-paper",
            "--remote",
            "http://srv.example.com/mcp",
            "--project-dir",
            str(project_dir),
        ],
    )
    assert result.exit_code == 1
    assert "no cairn.toml found" in result.output
    assert project_dir.exists()


def test_dev_unregister_fixture_cli_reports_idempotent_no_op(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the server says the name wasn't registered, the CLI reports a
    no-op success, not an error."""
    from typer.testing import CliRunner

    from cairn.cli.app import app

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("CAIRN_BEARER_TOKEN", "tok")

    calls: list[dict] = []
    monkeypatch.setattr(
        "cairn.mcp.remote.call_tool",
        _stub_call_tool(
            [
                {
                    "unregistered": False,
                    "cairn": "shared-physics-paper",
                    "removed_path": None,
                    "kept_files": True,
                    "reason": "not_registered",
                }
            ],
            calls,
        ),
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "dev",
            "unregister-fixture",
            "shared-physics-paper",
            "--remote",
            "http://srv.example.com/mcp",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "was not registered" in result.output
    assert "no-op" in result.output
