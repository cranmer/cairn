"""Tests for MCP over HTTP features (US-P-11, US-P-12, US-P-13).

US-P-11: HTTP transport for `cairn mcp` (--transport flag)
US-P-12: Remote pairing via `cairn link --endpoint`
US-P-13: Remote dispatch for CLI write commands
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from cairn.cairn_toml import (
    CairnTomlError,
    load_pointer,
    write_pointer,
)
from cairn.cli.app import app

runner = CliRunner()


@pytest.fixture
def isolated_xdg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return tmp_path


# ---------------------------------------------------------------------------
# cairn_toml.py — three-mode validation (US-P-12)
# ---------------------------------------------------------------------------


def test_remote_mode_write_and_load(tmp_path: Path):
    """write_pointer with endpoint+name produces remote-mode cairn.toml."""
    project = tmp_path / "proj"
    project.mkdir()
    written = write_pointer(project, endpoint="https://cairn.example.com", name="my-cairn")
    assert written.is_file()
    pointer = load_pointer(written)
    assert pointer.endpoint == "https://cairn.example.com"
    assert pointer.name == "my-cairn"
    assert pointer.path is None
    assert pointer.mode == "remote"
    assert pointer.is_remote is True


def test_local_path_mode_is_not_remote(tmp_path: Path):
    project = tmp_path / "proj"
    project.mkdir()
    cairn = tmp_path / "cairn"
    cairn.mkdir()
    written = write_pointer(project, path=cairn)
    pointer = load_pointer(written)
    assert pointer.mode == "local-path"
    assert pointer.is_remote is False


def test_local_registry_mode_is_not_remote(tmp_path: Path):
    project = tmp_path / "proj"
    project.mkdir()
    written = write_pointer(project, name="demo")
    pointer = load_pointer(written)
    assert pointer.mode == "local-registry"
    assert pointer.is_remote is False


def test_remote_mode_content_has_both_fields(tmp_path: Path):
    """The written cairn.toml should contain both endpoint and name lines."""
    project = tmp_path / "proj"
    project.mkdir()
    written = write_pointer(project, endpoint="https://example.com", name="test-cairn")
    content = written.read_text()
    assert 'endpoint = "https://example.com"' in content
    assert 'name = "test-cairn"' in content


def test_load_rejects_endpoint_without_name(tmp_path: Path):
    """endpoint alone is invalid — must be paired with name."""
    target = tmp_path / "cairn.toml"
    target.write_text('[cairn]\nendpoint = "https://example.com"\n', encoding="utf-8")
    with pytest.raises(CairnTomlError, match="requires.*name"):
        load_pointer(target)


def test_load_rejects_path_and_name_together(tmp_path: Path):
    target = tmp_path / "cairn.toml"
    target.write_text(
        '[cairn]\npath = "/some/path"\nname = "demo"\n', encoding="utf-8"
    )
    with pytest.raises(CairnTomlError, match="path.*name|name.*path"):
        load_pointer(target)


def test_load_rejects_path_and_endpoint_together(tmp_path: Path):
    target = tmp_path / "cairn.toml"
    target.write_text(
        '[cairn]\npath = "/some/path"\nendpoint = "https://example.com"\nname = "demo"\n',
        encoding="utf-8",
    )
    # path + endpoint is invalid regardless of name; validator catches it
    with pytest.raises(CairnTomlError):
        load_pointer(target)


def test_load_rejects_empty_cairn_section(tmp_path: Path):
    target = tmp_path / "cairn.toml"
    target.write_text("[cairn]\n", encoding="utf-8")
    with pytest.raises(CairnTomlError, match="pointer"):
        load_pointer(target)


def test_write_pointer_rejects_endpoint_without_name(tmp_path: Path):
    project = tmp_path / "proj"
    project.mkdir()
    with pytest.raises(CairnTomlError, match="endpoint requires name"):
        write_pointer(project, endpoint="https://example.com")


def test_write_pointer_rejects_path_and_name(tmp_path: Path):
    project = tmp_path / "proj"
    project.mkdir()
    with pytest.raises(CairnTomlError, match="mutually exclusive"):
        write_pointer(project, path=tmp_path, name="demo")


def test_write_pointer_rejects_path_and_endpoint(tmp_path: Path):
    project = tmp_path / "proj"
    project.mkdir()
    with pytest.raises(CairnTomlError, match="mutually exclusive"):
        write_pointer(project, path=tmp_path, endpoint="https://example.com")


# ---------------------------------------------------------------------------
# `cairn link --endpoint` (US-P-12)
# ---------------------------------------------------------------------------


def test_link_endpoint_writes_remote_pointer(
    isolated_xdg: Path, monkeypatch: pytest.MonkeyPatch
):
    """`cairn link --endpoint <url> --name <handle>` writes a remote-mode cairn.toml."""
    project = isolated_xdg / "my-project"
    project.mkdir()
    monkeypatch.chdir(isolated_xdg)

    res = runner.invoke(
        app,
        [
            "link",
            str(project),
            "--endpoint",
            "https://cairn.example.com",
            "--name",
            "research",
            "--no-probe",
        ],
        catch_exceptions=False,
    )
    assert res.exit_code == 0, res.output
    pointer_path = project / "cairn.toml"
    assert pointer_path.is_file()
    pointer = load_pointer(pointer_path)
    assert pointer.endpoint == "https://cairn.example.com"
    assert pointer.name == "research"
    assert pointer.is_remote


def test_link_endpoint_without_name_errors(
    isolated_xdg: Path, monkeypatch: pytest.MonkeyPatch
):
    """`cairn link --endpoint` without --name gives an actionable error."""
    project = isolated_xdg / "my-project"
    project.mkdir()
    monkeypatch.chdir(isolated_xdg)

    res = runner.invoke(
        app,
        ["link", str(project), "--endpoint", "https://cairn.example.com", "--no-probe"],
        catch_exceptions=False,
    )
    assert res.exit_code != 0
    assert "--name" in res.output


def test_link_endpoint_prints_pairing_info(
    isolated_xdg: Path, monkeypatch: pytest.MonkeyPatch
):
    """`cairn link --endpoint` prints endpoint, cairn name, and credential hint."""
    project = isolated_xdg / "my-project"
    project.mkdir()
    monkeypatch.chdir(isolated_xdg)

    res = runner.invoke(
        app,
        [
            "link",
            str(project),
            "--endpoint",
            "https://cairn.example.com",
            "--name",
            "research",
            "--no-probe",
        ],
        catch_exceptions=False,
    )
    assert res.exit_code == 0, res.output
    assert "https://cairn.example.com" in res.output
    assert "research" in res.output
    # Should mention credentials
    assert "CAIRN_BEARER_TOKEN" in res.output or "credentials" in res.output.lower()


def test_link_endpoint_respects_force_flag(
    isolated_xdg: Path, monkeypatch: pytest.MonkeyPatch
):
    """--force overwrites an existing cairn.toml."""
    project = isolated_xdg / "my-project"
    project.mkdir()
    write_pointer(project, name="old-local")
    monkeypatch.chdir(isolated_xdg)

    res = runner.invoke(
        app,
        [
            "link",
            str(project),
            "--endpoint",
            "https://new.example.com",
            "--name",
            "new-remote",
            "--no-probe",
            "--force",
        ],
        catch_exceptions=False,
    )
    assert res.exit_code == 0, res.output
    pointer = load_pointer(project / "cairn.toml")
    assert pointer.is_remote
    assert pointer.endpoint == "https://new.example.com"


def test_link_endpoint_refuses_overwrite_without_force(
    isolated_xdg: Path, monkeypatch: pytest.MonkeyPatch
):
    project = isolated_xdg / "my-project"
    project.mkdir()
    write_pointer(project, name="existing")
    monkeypatch.chdir(isolated_xdg)

    res = runner.invoke(
        app,
        [
            "link",
            str(project),
            "--endpoint",
            "https://new.example.com",
            "--name",
            "new-remote",
            "--no-probe",
        ],
        catch_exceptions=False,
    )
    assert res.exit_code != 0
    assert "--force" in res.output


# ---------------------------------------------------------------------------
# cairn.credentials (US-P-13)
# ---------------------------------------------------------------------------


def test_credentials_env_var_takes_priority(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """CAIRN_BEARER_TOKEN takes priority over any credentials file."""
    from cairn.credentials import load_bearer_token

    monkeypatch.setenv("CAIRN_BEARER_TOKEN", "env-token-xyz")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    token = load_bearer_token("https://example.com")
    assert token == "env-token-xyz"


def test_credentials_file_lookup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Token is loaded from credentials.toml when no env var is set."""
    from cairn.credentials import load_bearer_token, save_bearer_token

    monkeypatch.delenv("CAIRN_BEARER_TOKEN", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    save_bearer_token("https://example.com", "file-token-abc")
    token = load_bearer_token("https://example.com")
    assert token == "file-token-abc"


def test_credentials_returns_none_when_not_configured(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    from cairn.credentials import load_bearer_token

    monkeypatch.delenv("CAIRN_BEARER_TOKEN", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    token = load_bearer_token("https://no-such-endpoint.example.com")
    assert token is None


def test_credentials_file_has_mode_0600(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """credentials.toml must be written with mode 0600."""
    import stat

    from cairn.credentials import credentials_path, save_bearer_token

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    save_bearer_token("https://example.com", "secret")
    creds = credentials_path()
    mode = oct(stat.S_IMODE(creds.stat().st_mode))
    assert mode == "0o600", f"expected 0600, got {mode}"


def test_credentials_different_endpoints_are_independent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    from cairn.credentials import load_bearer_token, save_bearer_token

    monkeypatch.delenv("CAIRN_BEARER_TOKEN", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    save_bearer_token("https://server-a.example.com", "token-a")
    save_bearer_token("https://server-b.example.com", "token-b")

    assert load_bearer_token("https://server-a.example.com") == "token-a"
    assert load_bearer_token("https://server-b.example.com") == "token-b"
    assert load_bearer_token("https://server-c.example.com") is None


# ---------------------------------------------------------------------------
# US-P-11: `cairn mcp --transport` flag
# ---------------------------------------------------------------------------


def test_mcp_rejects_invalid_transport(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """`cairn mcp --transport bogus` exits non-zero with a clear error.

    This test does not require the [mcp] extra — the flag validation runs before
    the MCP import.
    """
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    res = runner.invoke(app, ["mcp", "--transport", "bogus"], catch_exceptions=False)
    assert res.exit_code != 0
    assert "bogus" in res.output
    assert "stdio" in res.output or "streamable-http" in res.output


def test_mcp_accepts_valid_transports(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """--transport with valid values doesn't fail early (mock run() to avoid blocking)."""
    pytest.importorskip("mcp")  # skip if [mcp] extra is not installed
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    for transport in ("streamable-http", "sse"):
        with patch("cairn.mcp.server.run") as mock_run:
            res = runner.invoke(
                app,
                ["mcp", "--transport", transport, "--port", "19999"],
                catch_exceptions=False,
            )
        # Should call run with the transport, not fail with a usage error.
        assert res.exit_code == 0, f"transport={transport}: {res.output}"
        mock_run.assert_called_once_with(
            transport=transport, host="127.0.0.1", port=19999, path="/mcp"
        )


def test_mcp_stdio_transport_calls_run_without_kwargs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """--transport stdio (default) calls run() with no HTTP kwargs."""
    pytest.importorskip("mcp")  # skip if [mcp] extra is not installed
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    with patch("cairn.mcp.server.run") as mock_run:
        res = runner.invoke(app, ["mcp", "--transport", "stdio"], catch_exceptions=False)

    assert res.exit_code == 0, res.output
    mock_run.assert_called_once_with()


# ---------------------------------------------------------------------------
# US-P-13: remote dispatch in CLI write commands
# ---------------------------------------------------------------------------


@pytest.fixture
def project_with_remote_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A project directory with a remote-mode cairn.toml."""
    project = tmp_path / "project"
    project.mkdir()
    write_pointer(
        project,
        endpoint="https://cairn.example.com",
        name="my-cairn",
    )
    monkeypatch.chdir(project)
    return project


def test_decision_add_dispatches_to_remote(
    project_with_remote_toml: Path, monkeypatch: pytest.MonkeyPatch
):
    """`cairn decision add` calls dispatch_tool when cairn.toml is remote-mode."""
    mock_result = {"ok": True, "id": "D-001"}

    with patch("cairn.mcp.remote.dispatch_tool", return_value=mock_result) as mock_dispatch:
        res = runner.invoke(
            app,
            ["decision", "add", "--author", "alice", "--text", "Use remote dispatch"],
            catch_exceptions=False,
        )

    assert res.exit_code == 0, res.output
    assert "D-001" in res.output
    assert "remote cairn" in res.output.lower()

    mock_dispatch.assert_called_once()
    call_args = mock_dispatch.call_args
    assert call_args[0][0] == "https://cairn.example.com"
    assert call_args[0][1] == "my-cairn"
    assert call_args[0][2] == "add_decision"
    assert call_args[0][3]["author"] == "alice"
    assert call_args[0][3]["text"] == "Use remote dispatch"


def test_action_add_dispatches_to_remote(
    project_with_remote_toml: Path, monkeypatch: pytest.MonkeyPatch
):
    """`cairn action add` calls dispatch_tool for remote-mode projects."""
    mock_result = {"ok": True, "id": "A-001"}

    with patch("cairn.mcp.remote.dispatch_tool", return_value=mock_result) as mock_dispatch:
        res = runner.invoke(
            app,
            ["action", "add", "--assignee", "bob", "--text", "Review the paper"],
            catch_exceptions=False,
        )

    assert res.exit_code == 0, res.output
    assert "A-001" in res.output

    mock_dispatch.assert_called_once()
    args = mock_dispatch.call_args[0]
    assert args[2] == "add_action"
    assert args[3]["assignee"] == "bob"


def test_action_complete_dispatches_to_remote(
    project_with_remote_toml: Path, monkeypatch: pytest.MonkeyPatch
):
    """`cairn action complete` calls dispatch_tool for remote-mode projects."""
    mock_result = {"ok": True}

    with patch("cairn.mcp.remote.dispatch_tool", return_value=mock_result) as mock_dispatch:
        res = runner.invoke(
            app,
            ["action", "complete", "A-007"],
            catch_exceptions=False,
        )

    assert res.exit_code == 0, res.output
    assert "A-007" in res.output

    mock_dispatch.assert_called_once()
    args = mock_dispatch.call_args[0]
    assert args[2] == "complete_action"
    assert args[3]["id"] == "A-007"  # MCP tool uses "id", not "action_id"


def test_finding_add_dispatches_to_remote(
    project_with_remote_toml: Path, monkeypatch: pytest.MonkeyPatch
):
    """`cairn finding add` calls dispatch_tool for remote-mode projects."""
    mock_result = {"ok": True, "path": "knowledge/findings/2026-05-21-gw-signal.md"}

    with patch("cairn.mcp.remote.dispatch_tool", return_value=mock_result) as mock_dispatch:
        res = runner.invoke(
            app,
            ["finding", "add", "--author", "carol", "--title", "GW signal detected"],
            catch_exceptions=False,
        )

    assert res.exit_code == 0, res.output

    mock_dispatch.assert_called_once()
    args = mock_dispatch.call_args[0]
    assert args[2] == "add_finding"
    assert args[3]["author"] == "carol"
    assert args[3]["title"] == "GW signal detected"


def test_remote_dispatch_surfaces_auth_error(
    project_with_remote_toml: Path, monkeypatch: pytest.MonkeyPatch
):
    """A RemoteDispatchError is shown as a clean error message, not a traceback."""
    from cairn.mcp.remote import RemoteDispatchError

    with patch(
        "cairn.mcp.remote.dispatch_tool",
        side_effect=RemoteDispatchError(
            "authentication failed against https://cairn.example.com"
        ),
    ):
        res = runner.invoke(
            app,
            ["decision", "add", "--author", "alice", "--text", "Should fail"],
            catch_exceptions=False,
        )

    assert res.exit_code != 0
    assert "authentication failed" in res.output.lower()


def test_remote_dispatch_error_message_mentions_endpoint(
    project_with_remote_toml: Path, monkeypatch: pytest.MonkeyPatch
):
    from cairn.mcp.remote import RemoteDispatchError

    with patch(
        "cairn.mcp.remote.dispatch_tool",
        side_effect=RemoteDispatchError(
            "network unreachable: could not connect to https://cairn.example.com"
        ),
    ):
        res = runner.invoke(
            app,
            ["action", "add", "--assignee", "bob", "--text", "Should fail"],
            catch_exceptions=False,
        )

    assert res.exit_code != 0
    assert "cairn.example.com" in res.output


def test_local_cairn_still_works_when_no_remote_toml(
    isolated_xdg: Path, monkeypatch: pytest.MonkeyPatch
):
    """Local cairn write commands are unaffected when there's no remote cairn.toml."""
    monkeypatch.chdir(isolated_xdg)
    runner.invoke(app, ["init", "local-test", "--no-input"], catch_exceptions=False)
    cairn_dir = isolated_xdg / "local-test"
    monkeypatch.chdir(cairn_dir)
    runner.invoke(
        app,
        ["collaborator", "add", "--id", "alice", "--name", "Alice", "--role", "PhD"],
        catch_exceptions=False,
    )

    res = runner.invoke(
        app,
        ["decision", "add", "--author", "alice", "--text", "Use local dispatch"],
        catch_exceptions=False,
    )
    assert res.exit_code == 0, res.output
    assert "D-001" in res.output
    # Verify file was written locally
    import yaml

    decisions_yaml = cairn_dir / "state" / "decisions.yaml"
    data = yaml.safe_load(decisions_yaml.read_text())
    assert any(d["id"] == "D-001" for d in data["decisions"])
