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


def test_get_project_md_returns_content(cairn_root: Path):
    out = _call("get_project_md", {"cairn": "c"})
    assert out["exists"] is True
    # The bundled template's PROJECT.md should have a header.
    assert out["content"].startswith("#")


def test_set_project_md_overwrites_and_commits(cairn_root: Path):
    new_content = "# Overhauled\n\nFresh content.\n"
    out = _call(
        "set_project_md",
        {"author": "kyle", "content": new_content, "cairn": "c"},
    )
    assert "commit_sha" in out
    # Round-trip via get_project_md
    got = _call("get_project_md", {"cairn": "c"})
    assert got["content"] == new_content


def test_set_project_md_rejects_unknown_author(cairn_root: Path):
    with pytest.raises(Exception, match="unknown author"):
        _call(
            "set_project_md",
            {"author": "ghost", "content": "x", "cairn": "c"},
        )


def test_add_collaborator_accepts_unknown_type(cairn_root: Path):
    """OQ-5 stopgap: `type='unknown'` enables placeholder identities like
    `repo-history` for bootstrap attribution. `type='group'` is the
    parallel value for genuine multi-person aggregates (consensus,
    core-team) — both shipped together as the rename of the original
    `virtual` value."""
    out = _call(
        "add_collaborator",
        {
            "id": "repo-history",
            "name": "Repository history",
            "role": "bootstrap-attribution placeholder",
            "type": "unknown",
        },
    )
    assert out["id"] == "repo-history"
    # Findings can then be attributed to the placeholder collaborator
    f = _call(
        "add_finding",
        {
            "author": "repo-history",
            "title": "Extracted from docs/X.md",
            "body": "Observation derived from repo state.",
        },
    )
    assert "commit_sha" in f


def test_add_collaborator_accepts_group_type(cairn_root: Path):
    out = _call(
        "add_collaborator",
        {
            "id": "consensus",
            "name": "Project consensus",
            "role": "group decision-making placeholder",
            "type": "group",
        },
    )
    assert out["id"] == "consensus"


def test_add_collaborator_rejects_virtual_type(cairn_root: Path):
    """The original `virtual` value was renamed to group/unknown; ensure
    `virtual` no longer validates so we don't accidentally accept the old
    name silently."""
    with pytest.raises(Exception, match=r"(Literal|virtual|validation)"):
        _call(
            "add_collaborator",
            {
                "id": "ghost-type",
                "name": "x",
                "role": "x",
                "type": "virtual",
            },
        )


def test_add_open_question_accepts_backdated_date(cairn_root: Path):
    """Question writes can be backdated like decisions/findings/actions."""
    out = _call(
        "add_open_question",
        {
            "raised_by": "kyle",
            "question": "Should we resample stratified?",
            "date": "2025-09-10T09:00:00Z",
        },
    )
    listed = _call("get_open_questions", {})
    rec = next(q for q in listed if q["id"] == out["id"])
    assert rec["date"].startswith("2025-09-10")


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


def test_whoami_returns_git_match_suggestion(cairn_root: Path):
    out = _call("whoami", {})
    # Test conftest sets GIT_AUTHOR_EMAIL=test@example.com; whoami reads
    # git config which is whatever the local env reports. Just check shape.
    assert "git_email" in out
    assert "suggested_id" in out


def test_list_collaborators(cairn_root: Path):
    out = _call("list_collaborators", {})
    assert isinstance(out, list)
    assert any(c["id"] == "kyle" for c in out)


def test_list_and_get_decision(cairn_root: Path):
    _call("add_decision", {"author": "kyle", "text": "first", "cairn": "c"})
    _call("add_decision", {"author": "kyle", "text": "second resampling change", "cairn": "c"})
    listed = _call("list_decisions", {})
    assert len(listed) == 2
    # Newest first
    assert listed[0]["decision"] == "second resampling change"
    # Filter by query
    filt = _call("list_decisions", {"query": "resampling"})
    assert len(filt) == 1
    # Single fetch
    got = _call("get_decision", {"id": listed[0]["id"]})
    assert got["id"] == listed[0]["id"]


def test_list_and_get_finding(cairn_root: Path):
    add = _call(
        "add_finding",
        {"author": "kyle", "title": "Found a thing", "cairn": "c", "body": "body"},
    )
    assert "slug" in add  # new in this commit
    slug = add["slug"]
    listed = _call("list_findings", {})
    assert len(listed) == 1
    assert listed[0]["slug"] == slug
    got = _call("get_finding", {"slug": slug})
    assert got["frontmatter"]["title"] == "Found a thing"
    assert "body" in got["body"]


def test_resolve_open_question(cairn_root: Path):
    q = _call(
        "add_open_question",
        {"raised_by": "kyle", "question": "Should we X?", "cairn": "c"},
    )
    d = _call(
        "add_decision",
        {"author": "kyle", "text": "Yes, do X.", "cairn": "c", "related": [q["id"]]},
    )
    out = _call(
        "resolve_open_question",
        {"id": q["id"], "answered_by": d["id"], "actor": "kyle", "cairn": "c"},
    )
    assert out["id"] == q["id"]
    # No longer open
    open_qs = _call("get_open_questions", {})
    assert all(qq["status"] != "open" or qq["id"] != q["id"] for qq in open_qs) or (
        not any(qq["id"] == q["id"] and qq["status"] == "open" for qq in open_qs)
    )


def test_start_and_close_exploration_via_mcp(cairn_root: Path):
    out = _call(
        "start_exploration",
        {"description": "try alt loss", "as_id": "kyle", "cairn": "c"},
    )
    assert out["name"] == "kyle/try-alt-loss"
    closed = _call(
        "close_exploration",
        {
            "name": "kyle/try-alt-loss",
            "status": "abandoned",
            "reason": "explored, set aside",
            "closed_by": "kyle",
            "cairn": "c",
        },
    )
    assert closed["status"] == "abandoned"


def test_unknown_author_message_points_at_mcp_tool(cairn_root: Path):
    with pytest.raises(Exception, match="add_collaborator"):
        _call(
            "add_decision",
            {"author": "ghost", "text": "no", "cairn": "c"},
        )


def test_semantic_project_section_round_trip(cairn_root: Path):
    """Each project section is independently readable and writable."""
    # Overview
    out = _call("get_project_overview", {})
    assert out["exists"] is True  # template ships with placeholder content
    upd = _call(
        "set_project_overview",
        {"author": "kyle", "content": "Brand new overview body."},
    )
    assert "commit_sha" in upd
    got = _call("get_project_overview", {})
    assert "Brand new overview body." in got["content"]

    # Current focus stays untouched
    cf = _call("get_current_focus", {})
    assert cf["exists"] is True

    # Updating current focus doesn't disturb overview
    _call(
        "set_current_focus",
        {"author": "kyle", "content": "- item A\n- item B"},
    )
    overview2 = _call("get_project_overview", {})
    assert "Brand new overview body." in overview2["content"]
    focus2 = _call("get_current_focus", {})
    assert "item A" in focus2["content"]


def test_semantic_setter_rejects_unknown_author(cairn_root: Path):
    with pytest.raises(Exception, match="unknown author"):
        _call(
            "set_project_overview",
            {"author": "ghost", "content": "x"},
        )


def test_start_exploration_returns_branch_name_and_merge_state(cairn_root: Path):
    out = _call(
        "start_exploration",
        {"description": "test branch info", "as_id": "kyle"},
    )
    assert out["branch_name"] == "kyle/test-branch-info"
    assert out["merge_state"] == "active"


def test_add_decision_accepts_backdated_date_and_source_refs(cairn_root: Path):
    """B1 + B2: writes accept explicit date and structured provenance fields."""
    out = _call(
        "add_decision",
        {
            "author": "kyle",
            "text": "Use stratified resampling",
            "context": "Per PR #74",
            "date": "2025-11-15T14:30:00Z",
            "source_prs": ["74"],
            "source_commits": ["62bc70e", "fc0c9b5"],
        },
    )
    assert out["id"] == "D-001"
    # Round-trip via get_decision
    d = _call("get_decision", {"id": "D-001"})
    assert d["date"].startswith("2025-11-15")  # not today
    assert d["source_prs"] == ["74"]
    assert "62bc70e" in d["source_commits"]


def test_add_finding_accepts_backdated_date(cairn_root: Path):
    out = _call(
        "add_finding",
        {
            "author": "kyle",
            "title": "Backdated learning",
            "body": "We discovered X.",
            "date": "2026-01-15T12:00:00Z",
            "source_prs": ["12"],
        },
    )
    # File should be named after the backdated date, not today
    assert out["date"] == "2026-01-15"
    assert out["path"].startswith("knowledge/findings/2026-01-15-")


def test_add_decision_rejects_unparseable_date(cairn_root: Path):
    with pytest.raises(Exception, match="invalid date"):
        _call(
            "add_decision",
            {"author": "kyle", "text": "x", "date": "not a date"},
        )


def test_status_suggests_bootstrap_when_empty(cairn_root: Path):
    out = _call("status", {})
    assert out.get("suggested_next") is not None
    assert "bootstrap" in out["suggested_next"].lower()


def test_status_clears_suggestion_after_first_write(cairn_root: Path):
    _call("add_decision", {"author": "kyle", "text": "first"})
    out = _call("status", {})
    assert out.get("suggested_next") is None


def test_list_skills_returns_bundled_skills(cairn_root: Path):
    out = _call("list_skills", {})
    names = {s["name"] for s in out}
    # Bundled skills shipped with the template
    assert "orient" in names
    assert "bootstrap_from_repo" in names
    assert "log-finding" in names
    # Each has a description
    for s in out:
        assert s["description"] is None or isinstance(s["description"], str)


def test_get_skill_returns_full_content(cairn_root: Path):
    out = _call("get_skill", {"name": "bootstrap_from_repo"})
    assert out["name"] == "bootstrap_from_repo"
    assert "# Bootstrap a cairn from a project repository" in out["content"]


def test_get_skill_rejects_unknown_name(cairn_root: Path):
    with pytest.raises(Exception, match="no skill named 'nope'"):
        _call("get_skill", {"name": "nope"})


def test_server_instructions_describe_what_cairn_is(cairn_root: Path):
    """The server-level instructions text must orient an agent connecting
    fresh — what cairn is, the four entity types, the facilitator posture,
    and the bootstrap pointer. Guard against silent regression."""
    server = build_server()
    instructions = server.instructions or ""
    assert "shared project memory" in instructions
    assert "decisions, findings, open questions, and action items" in instructions
    # Facilitator posture
    assert "facilitator" in instructions.lower()
    assert "note-taker" in instructions.lower()
    # Bootstrap pointer
    assert "bootstrap_from_repo" in instructions


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
