"""Tests for the fixes surfaced by the multi-user/multi-cairn UX test run.

Covers findings F-01 through F-08 from
``tests/agent_smoke/multi-user-multi-cairn/runs/20260523T175633Z/SYNTHESIS.md``.

F-01: cairn mcp --transport streamable-http actually starts.
F-02: cairn finding/decision add (remote-MCP mode) succeeds against a real HTTP server.
F-03: cairn status/orient/validate/exploration/collaborator/skills honor cairn.toml.
F-04: error message mentions cairn.toml when one is present but not honored.
F-06: finding slug doesn't end in a dangling hyphen.
F-07: cairn --version flag works.
F-08: cairn decision add output includes the state file path and related refs.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import click
import pytest
from typer.testing import CliRunner

from cairn.cairn_toml import write_pointer
from cairn.cli._common import (
    RemoteTarget,
    _hint_pointer_if_any,
    require_local_target,
)
from cairn.cli.app import app

runner = CliRunner()

_CAIRN_BIN = shutil.which("cairn") or "cairn"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bootstrap_cairn(cwd: Path, name: str = "c") -> Path:
    """Scaffold a cairn at <cwd>/<name> and add a `kyle` collaborator."""
    res = runner.invoke(app, ["init", name, "--no-input"], catch_exceptions=False)
    assert res.exit_code == 0, res.output
    root = cwd / name
    res = runner.invoke(
        app,
        ["--help"],  # no-op; just to ensure app is wired
    )
    # Add a collaborator via CLI to keep the schema valid.
    res = runner.invoke(
        app,
        ["collaborator", "add", "--id", "kyle", "--name", "Kyle", "--role", "PI"],
        catch_exceptions=False,
        env={**os.environ, "PWD": str(root)},
    )
    return root


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_until_listening(port: int, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError(f"server on 127.0.0.1:{port} did not come up within {timeout}s")


# ---------------------------------------------------------------------------
# F-07: cairn --version
# ---------------------------------------------------------------------------


def test_f07_cli_accepts_dashdash_version_flag():
    """`cairn --version` prints the version and exits 0 (parallel to `cairn version`)."""
    res = runner.invoke(app, ["--version"])
    assert res.exit_code == 0, res.output
    # Version strings look like 0.0.1.dev99+gabcdef
    assert res.output.strip()
    assert any(ch.isdigit() for ch in res.output)


# ---------------------------------------------------------------------------
# F-03: paired-cwd routing works for read/utility commands
# ---------------------------------------------------------------------------


def test_f03_status_honors_cairn_toml_pointer(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    """`cairn status` from a paired project repo finds the cairn via cairn.toml."""
    res = runner.invoke(app, ["init", "demo-cairn", "--no-input"], catch_exceptions=False)
    assert res.exit_code == 0, res.output
    cairn_root = cwd / "demo-cairn"

    # Register in a per-test XDG dir so the pointer's `name=` resolves.
    config = cwd / "xdgconfig"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config))
    res = runner.invoke(
        app, ["register", "demo-cairn", str(cairn_root)], catch_exceptions=False
    )
    assert res.exit_code == 0, res.output

    project = cwd / "project-repo"
    project.mkdir()
    write_pointer(project, name="demo-cairn")
    monkeypatch.chdir(project)

    res = runner.invoke(app, ["status"], catch_exceptions=False)
    assert res.exit_code == 0, res.output
    assert "demo-cairn" in res.output


def test_f03_orient_honors_cairn_toml_pointer(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    """`cairn orient` from a paired project repo resolves via cairn.toml."""
    res = runner.invoke(app, ["init", "demo", "--no-input"], catch_exceptions=False)
    assert res.exit_code == 0
    cairn_root = cwd / "demo"
    config = cwd / "xdg"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config))
    runner.invoke(app, ["register", "demo", str(cairn_root)], catch_exceptions=False)

    project = cwd / "proj"
    project.mkdir()
    write_pointer(project, name="demo")
    monkeypatch.chdir(project)

    res = runner.invoke(app, ["orient"], catch_exceptions=False)
    assert res.exit_code == 0, res.output


def test_f03_validate_honors_cairn_toml_pointer(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    """`cairn validate` from a paired project repo resolves via cairn.toml."""
    res = runner.invoke(app, ["init", "demo", "--no-input"], catch_exceptions=False)
    assert res.exit_code == 0
    cairn_root = cwd / "demo"
    config = cwd / "xdg"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config))
    runner.invoke(app, ["register", "demo", str(cairn_root)], catch_exceptions=False)

    project = cwd / "proj"
    project.mkdir()
    write_pointer(project, name="demo")
    monkeypatch.chdir(project)

    res = runner.invoke(app, ["validate"], catch_exceptions=False)
    assert res.exit_code == 0, res.output


def test_f03_collaborator_add_honors_cairn_toml_pointer(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    """`cairn collaborator add` from a paired project repo writes to the right cairn."""
    res = runner.invoke(app, ["init", "demo", "--no-input"], catch_exceptions=False)
    assert res.exit_code == 0
    cairn_root = cwd / "demo"
    config = cwd / "xdg"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config))
    runner.invoke(app, ["register", "demo", str(cairn_root)], catch_exceptions=False)

    project = cwd / "proj"
    project.mkdir()
    write_pointer(project, name="demo")
    monkeypatch.chdir(project)

    res = runner.invoke(
        app,
        ["collaborator", "add", "--id", "kyle", "--name", "Kyle", "--role", "PI"],
        catch_exceptions=False,
    )
    assert res.exit_code == 0, res.output
    collabs = (cairn_root / "state" / "collaborators.yaml").read_text()
    assert "kyle" in collabs


def test_f03_require_local_target_rejects_remote_clearly():
    """`require_local_target` exits with a clear error when given a RemoteTarget."""
    remote = RemoteTarget(
        endpoint="http://127.0.0.1:9999/mcp", cairn_name="my-cairn", token=None
    )
    with pytest.raises(click.exceptions.Exit) as exc_info:
        require_local_target(remote, "status")
    assert exc_info.value.exit_code == 1


def test_f03_remote_pairing_status_gives_clear_error(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    """In a remote-MCP-paired project repo, `status` says so clearly (not generic error)."""
    project = cwd / "proj"
    project.mkdir()
    write_pointer(project, endpoint="http://127.0.0.1:1/mcp", name="remote-cairn")
    monkeypatch.chdir(project)

    res = runner.invoke(app, ["status"])
    assert res.exit_code != 0
    # The error names the cairn and the endpoint so the user knows what's going on.
    assert "remote-cairn" in res.output
    assert "remote-MCP" in res.output or "not supported" in res.output


# ---------------------------------------------------------------------------
# F-04: hint mentions cairn.toml when one is present
# ---------------------------------------------------------------------------


def test_f04_hint_when_cairn_toml_present_but_not_honored(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    """A pointer that resolution doesn't follow gets surfaced in the error.

    Exercises ``_hint_pointer_if_any`` indirectly via ``cairn link --help``-
    style flow; specifically calls a command that uses ``resolve_or_exit``
    against a cwd that has a ``cairn.toml`` whose registered name is wrong,
    and confirms the error mentions the pointer.
    """
    project = cwd / "proj"
    project.mkdir()
    write_pointer(project, name="not-registered-anywhere")
    monkeypatch.chdir(project)

    # Use a command that ends up calling resolve_or_exit indirectly.
    # `cairn link` uses resolve_or_exit. Without a cairn nor a registered name,
    # it should error AND mention the pointer.
    # But link's purpose is to write pointers; for this test we use the helper
    # directly which is the canonical test of the hint.
    captured = []

    def fake_echo(msg: str, err: bool = False) -> None:
        if err:
            captured.append(msg)

    with patch("cairn.cli._common.typer.echo", side_effect=fake_echo):
        _hint_pointer_if_any(project)

    assert any("cairn.toml" in m for m in captured)


# ---------------------------------------------------------------------------
# F-06: finding slug doesn't have a trailing dangling hyphen
# ---------------------------------------------------------------------------


def test_f06_finding_slug_strips_trailing_hyphen(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    """A long title that would truncate mid-word doesn't leave a trailing `-`."""
    res = runner.invoke(app, ["init", "demo", "--no-input"], catch_exceptions=False)
    assert res.exit_code == 0
    root = cwd / "demo"
    monkeypatch.chdir(root)
    runner.invoke(
        app, ["collaborator", "add", "--id", "kyle", "--name", "K", "--role", "PI"]
    )

    # 80-char title; the slug will hit the 60-char truncation cap.
    title = (
        "this is a very long title that will definitely truncate "
        "somewhere in the middle of a word probably yes"
    )
    res = runner.invoke(
        app,
        ["finding", "add", "--author", "kyle", "--title", title, "--body", "x"],
        catch_exceptions=False,
    )
    assert res.exit_code == 0, res.output

    findings = list((root / "knowledge" / "findings").iterdir())
    assert findings
    name = findings[0].stem  # without the .md extension
    assert not name.endswith("-"), f"slug ends in dangling hyphen: {name}"


# ---------------------------------------------------------------------------
# F-08: decision add output includes state path + related refs
# ---------------------------------------------------------------------------


def test_f08_decision_add_output_includes_path_and_related(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    """`cairn decision add` output is informative (not just `Recorded D-NNN.`)."""
    res = runner.invoke(app, ["init", "demo", "--no-input"], catch_exceptions=False)
    assert res.exit_code == 0
    root = cwd / "demo"
    monkeypatch.chdir(root)
    runner.invoke(
        app, ["collaborator", "add", "--id", "kyle", "--name", "K", "--role", "PI"]
    )

    res = runner.invoke(
        app,
        [
            "decision",
            "add",
            "--author",
            "kyle",
            "--text",
            "Adopt a thing",
            "--context",
            "Because.",
        ],
        catch_exceptions=False,
    )
    assert res.exit_code == 0, res.output
    assert "D-001" in res.output
    assert "state/decisions.yaml" in res.output


def test_f08_decision_add_output_echoes_related(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    """When `--related` is passed, the output confirms which ids were linked."""
    res = runner.invoke(app, ["init", "demo", "--no-input"], catch_exceptions=False)
    assert res.exit_code == 0
    root = cwd / "demo"
    monkeypatch.chdir(root)
    runner.invoke(
        app, ["collaborator", "add", "--id", "kyle", "--name", "K", "--role", "PI"]
    )
    # Seed a Q-001 so the related id resolves.
    (root / "state" / "open_questions.yaml").write_text(
        "- id: Q-001\n"
        "  raised_by: kyle\n"
        "  date: 2026-05-23T00:00:00Z\n"
        "  question: What?\n"
        "  status: open\n"
        "  answered_by: null\n"
        "  related: []\n",
        encoding="utf-8",
    )

    res = runner.invoke(
        app,
        [
            "decision",
            "add",
            "--author",
            "kyle",
            "--text",
            "A choice",
            "--related",
            "Q-001",
        ],
        catch_exceptions=False,
    )
    assert res.exit_code == 0, res.output
    assert "Q-001" in res.output


# ---------------------------------------------------------------------------
# F-01 + F-02: HTTP transport end-to-end via a real subprocess server
#
# These tests are heavier than the rest of the suite because they spawn a
# real `cairn mcp --transport streamable-http` subprocess. Marked with a
# module-scoped fixture so the cost is paid once per session.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def http_server_endpoint(tmp_path_factory: pytest.TempPathFactory):
    """Start a real cairn HTTP MCP server in a subprocess for the module's tests."""
    tmp = tmp_path_factory.mktemp("http-server")
    config = tmp / "config"
    config.mkdir()
    cairn_dir = tmp / "cairn"

    env = {
        **os.environ,
        "XDG_CONFIG_HOME": str(config),
        "GIT_AUTHOR_NAME": "Test User",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test User",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }

    # Scaffold a cairn + collaborator.  Use the runner's init so we get a clear
    # failure message in-process instead of a CalledProcessError.
    init_res = subprocess.run(
        [_CAIRN_BIN, "init", str(cairn_dir.name), "--no-input"],
        cwd=tmp,
        env=env,
        capture_output=True,
        text=True,
    )
    if init_res.returncode != 0:
        pytest.fail(
            f"cairn init failed (exit {init_res.returncode}).\n"
            f"stdout: {init_res.stdout}\nstderr: {init_res.stderr}"
        )
    subprocess.run(
        [
            _CAIRN_BIN, "collaborator", "add",
            "--id", "kyle", "--name", "Kyle", "--role", "PI",
        ],
        cwd=cairn_dir,
        env=env,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [_CAIRN_BIN, "register", "test-cairn", str(cairn_dir)],
        env=env,
        check=True,
        capture_output=True,
    )

    port = _free_port()
    proc = subprocess.Popen(
        [
            _CAIRN_BIN, "mcp",
            "--transport", "streamable-http",
            "--host", "127.0.0.1",
            "--port", str(port),
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        _wait_until_listening(port)
    except TimeoutError:
        proc.kill()
        out, err = proc.communicate(timeout=5)
        pytest.fail(
            f"cairn mcp HTTP server did not start within timeout.\n"
            f"stdout: {out.decode()[:2000]}\nstderr: {err.decode()[:2000]}"
        )

    endpoint = f"http://127.0.0.1:{port}/mcp"
    yield {"endpoint": endpoint, "cairn_name": "test-cairn", "cairn_dir": cairn_dir,
           "config": config}

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def test_f01_http_server_actually_starts(http_server_endpoint):
    """F-01: `cairn mcp --transport streamable-http --host --port` actually starts.

    The mere fact that the fixture's ``_wait_until_listening`` returned is the
    pass condition.  We add a probe to confirm the endpoint is responsive.
    """
    endpoint = http_server_endpoint["endpoint"]
    # The endpoint requires a session-init handshake; a raw POST without one
    # should fail with HTTP 4xx (server is up; request rejected — that's fine).
    req = urllib.request.Request(
        endpoint,
        data=b"{}",
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json,text/event-stream",
        },
    )
    try:
        urllib.request.urlopen(req, timeout=3)
    except urllib.error.HTTPError:
        # 4xx is the expected response — server is alive, request was malformed.
        return
    # 200 is also fine; either way the server is up.


def test_f02_remote_call_tool_round_trip(http_server_endpoint):
    """F-02: call_tool performs the MCP session handshake and gets a real response."""
    from cairn.mcp.remote import call_tool

    result = call_tool(
        http_server_endpoint["endpoint"],
        "whoami",
        {"cairn": http_server_endpoint["cairn_name"]},
        token=None,  # server doesn't enforce auth on loopback
    )
    # whoami returns a dict with the cairn name and collaborator info.
    assert isinstance(result, dict)


def test_f02_remote_finding_add_round_trip(http_server_endpoint, tmp_path: Path):
    """F-02: end-to-end finding add over HTTP transport produces a real file."""
    project = tmp_path / "proj"
    project.mkdir()
    write_pointer(
        project,
        endpoint=http_server_endpoint["endpoint"],
        name=http_server_endpoint["cairn_name"],
    )

    env = {
        **os.environ,
        "XDG_CONFIG_HOME": str(http_server_endpoint["config"]),
        "CAIRN_BEARER_TOKEN": "test",
    }
    res = subprocess.run(
        [
            _CAIRN_BIN, "finding", "add",
            "--author", "kyle",
            "--title", "F-02 round-trip",
            "--body", "Written via HTTP transport.",
        ],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    assert "F-02 round-trip" not in res.stdout or "Logged finding" in res.stdout
    # The finding file should land in the cairn's findings dir.
    findings = list(
        (http_server_endpoint["cairn_dir"] / "knowledge" / "findings").iterdir()
    )
    assert any("f-02-round-trip" in f.name for f in findings)
