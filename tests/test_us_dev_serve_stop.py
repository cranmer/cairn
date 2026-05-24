"""Tests for the `cairn dev` subgroup (serve, stop, scaffold-fixture)."""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cairn.cli.app import app


def _port_is_open(host: str, port: int, timeout: float = 0.5) -> bool:
    """Return True if a TCP connect to (host, port) succeeds within timeout."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def _bootstrap_cairn(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Init a minimal cairn at <tmp_path>/fixture-cairn and return its path."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["init", "fixture-cairn", "--no-input"])
    assert result.exit_code == 0, result.output
    return tmp_path / "fixture-cairn"


def test_dev_subgroup_help_lists_three_commands() -> None:
    """`cairn dev --help` should list serve, stop, and scaffold-fixture."""
    runner = CliRunner()
    result = runner.invoke(app, ["dev", "--help"])
    assert result.exit_code == 0, result.output
    assert "serve" in result.output
    assert "stop" in result.output
    assert "scaffold-fixture" in result.output


def test_dev_serve_starts_detached_server_and_writes_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`cairn dev serve --cairn <path>` should start an HTTP MCP server in
    the background and write a state file with pid/port/url."""
    cache_home = tmp_path / "cache"
    cache_home.mkdir()
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))

    cairn_dir = _bootstrap_cairn(tmp_path, monkeypatch)

    runner = CliRunner()
    serve_result = runner.invoke(
        app, ["dev", "serve", "--cairn-path", str(cairn_dir)]
    )
    state_dir = cache_home / "cairn" / "dev-servers"
    try:
        assert serve_result.exit_code == 0, serve_result.output

        # Output should include pid, port, url.
        assert "pid=" in serve_result.output
        assert "port=" in serve_result.output
        assert "http://127.0.0.1:" in serve_result.output

        # State file should exist under XDG_CACHE_HOME/cairn/dev-servers/.
        state_files = [p for p in state_dir.glob("*.json") if p.parent == state_dir]
        assert len(state_files) == 1, f"expected 1 state file, got {state_files}"

        state = json.loads(state_files[0].read_text())
        assert "pid" in state
        assert "port" in state
        assert "host" in state and state["host"] == "127.0.0.1"
        assert "path" in state and state["path"] == "/mcp"
        assert "url" in state
        assert state["url"].startswith("http://127.0.0.1:")
        assert state["url"].endswith("/mcp")

        # Server should actually be accepting connections.
        assert _port_is_open(state["host"], state["port"])

        # And it must be detached — its own session leader (the bit
        # `start_new_session=True` actually flips). PPID stays as the
        # spawning process until the parent exits, so we check the
        # session id instead.
        pid = state["pid"]
        assert os.getsid(pid) == pid, "child should be its own session leader"
    finally:
        # Best-effort cleanup; the `stop` test will exercise the real path.
        for sf in state_dir.glob("*.json"):
            try:
                pid = json.loads(sf.read_text())["pid"]
                os.kill(pid, 15)
            except (FileNotFoundError, ProcessLookupError, KeyError):
                pass


def test_dev_stop_all_kills_running_servers_and_clears_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache_home = tmp_path / "cache"
    cache_home.mkdir()
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))

    cairn_dir = _bootstrap_cairn(tmp_path, monkeypatch)
    runner = CliRunner()

    # Start two servers.
    r1 = runner.invoke(app, ["dev", "serve", "--cairn-path", str(cairn_dir)])
    r2 = runner.invoke(app, ["dev", "serve", "--cairn-path", str(cairn_dir)])
    assert r1.exit_code == 0, r1.output
    assert r2.exit_code == 0, r2.output

    state_dir = cache_home / "cairn" / "dev-servers"
    pids_before = sorted(
        json.loads(p.read_text())["pid"]
        for p in state_dir.glob("*.json")
        if p.parent == state_dir
    )
    assert len(pids_before) == 2

    stop_result = runner.invoke(app, ["dev", "stop", "--all"])
    assert stop_result.exit_code == 0, stop_result.output

    # State files removed.
    remaining = [p for p in state_dir.glob("*.json") if p.parent == state_dir]
    assert remaining == [], remaining

    # Processes gone.
    for pid in pids_before:
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)


def test_dev_list_reports_running_servers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache_home = tmp_path / "cache"
    cache_home.mkdir()
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))

    cairn_dir = _bootstrap_cairn(tmp_path, monkeypatch)
    runner = CliRunner()

    list_empty = runner.invoke(app, ["dev", "list"])
    assert list_empty.exit_code == 0
    assert "no dev servers" in list_empty.output.lower()

    r = runner.invoke(app, ["dev", "serve", "--cairn-path", str(cairn_dir)])
    pid = int(
        next(tok for tok in r.output.split() if tok.startswith("pid=")).split("=")[1]
    )
    try:
        list_one = runner.invoke(app, ["dev", "list"])
        assert list_one.exit_code == 0, list_one.output
        assert str(pid) in list_one.output
        assert "http://127.0.0.1:" in list_one.output
    finally:
        runner.invoke(app, ["dev", "stop", "--all"])


def test_dev_stop_by_pid_kills_one_server(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache_home = tmp_path / "cache"
    cache_home.mkdir()
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))

    cairn_dir = _bootstrap_cairn(tmp_path, monkeypatch)
    runner = CliRunner()

    r = runner.invoke(app, ["dev", "serve", "--cairn-path", str(cairn_dir)])
    assert r.exit_code == 0, r.output
    pid = int(
        next(tok for tok in r.output.split() if tok.startswith("pid=")).split("=")[1]
    )

    stop_result = runner.invoke(app, ["dev", "stop", "--pid", str(pid)])
    try:
        assert stop_result.exit_code == 0, stop_result.output
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)
    finally:
        try:
            os.kill(pid, 15)
        except ProcessLookupError:
            pass
