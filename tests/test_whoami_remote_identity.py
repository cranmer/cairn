"""Regression tests for caller-identity threading over remote MCP.

The remote MCP server has no access to the caller's local ``git config``,
so ``whoami`` was returning ``git_email=null`` for every HTTP caller. The
client now stamps ``X-Cairn-Git-Email`` / ``X-Cairn-Git-Name`` headers on
every request and the server's ``_suggest_collaborator_match`` prefers
that header over its local-shell fallback.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("mcp")


def test_call_tool_stamps_identity_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every remote call must include X-Cairn-Git-Email + X-Cairn-Git-Name."""
    from cairn.mcp import remote

    monkeypatch.setattr(
        remote,
        "_resolve_caller_identity",
        lambda: ("kyle@example.com", "Kyle Example"),
    )

    captured: list[dict[str, str]] = []

    class _FakeResp:
        def __init__(self) -> None:
            self.headers = {"Mcp-Session-Id": "abc123"}

        def read(self) -> bytes:
            return b'{"jsonrpc":"2.0","id":1,"result":{}}'

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def _fake_urlopen(req, timeout=30):
        captured.append(dict(req.headers))
        return _FakeResp()

    monkeypatch.setattr(remote.urllib.request, "urlopen", _fake_urlopen)

    remote.call_tool("http://srv.example.com/mcp", "whoami", {}, token="tok")

    # Every POST that made it out should have stamped the identity.
    assert captured, "no requests were dispatched"
    for headers in captured:
        # urllib title-cases header keys.
        assert headers.get("X-cairn-git-email") == "kyle@example.com", headers
        assert headers.get("X-cairn-git-name") == "Kyle Example", headers


def test_call_tool_omits_headers_when_identity_unresolvable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the local git identity can't be resolved we send no identity headers."""
    from cairn.mcp import remote

    monkeypatch.setattr(remote, "_resolve_caller_identity", lambda: (None, None))

    captured: list[dict[str, str]] = []

    class _FakeResp:
        def __init__(self) -> None:
            self.headers = {"Mcp-Session-Id": "abc123"}

        def read(self) -> bytes:
            return b'{"jsonrpc":"2.0","id":1,"result":{}}'

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(
        remote.urllib.request,
        "urlopen",
        lambda req, timeout=30: captured.append(dict(req.headers)) or _FakeResp(),
    )

    remote.call_tool("http://srv.example.com/mcp", "whoami", {}, token="tok")

    for headers in captured:
        assert "X-cairn-git-email" not in headers
        assert "X-cairn-git-name" not in headers


def test_whoami_prefers_header_email_over_local_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Server side: when the X-Cairn-Git-Email header is set, _suggest_collaborator_match
    uses it (matching against the cairn's collaborators) rather than the host's
    local git config. Simulates the HTTP path in-process by populating the
    ``request_ctx`` contextvar that the streamable-http transport sets."""
    from typer.testing import CliRunner

    from cairn.cli.app import app
    from cairn.mcp.server import _suggest_collaborator_match
    from cairn.paths import CairnPaths
    from cairn.schemas import Collaborator

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    res = runner.invoke(app, ["init", "c", "--no-input"], catch_exceptions=False)
    assert res.exit_code == 0, res.output
    root = tmp_path / "c"
    paths = CairnPaths(root=root)

    class _FakeHeaders:
        def __init__(self, mapping: dict[str, str]):
            self._mapping = {k.lower(): v for k, v in mapping.items()}

        def get(self, key, default=None):
            return self._mapping.get(key.lower(), default)

    class _FakeRequest:
        def __init__(self, headers: dict[str, str]):
            self.headers = _FakeHeaders(headers)

    class _FakeRequestContext:
        def __init__(self, request):
            self.request = request

    from mcp.server.lowlevel.server import request_ctx

    fake_rc = _FakeRequestContext(_FakeRequest({"X-Cairn-Git-Email": "kyle@example.com"}))
    collabs = [
        Collaborator(id="kyle", name="Kyle", role="PI", email="kyle@example.com"),
        Collaborator(id="lila", name="Lila", role="postdoc", email="lila@example.com"),
    ]
    token = request_ctx.set(fake_rc)
    try:
        out = _suggest_collaborator_match(paths, collabs)
    finally:
        request_ctx.reset(token)

    assert out["git_email"] == "kyle@example.com"
    assert out["suggested_id"] == "kyle"


def test_whoami_falls_back_to_local_git_without_header(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No request context (stdio path) → the existing local-git fallback runs."""
    from typer.testing import CliRunner

    from cairn.cli.app import app
    from cairn.mcp.server import _suggest_collaborator_match
    from cairn.paths import CairnPaths

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(app, ["init", "c", "--no-input"], catch_exceptions=False)
    root = tmp_path / "c"
    paths = CairnPaths(root=root)

    # No request_ctx is set → _caller_email_from_headers returns None and the
    # function falls through to its `git config` subprocess (which conftest
    # arranges via env vars to be a known-good value).
    import subprocess

    def _fake_run(args, **kwargs):
        class _R:
            returncode = 0
            stdout = "fallback@example.com\n"

        return _R()

    monkeypatch.setattr(subprocess, "run", _fake_run)
    out = _suggest_collaborator_match(paths, [])
    assert out["git_email"] == "fallback@example.com"
