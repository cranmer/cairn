"""Tests for US-P-11 (HTTP transport), US-P-12 (remote pairing), US-P-13 (remote dispatch).

US-P-11: cairn mcp --transport {stdio,streamable-http,sse}
US-P-12: cairn link --endpoint <url> --name <handle> (three-mode cairn.toml)
US-P-13: remote dispatch from write commands + echoing resolved cairn + new ID (m13v fix)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from cairn.cairn_toml import CairnTomlError, load_pointer, write_pointer
from cairn.cli._common import RemoteTarget, resolve_target
from cairn.cli.app import app
from cairn.mcp.remote import (
    RemoteAuthError,
    RemoteCallError,
    RemoteNetworkError,
    _parse_sse_response,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bootstrap_cairn(cwd: Path, monkeypatch: pytest.MonkeyPatch, name: str = "p") -> Path:
    """Create a minimal cairn and register a collaborator."""
    runner.invoke(app, ["init", name, "--no-input"], catch_exceptions=False)
    root = cwd / name
    monkeypatch.chdir(root)
    runner.invoke(
        app, ["collaborator", "add", "--id", "kyle", "--name", "Kyle", "--role", "PI"]
    )
    return root


# ---------------------------------------------------------------------------
# US-P-11: cairn mcp --transport validation
# ---------------------------------------------------------------------------


def test_us_p_11_invalid_transport_fails_fast(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    """`cairn mcp --transport bogus` fails before importing the MCP server."""
    # We don't need a cairn for this — the transport check happens before
    # the server is built.
    res = runner.invoke(app, ["mcp", "--transport", "bogus"], catch_exceptions=False)
    assert res.exit_code != 0
    assert "invalid --transport" in res.output
    assert "bogus" in res.output


def test_us_p_11_valid_transport_values_dont_fail_early():
    """Valid --transport values don't trigger the 'invalid --transport' early guard.

    Mocks ``server.run`` so the test doesn't actually start a long-running
    server (which would block stdio and leave HTTP listeners open).
    """
    for transport in ("stdio", "streamable-http", "sse"):
        with patch("cairn.mcp.server.build_server") as build:
            build.return_value.run.return_value = None
            res = runner.invoke(app, ["mcp", "--transport", transport])
        assert "invalid --transport" not in res.output


# ---------------------------------------------------------------------------
# US-P-12: cairn_toml three-mode validator
# ---------------------------------------------------------------------------


def test_us_p_12_remote_mode_requires_name_with_endpoint(tmp_path: Path):
    """endpoint alone in cairn.toml is rejected with actionable error."""
    target = tmp_path / "cairn.toml"
    target.write_text('[cairn]\nendpoint = "https://mcp.example.com/mcp"\n', encoding="utf-8")
    with pytest.raises(CairnTomlError, match=r"requires.*name"):
        load_pointer(target)


def test_us_p_12_remote_mode_endpoint_plus_name_accepted(tmp_path: Path):
    """endpoint + name together → remote-MCP mode, is_remote=True."""
    project = tmp_path / "proj"
    project.mkdir()
    written = write_pointer(project, endpoint="https://mcp.example.com/mcp", name="my-cairn")
    pointer = load_pointer(written)
    assert pointer.is_remote
    assert pointer.endpoint == "https://mcp.example.com/mcp"
    assert pointer.name == "my-cairn"


def test_us_p_12_link_endpoint_requires_name(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    """`cairn link --endpoint <url>` without --name errors."""
    project = cwd / "myproject"
    project.mkdir()
    res = runner.invoke(
        app,
        ["link", str(project), "--endpoint", "https://mcp.example.com/mcp"],
        catch_exceptions=False,
    )
    assert res.exit_code != 0
    assert "--name" in res.output


def test_us_p_12_link_endpoint_writes_remote_toml(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    """`cairn link --endpoint <url> --name <handle> --no-probe` writes remote-mode cairn.toml."""
    project = cwd / "myproject"
    project.mkdir()
    res = runner.invoke(
        app,
        [
            "link",
            str(project),
            "--endpoint", "https://mcp.example.com/mcp",
            "--name", "my-cairn",
            "--no-probe",
        ],
        catch_exceptions=False,
    )
    assert res.exit_code == 0, res.output
    pointer = load_pointer(project / "cairn.toml")
    assert pointer.is_remote
    assert pointer.endpoint == "https://mcp.example.com/mcp"
    assert pointer.name == "my-cairn"


def test_us_p_12_link_endpoint_prints_credential_hints(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    """`cairn link --endpoint` output includes credential setup hints."""
    project = cwd / "myproject"
    project.mkdir()
    res = runner.invoke(
        app,
        [
            "link",
            str(project),
            "--endpoint", "https://mcp.example.com/mcp",
            "--name", "my-cairn",
            "--no-probe",
        ],
        catch_exceptions=False,
    )
    assert res.exit_code == 0, res.output
    assert "CAIRN_BEARER_TOKEN" in res.output
    assert "credentials.toml" in res.output


def test_us_p_12_link_endpoint_probe_failure_blocks_write(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    """When probe fails, `cairn link --endpoint` refuses to write the pointer."""
    project = cwd / "myproject"
    project.mkdir()
    with patch("cairn.cli.link_cmd.probe", return_value=False):
        res = runner.invoke(
            app,
            [
                "link",
                str(project),
                "--endpoint", "https://down.example.com/mcp",
                "--name", "my-cairn",
            ],
            catch_exceptions=False,
        )
    assert res.exit_code != 0
    assert "could not reach" in res.output
    assert not (project / "cairn.toml").exists()


def test_us_p_12_link_endpoint_no_probe_skips_check(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    """--no-probe writes the pointer even without network access."""
    project = cwd / "myproject"
    project.mkdir()
    with patch("cairn.cli.link_cmd.probe", return_value=False) as mock_probe:
        res = runner.invoke(
            app,
            [
                "link",
                str(project),
                "--endpoint", "https://mcp.example.com/mcp",
                "--name", "my-cairn",
                "--no-probe",
            ],
            catch_exceptions=False,
        )
    mock_probe.assert_not_called()
    assert res.exit_code == 0, res.output
    assert (project / "cairn.toml").exists()


# ---------------------------------------------------------------------------
# US-P-13: resolve_target() + remote dispatch
# ---------------------------------------------------------------------------


def test_us_p_13_resolve_target_returns_local_when_no_pointer(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    """With no cairn.toml, resolve_target falls back to local cairn resolution."""
    from cairn.paths import CairnPaths

    root = _bootstrap_cairn(cwd, monkeypatch)
    result = resolve_target()
    assert isinstance(result, CairnPaths)
    assert result.root.resolve() == root.resolve()


def test_us_p_13_resolve_target_returns_remote_target(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    """With a remote-mode cairn.toml, resolve_target returns RemoteTarget."""
    project = cwd / "proj"
    project.mkdir()
    write_pointer(
        project,
        endpoint="https://mcp.example.com/mcp",
        name="my-cairn",
    )
    monkeypatch.chdir(project)
    monkeypatch.setenv("CAIRN_BEARER_TOKEN", "test-token")
    result = resolve_target()
    assert isinstance(result, RemoteTarget)
    assert result.endpoint == "https://mcp.example.com/mcp"
    assert result.cairn_name == "my-cairn"
    assert result.token == "test-token"


def test_us_p_13_remote_target_token_from_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """CAIRN_BEARER_TOKEN env var is picked up by resolve_target."""
    project = tmp_path / "proj"
    project.mkdir()
    write_pointer(project, endpoint="https://mcp.example.com/mcp", name="demo")
    monkeypatch.chdir(project)
    monkeypatch.setenv("CAIRN_BEARER_TOKEN", "abc123")
    result = resolve_target()
    assert isinstance(result, RemoteTarget)
    assert result.token == "abc123"


def test_us_p_13_remote_target_no_token_when_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """token is None when no env var and no credentials file."""
    project = tmp_path / "proj"
    project.mkdir()
    write_pointer(project, endpoint="https://mcp.example.com/mcp", name="demo")
    monkeypatch.chdir(project)
    monkeypatch.delenv("CAIRN_BEARER_TOKEN", raising=False)
    # Redirect credentials file to a non-existent path.
    import cairn.credentials as creds_mod
    monkeypatch.setattr(creds_mod, "_CREDENTIALS_FILE", Path(tmp_path / "no-creds.toml"))
    result = resolve_target()
    assert isinstance(result, RemoteTarget)
    assert result.token is None


# ---------------------------------------------------------------------------
# US-P-13 + m13v fix: write commands echo resolved cairn + new ID
# ---------------------------------------------------------------------------


def _make_decision_response(cairn_name: str, new_id: str) -> dict:
    return {"cairn": cairn_name, "id": new_id, "commit_sha": "abc123def456"}


def _make_action_response(cairn_name: str, new_id: str) -> dict:
    return {"cairn": cairn_name, "id": new_id, "commit_sha": "abc123def456"}


def _make_finding_response(cairn_name: str) -> dict:
    return {
        "cairn": cairn_name,
        "slug": "test-finding",
        "date": "2026-05-21",
        "path": "knowledge/findings/2026-05-21-test-finding.md",
        "commit_sha": "abc123def456",
    }


def test_us_p_13_decision_add_remote_echoes_cairn_and_id(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    """cairn decision add in remote mode prints resolved cairn name + new ID (m13v fix)."""
    project = cwd / "proj"
    project.mkdir()
    write_pointer(project, endpoint="https://mcp.example.com/mcp", name="my-cairn")
    monkeypatch.chdir(project)
    monkeypatch.setenv("CAIRN_BEARER_TOKEN", "test-token")

    with patch("cairn.mcp.remote.call_tool") as mock_call:
        mock_call.return_value = _make_decision_response("my-cairn", "D-001")
        res = runner.invoke(
            app,
            ["decision", "add", "--author", "kyle", "--text", "Use stratified resampling"],
            catch_exceptions=False,
        )

    assert res.exit_code == 0, res.output
    # m13v fix: confirmed cairn name + ID in output
    assert "D-001" in res.output
    assert "my-cairn" in res.output
    assert "https://mcp.example.com/mcp" in res.output


def test_us_p_13_decision_add_remote_server_resolves_to_different_cairn(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    """If server resolves to a different cairn handle, the CLI shows the actual one.

    This is the core m13v concern: a wrong `name` in cairn.toml writes to the
    wrong cairn. The echoed server response makes the discrepancy visible.
    """
    project = cwd / "proj"
    project.mkdir()
    # cairn.toml says "my-cairn" but server resolves to "other-cairn"
    write_pointer(project, endpoint="https://mcp.example.com/mcp", name="my-cairn")
    monkeypatch.chdir(project)
    monkeypatch.setenv("CAIRN_BEARER_TOKEN", "test-token")

    with patch("cairn.mcp.remote.call_tool") as mock_call:
        mock_call.return_value = _make_decision_response("other-cairn", "D-001")
        res = runner.invoke(
            app,
            ["decision", "add", "--author", "kyle", "--text", "A decision"],
            catch_exceptions=False,
        )

    assert res.exit_code == 0, res.output
    # The actual resolved cairn name (not the one in cairn.toml) is shown.
    assert "other-cairn" in res.output


def test_us_p_13_decision_add_remote_missing_token_errors(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    """cairn decision add remote-mode with no token exits with credential hint."""
    project = cwd / "proj"
    project.mkdir()
    write_pointer(project, endpoint="https://mcp.example.com/mcp", name="my-cairn")
    monkeypatch.chdir(project)
    monkeypatch.delenv("CAIRN_BEARER_TOKEN", raising=False)
    import cairn.credentials as creds_mod
    monkeypatch.setattr(creds_mod, "_CREDENTIALS_FILE", Path(cwd / "no-creds.toml"))

    res = runner.invoke(
        app,
        ["decision", "add", "--author", "kyle", "--text", "x"],
        catch_exceptions=False,
    )
    assert res.exit_code != 0
    assert "CAIRN_BEARER_TOKEN" in res.output


def test_us_p_13_action_add_remote_echoes_cairn_and_id(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    """cairn action add in remote mode prints resolved cairn + ID."""
    project = cwd / "proj"
    project.mkdir()
    write_pointer(project, endpoint="https://mcp.example.com/mcp", name="my-cairn")
    monkeypatch.chdir(project)
    monkeypatch.setenv("CAIRN_BEARER_TOKEN", "test-token")

    with patch("cairn.mcp.remote.call_tool") as mock_call:
        mock_call.return_value = _make_action_response("my-cairn", "A-001")
        res = runner.invoke(
            app,
            ["action", "add", "--assignee", "kyle", "--text", "Write tests"],
            catch_exceptions=False,
        )

    assert res.exit_code == 0, res.output
    assert "A-001" in res.output
    assert "my-cairn" in res.output


def test_us_p_13_action_complete_remote_echoes_cairn_and_id(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    """cairn action complete in remote mode prints resolved cairn + ID."""
    project = cwd / "proj"
    project.mkdir()
    write_pointer(project, endpoint="https://mcp.example.com/mcp", name="my-cairn")
    monkeypatch.chdir(project)
    monkeypatch.setenv("CAIRN_BEARER_TOKEN", "test-token")

    with patch("cairn.mcp.remote.call_tool") as mock_call:
        mock_call.return_value = {"cairn": "my-cairn", "id": "A-002", "commit_sha": "x"}
        res = runner.invoke(
            app,
            ["action", "complete", "A-002", "--by", "kyle"],
            catch_exceptions=False,
        )

    assert res.exit_code == 0, res.output
    assert "A-002" in res.output
    assert "my-cairn" in res.output


def test_us_p_13_finding_add_remote_echoes_cairn_and_path(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    """cairn finding add in remote mode prints resolved cairn + file path."""
    project = cwd / "proj"
    project.mkdir()
    write_pointer(project, endpoint="https://mcp.example.com/mcp", name="my-cairn")
    monkeypatch.chdir(project)
    monkeypatch.setenv("CAIRN_BEARER_TOKEN", "test-token")

    with patch("cairn.mcp.remote.call_tool") as mock_call:
        mock_call.return_value = _make_finding_response("my-cairn")
        res = runner.invoke(
            app,
            ["finding", "add", "--author", "kyle", "--title", "Test Finding"],
            catch_exceptions=False,
        )

    assert res.exit_code == 0, res.output
    assert "my-cairn" in res.output
    assert "https://mcp.example.com/mcp" in res.output


def test_us_p_13_remote_auth_error_shown_clearly(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    """HTTP 401/403 → RemoteAuthError → clear CLI message."""
    project = cwd / "proj"
    project.mkdir()
    write_pointer(project, endpoint="https://mcp.example.com/mcp", name="my-cairn")
    monkeypatch.chdir(project)
    monkeypatch.setenv("CAIRN_BEARER_TOKEN", "bad-token")

    with patch("cairn.mcp.remote.call_tool") as mock_call:
        mock_call.side_effect = RemoteAuthError(
            "authentication failed against https://mcp.example.com/mcp (HTTP 401)"
        )
        res = runner.invoke(
            app,
            ["decision", "add", "--author", "kyle", "--text", "x"],
            catch_exceptions=False,
        )

    assert res.exit_code != 0
    assert "authentication failed" in res.output


def test_us_p_13_network_error_shown_clearly(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    """Network error → RemoteNetworkError → clear CLI message."""
    project = cwd / "proj"
    project.mkdir()
    write_pointer(project, endpoint="https://down.example.com/mcp", name="my-cairn")
    monkeypatch.chdir(project)
    monkeypatch.setenv("CAIRN_BEARER_TOKEN", "test-token")

    with patch("cairn.mcp.remote.call_tool") as mock_call:
        mock_call.side_effect = RemoteNetworkError(
            "could not reach https://down.example.com/mcp"
        )
        res = runner.invoke(
            app,
            ["decision", "add", "--author", "kyle", "--text", "x"],
            catch_exceptions=False,
        )

    assert res.exit_code != 0
    assert "could not reach" in res.output


def test_us_p_13_remote_call_error_forwarded(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    """Remote validation error → RemoteCallError → forwarded to user."""
    project = cwd / "proj"
    project.mkdir()
    write_pointer(project, endpoint="https://mcp.example.com/mcp", name="my-cairn")
    monkeypatch.chdir(project)
    monkeypatch.setenv("CAIRN_BEARER_TOKEN", "test-token")

    with patch("cairn.mcp.remote.call_tool") as mock_call:
        mock_call.side_effect = RemoteCallError("unknown author 'kyle'")
        res = runner.invoke(
            app,
            ["decision", "add", "--author", "kyle", "--text", "x"],
            catch_exceptions=False,
        )

    assert res.exit_code != 0
    assert "unknown author" in res.output


# ---------------------------------------------------------------------------
# mcp.remote module unit tests
# ---------------------------------------------------------------------------


def test_remote_parse_sse_response():
    raw = (
        b'data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text",'
        b'"text":"{\\"id\\":\\"D-001\\"}"}]}}\n'
    )
    result = _parse_sse_response(raw)
    assert result["result"]["content"][0]["type"] == "text"


def test_remote_parse_sse_response_skips_done():
    raw = b'data: [DONE]\n'
    with pytest.raises(RemoteCallError, match="could not parse"):
        _parse_sse_response(raw)


# ---------------------------------------------------------------------------
# credentials module unit tests
# ---------------------------------------------------------------------------


def test_credentials_env_var_takes_precedence(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """CAIRN_BEARER_TOKEN env var takes precedence over the file."""
    import cairn.credentials as creds_mod
    monkeypatch.setenv("CAIRN_BEARER_TOKEN", "env-token")
    monkeypatch.setattr(creds_mod, "_CREDENTIALS_FILE", tmp_path / "creds.toml")
    assert creds_mod.resolve_token("https://any.example.com/mcp") == "env-token"


def test_credentials_file_lookup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Token is loaded from credentials.toml keyed by endpoint."""
    import cairn.credentials as creds_mod
    monkeypatch.delenv("CAIRN_BEARER_TOKEN", raising=False)
    creds_file = tmp_path / "creds.toml"
    creds_file.write_text(
        '[endpoints."https://mcp.example.com/mcp"]\ntoken = "file-token"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(creds_mod, "_CREDENTIALS_FILE", creds_file)
    assert creds_mod.resolve_token("https://mcp.example.com/mcp") == "file-token"
    assert creds_mod.resolve_token("https://other.example.com/mcp") is None


def test_credentials_store_and_load(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """store_token writes a 0600 file; resolve_token reads it back."""
    import stat

    import cairn.credentials as creds_mod
    monkeypatch.delenv("CAIRN_BEARER_TOKEN", raising=False)
    creds_file = tmp_path / "creds" / "credentials.toml"
    monkeypatch.setattr(creds_mod, "_CREDENTIALS_FILE", creds_file)

    written = creds_mod.store_token("https://mcp.example.com/mcp", "stored-token")
    assert written.is_file()
    perms = stat.S_IMODE(written.stat().st_mode)
    assert perms == (stat.S_IRUSR | stat.S_IWUSR)
    assert creds_mod.resolve_token("https://mcp.example.com/mcp") == "stored-token"
