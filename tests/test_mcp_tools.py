"""Tier-1 MCP tool integration tests.

Exercises the tools through FastMCP's ``call_tool`` rather than the wire
protocol — fast, deterministic, and verifies the tool registration plus the
underlying business logic in one shot.

Skipped if the ``mcp`` extra is not installed.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

pytest.importorskip("mcp")  # the [mcp] extra

from typer.testing import CliRunner

from cairn.cli.app import app
from cairn.mcp.server import build_server

runner = CliRunner()


@pytest.fixture
def cairn_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Scaffold a cairn at tmp_path/c and register it as 'c' in an isolated registry."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.chdir(tmp_path)
    res = runner.invoke(app, ["init", "c", "--no-input"], catch_exceptions=False)
    assert res.exit_code == 0, res.output
    root = tmp_path / "c"
    monkeypatch.chdir(root)  # CLI calls in tests need to find this cairn via cwd-walk
    runner.invoke(
        app, ["collaborator", "add", "--id", "kyle", "--name", "Kyle", "--role", "PI"]
    )
    res = runner.invoke(app, ["register", "c", str(root)], catch_exceptions=False)
    assert res.exit_code == 0, res.output
    return root


def _call(tool: str, args: dict) -> dict | list:
    """Invoke a tool, return the structured-content payload."""
    server = build_server()
    result = asyncio.get_event_loop().run_until_complete(
        server.call_tool(tool, args)
    )
    # FastMCP returns (content_list, structured_content) tuples.
    _, structured = result
    if isinstance(structured, dict) and "result" in structured and len(structured) == 1:
        return structured["result"]
    return structured


def test_whoami_returns_cairn_metadata(cairn_root: Path):
    out = _call("whoami", {"cairn": "c"})
    assert out["cairn"] == "c"
    assert out["cairn_path"] == str(cairn_root)
    assert any(c["id"] == "kyle" for c in out["collaborators"])


def test_status_returns_project_state(cairn_root: Path):
    out = _call("status", {"cairn": "c"})
    assert out["project_name"] == "c"
    assert out["collaborator_count"] == 1


def test_single_cairn_convenience_omits_cairn_param(cairn_root: Path):
    # Only one cairn registered → `cairn` defaults to it.
    out = _call("whoami", {})
    assert out["cairn"] == "c"


def test_add_decision_via_mcp(cairn_root: Path):
    out = _call(
        "add_decision",
        {"author": "kyle", "text": "Use stratified resampling", "cairn": "c"},
    )
    assert out["id"] == "D-001"
    assert out["cairn"] == "c"
    assert "commit_sha" in out


def test_add_decision_rejects_unknown_author(cairn_root: Path):
    with pytest.raises(Exception, match="unknown author"):
        _call(
            "add_decision",
            {"author": "ghost", "text": "shouldn't work", "cairn": "c"},
        )


def test_add_action_and_complete(cairn_root: Path):
    add_out = _call(
        "add_action",
        {"text": "Do the thing", "assignee": "kyle", "cairn": "c"},
    )
    aid = add_out["id"]
    assert aid.startswith("A-")
    complete_out = _call(
        "complete_action", {"id": aid, "by": "kyle", "cairn": "c"}
    )
    assert complete_out["id"] == aid


def test_add_finding_via_mcp(cairn_root: Path):
    out = _call(
        "add_finding",
        {"author": "kyle", "title": "Tested", "cairn": "c", "body": "We saw X."},
    )
    assert out["path"].startswith("knowledge/findings/")
    assert out["path"].endswith("-tested.md")


def test_get_open_questions_returns_list(cairn_root: Path):
    out = _call("get_open_questions", {"cairn": "c"})
    assert out == []


def test_add_collaborator_via_mcp(cairn_root: Path):
    out = _call(
        "add_collaborator",
        {
            "id": "maria",
            "name": "Maria Santos",
            "role": "methods",
            "cairn": "c",
            "email": "maria@example.com",
        },
    )
    assert out["id"] == "maria"
    assert out["cairn"] == "c"
    # And a subsequent decision authored by maria succeeds (the new id is known)
    dec = _call(
        "add_decision",
        {"author": "maria", "text": "method change", "cairn": "c"},
    )
    assert dec["id"].startswith("D-")


def test_add_collaborator_rejects_duplicate_id(cairn_root: Path):
    with pytest.raises(Exception, match="already in use"):
        _call(
            "add_collaborator",
            {"id": "kyle", "name": "K2", "role": "x", "cairn": "c"},
        )


def test_add_open_question_via_mcp(cairn_root: Path):
    out = _call(
        "add_open_question",
        {
            "raised_by": "kyle",
            "question": "Should we resample stratified?",
            "cairn": "c",
        },
    )
    assert out["id"].startswith("Q-")
    # And it now appears in get_open_questions
    listed = _call("get_open_questions", {"cairn": "c"})
    assert len(listed) == 1
    assert listed[0]["id"] == out["id"]


def test_get_action_items_filters_by_assignee(cairn_root: Path):
    # Pre-add two actions, one for kyle, one for maria
    runner.invoke(
        app,
        ["collaborator", "add", "--id", "maria", "--name", "M", "--role", "postdoc"],
    )
    _call("add_action", {"text": "kyle task", "assignee": "kyle", "cairn": "c"})
    _call("add_action", {"text": "maria task", "assignee": "maria", "cairn": "c"})
    kyle_only = _call("get_action_items", {"cairn": "c", "assignee": "kyle"})
    assert len(kyle_only) == 1
    assert kyle_only[0]["assignee"] == "kyle"
