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

from cairn.dev.fixtures import _run, scaffold_cairn, scaffold_project
from cairn.registry import load_registry, registry_path


def test_scaffold_cairn_works_without_ambient_git_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: server containers have no global git config — scaffold_cairn
    must inject a synthetic identity so `cairn init`'s initial commit succeeds."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    # Strip every signal `get_user_identity()` consults.
    for var in (
        "GIT_AUTHOR_NAME",
        "GIT_AUTHOR_EMAIL",
        "GIT_COMMITTER_NAME",
        "GIT_COMMITTER_EMAIL",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "empty-gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")

    cairn_dir = tmp_path / "cairns" / "coral-bleach"
    scaffold_cairn("coral-bleach", cairn_dir)

    assert (cairn_dir / "state" / "collaborators.yaml").is_file()


def test_run_surfaces_subprocess_stderr(tmp_path: Path) -> None:
    """Regression: when a subprocess fails, _run must propagate its stderr
    in the raised exception so MCP callers see what actually went wrong."""
    with pytest.raises(RuntimeError) as exc_info:
        _run(
            [
                "python3" if Path("/usr/bin/python3").exists() else "python",
                "-c",
                "import sys; sys.stderr.write('boom: specific failure'); sys.exit(7)",
            ],
            cwd=tmp_path,
        )
    msg = str(exc_info.value)
    assert "exited 7" in msg
    assert "boom: specific failure" in msg


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


# ---------------------------------------------------------------------------
# list_fixtures tool + `cairn dev fixtures` CLI
# ---------------------------------------------------------------------------


def test_list_fixtures_tool_returns_catalog_under_dev_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("mcp")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("CAIRN_REGISTRY_PATH", str(tmp_path / "registry.toml"))

    from cairn.dev.fixtures_data import FIXTURES
    from cairn.mcp.server import build_server

    sandbox = tmp_path / "sandbox"
    server = build_server(allow_dev_tools=True, sandbox_path=sandbox)

    tool_names = {t.name for t in server._tool_manager.list_tools()}
    assert "list_fixtures" in tool_names

    result = _call_dev_tool(server, "list_fixtures", {})
    payload = result.structured_content if hasattr(result, "structured_content") else result
    if not isinstance(payload, dict):
        payload = payload[0] if isinstance(payload, list) else payload

    names = {entry["name"] for entry in payload["fixtures"]}
    assert names == set(FIXTURES)
    for entry in payload["fixtures"]:
        s = entry["summary"]
        assert isinstance(s["collaborators"], list)
        assert isinstance(s["decisions"], int)
        assert isinstance(s["questions"], int)
        assert isinstance(s["findings"], int)


def test_list_fixtures_absent_without_dev_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("mcp")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("CAIRN_REGISTRY_PATH", str(tmp_path / "registry.toml"))

    from cairn.mcp.server import build_server

    server = build_server()
    tool_names = {t.name for t in server._tool_manager.list_tools()}
    assert "list_fixtures" not in tool_names


def test_dev_fixtures_cli_local_lists_catalog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typer.testing import CliRunner

    from cairn.cli.app import app
    from cairn.dev.fixtures_data import FIXTURES

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    runner = CliRunner()
    result = runner.invoke(app, ["dev", "fixtures"])
    assert result.exit_code == 0, result.output
    for name in FIXTURES:
        assert name in result.output


def _stub_call_tool_returning(payload: dict):
    """Build a stand-in for `cairn.mcp.remote.call_tool` that ignores args
    and returns *payload*."""

    def _stub(endpoint, tool_name, arguments, *, token=None):
        return payload

    return _stub


def test_dev_fixtures_cli_remote_match(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from typer.testing import CliRunner

    from cairn.cli import dev_cmd
    from cairn.cli.app import app
    from cairn.dev.fixtures_data import FIXTURES

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("CAIRN_BEARER_TOKEN", "tok")

    # Build a "remote" catalog identical to the local one.
    remote_payload = {
        "fixtures": [
            {
                "name": name,
                "summary": {
                    "collaborators": [c.id for c in fix.collaborators],
                    "decisions": len(fix.decisions),
                    "questions": len(fix.questions),
                    "findings": len(fix.findings),
                },
            }
            for name, fix in FIXTURES.items()
        ]
    }
    monkeypatch.setattr("cairn.mcp.remote.call_tool", _stub_call_tool_returning(remote_payload))
    # Also patch the symbol the CLI imports locally inside its function body.
    monkeypatch.setattr(dev_cmd, "FIXTURES", FIXTURES, raising=True)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["dev", "fixtures", "--remote", "http://srv.example.com/mcp"],
    )
    assert result.exit_code == 0, result.output
    for name in FIXTURES:
        assert name in result.output
    assert "match" in result.output
    assert "drift" not in result.output
    assert "missing" not in result.output


def test_dev_fixtures_cli_remote_detects_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typer.testing import CliRunner

    from cairn.cli.app import app
    from cairn.dev.fixtures_data import FIXTURES

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("CAIRN_BEARER_TOKEN", "tok")

    # Tamper one count so the comparison reports drift; drop another
    # entirely so we hit the remote-missing branch too.
    fixtures_iter = iter(FIXTURES.items())
    first_name, first_fix = next(fixtures_iter)
    remote_payload = {
        "fixtures": [
            {
                "name": first_name,
                "summary": {
                    "collaborators": [c.id for c in first_fix.collaborators],
                    "decisions": len(first_fix.decisions) + 99,  # drift
                    "questions": len(first_fix.questions),
                    "findings": len(first_fix.findings),
                },
            },
            # Skip the second fixture entirely → remote-missing.
            *[
                {
                    "name": name,
                    "summary": {
                        "collaborators": [c.id for c in fix.collaborators],
                        "decisions": len(fix.decisions),
                        "questions": len(fix.questions),
                        "findings": len(fix.findings),
                    },
                }
                for i, (name, fix) in enumerate(fixtures_iter)
                if i != 0
            ],
            # And invent a fixture the client doesn't know → client-missing.
            {
                "name": "ghost-fixture",
                "summary": {
                    "collaborators": [],
                    "decisions": 0,
                    "questions": 0,
                    "findings": 0,
                },
            },
        ]
    }
    monkeypatch.setattr("cairn.mcp.remote.call_tool", _stub_call_tool_returning(remote_payload))

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["dev", "fixtures", "--remote", "http://srv.example.com/mcp"],
    )
    assert result.exit_code != 0  # drift → non-zero exit
    assert "drift" in result.output
    assert "remote-missing" in result.output
    assert "client-missing" in result.output
    assert "ghost-fixture" in result.output


# ---------------------------------------------------------------------------
# CAIRN_DEV_REMOTE_URL fallback (.env wire-up)
# ---------------------------------------------------------------------------


def test_dev_fixtures_falls_back_to_env_var(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without --remote, CAIRN_DEV_REMOTE_URL drives the comparison."""
    from typer.testing import CliRunner

    from cairn.cli.app import app
    from cairn.dev.fixtures_data import FIXTURES

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("CAIRN_DEV_REMOTE_URL", "http://srv.example.com/mcp")
    monkeypatch.setenv("CAIRN_BEARER_TOKEN", "tok")

    remote_payload = {
        "fixtures": [
            {
                "name": name,
                "summary": {
                    "collaborators": [c.id for c in fix.collaborators],
                    "decisions": len(fix.decisions),
                    "questions": len(fix.questions),
                    "findings": len(fix.findings),
                },
            }
            for name, fix in FIXTURES.items()
        ]
    }
    monkeypatch.setattr(
        "cairn.mcp.remote.call_tool", _stub_call_tool_returning(remote_payload)
    )

    runner = CliRunner()
    result = runner.invoke(app, ["dev", "fixtures"])  # no --remote
    assert result.exit_code == 0, result.output
    # The remote-comparison header should appear (not the local-only listing).
    assert "status" in result.output
    assert "match" in result.output


def test_dev_fixtures_explicit_remote_beats_env_var(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicit --remote URL is what gets dispatched to, not the env var."""
    from typer.testing import CliRunner

    from cairn.cli.app import app

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("CAIRN_DEV_REMOTE_URL", "http://wrong.example.com/mcp")
    monkeypatch.setenv("CAIRN_BEARER_TOKEN", "tok")

    captured: dict[str, str] = {}

    def _capturing_stub(endpoint, tool_name, arguments, *, token=None):
        captured["endpoint"] = endpoint
        return {"fixtures": []}

    monkeypatch.setattr("cairn.mcp.remote.call_tool", _capturing_stub)

    runner = CliRunner()
    runner.invoke(
        app,
        ["dev", "fixtures", "--remote", "http://right.example.com/mcp"],
    )
    assert captured["endpoint"] == "http://right.example.com/mcp"


def test_dev_fixtures_empty_env_var_falls_through_to_local(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Empty CAIRN_DEV_REMOTE_URL is treated as unset; we print local catalog."""
    from typer.testing import CliRunner

    from cairn.cli.app import app
    from cairn.dev.fixtures_data import FIXTURES

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("CAIRN_DEV_REMOTE_URL", "")

    runner = CliRunner()
    result = runner.invoke(app, ["dev", "fixtures"])
    assert result.exit_code == 0, result.output
    # Local-only output has no "status" column header.
    assert "status" not in result.output
    for name in FIXTURES:
        assert name in result.output
