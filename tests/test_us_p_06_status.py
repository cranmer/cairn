"""US-P-06 — Project status snapshot."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from cairn.cli.app import app

runner = CliRunner()


def _populated(cwd: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    runner.invoke(app, ["init", "p", "--pi-name", "PI", "--no-input"], catch_exceptions=False)
    root = cwd / "p"
    monkeypatch.chdir(root)
    runner.invoke(app, ["collaborator", "add", "--id", "kyle", "--name", "K", "--role", "PI"])
    runner.invoke(
        app, ["collaborator", "add", "--id", "maria", "--name", "M", "--role", "postdoc"]
    )
    for _ in range(3):
        runner.invoke(app, ["decision", "add", "--author", "kyle", "--text", "A decision"])
    # Add some open questions and actions directly to the YAML.
    (root / "state" / "open_questions.yaml").write_text(
        yaml.safe_dump(
            [
                {
                    "id": "Q-001",
                    "raised_by": "maria",
                    "date": "2026-05-01T00:00:00Z",
                    "question": "is X true",
                },
                {
                    "id": "Q-002",
                    "raised_by": "maria",
                    "date": "2026-05-02T00:00:00Z",
                    "question": "is Y true",
                },
            ]
        )
    )
    (root / "state" / "action_items.yaml").write_text(
        yaml.safe_dump(
            [
                {
                    "id": "A-001",
                    "assignee": "kyle",
                    "text": "draft outline",
                    "created": "2026-05-01T00:00:00Z",
                    "due_date": "2026-05-10",
                    "status": "open",
                },
                {
                    "id": "A-002",
                    "assignee": "maria",
                    "text": "rerun model",
                    "created": "2026-05-01T00:00:00Z",
                    "status": "open",
                },
            ]
        )
    )
    return root


def test_us_p_06_text_output_under_30_lines(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    _populated(cwd, monkeypatch)
    res = runner.invoke(app, ["status"], catch_exceptions=False)
    assert res.exit_code == 0, res.output
    assert len(res.output.splitlines()) <= 30
    assert "Open questions: 2" in res.output
    assert "Incomplete actions: 2" in res.output


def test_us_p_06_json_parses_and_has_required_keys(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    _populated(cwd, monkeypatch)
    res = runner.invoke(app, ["status", "--json"], catch_exceptions=False)
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["open_question_count"] == 2
    assert data["incomplete_action_count"] == 2
    assert isinstance(data["recent_decisions"], list)
    assert len(data["recent_decisions"]) == 3


def test_us_p_06_recent_decisions_capped_at_five(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    _populated(cwd, monkeypatch)
    for _ in range(5):
        runner.invoke(app, ["decision", "add", "--author", "kyle", "--text", "more"])
    res = runner.invoke(app, ["status", "--json"], catch_exceptions=False)
    data = json.loads(res.output)
    assert len(data["recent_decisions"]) == 5


def test_us_p_06_findings_surfaced_in_status(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    """`cairn status` reports finding count and the most recent few."""
    _populated(cwd, monkeypatch)
    runner.invoke(
        app, ["finding", "add", "--author", "kyle", "--title", "Result A"], catch_exceptions=False
    )
    runner.invoke(
        app, ["finding", "add", "--author", "kyle", "--title", "Result B"], catch_exceptions=False
    )
    res = runner.invoke(app, ["status", "--json"], catch_exceptions=False)
    data = json.loads(res.output)
    assert data["finding_count"] == 2
    assert {f["title"] for f in data["recent_findings"]} == {"Result A", "Result B"}
    text = runner.invoke(app, ["status"], catch_exceptions=False).output
    assert "Findings: 2 total" in text


def test_us_p_06_overdue_action_counted(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _populated(cwd, monkeypatch)
    raw = yaml.safe_load((root / "state" / "action_items.yaml").read_text())
    raw[0]["due_date"] = "2020-01-01"  # well in the past
    (root / "state" / "action_items.yaml").write_text(yaml.safe_dump(raw))
    res = runner.invoke(app, ["status", "--json"], catch_exceptions=False)
    data = json.loads(res.output)
    assert data["action_breakdown"]["overdue"] >= 1


def test_us_p_06_latest_meeting_surfaced(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _populated(cwd, monkeypatch)
    (root / "knowledge" / "meetings" / "2026-05-10.md").write_text("# Meeting\n")
    (root / "knowledge" / "meetings" / "2026-05-15.md").write_text("# Meeting\n")
    res = runner.invoke(app, ["status", "--json"], catch_exceptions=False)
    data = json.loads(res.output)
    assert data["latest_meeting"] == "2026-05-15"


def test_us_p_06_branch_flag_reads_branch_view(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    """A branch with a different decisions file shows different recent_decisions."""
    from git import Repo

    root = _populated(cwd, monkeypatch)
    repo = Repo(root)
    # On main: 3 decisions. Create a branch with one extra decision.
    repo.git.checkout("-b", "feature/extra")
    runner.invoke(app, ["decision", "add", "--author", "kyle", "--text", "branch-only"])
    # Switch back to main:
    main_branch = "master" if "master" in [h.name for h in repo.heads] else "main"
    repo.git.checkout(main_branch)

    res_main = runner.invoke(app, ["status", "--json"], catch_exceptions=False)
    res_branch = runner.invoke(
        app, ["status", "--json", "--branch", "feature/extra"], catch_exceptions=False
    )
    main_count = len(json.loads(res_main.output)["recent_decisions"])
    branch_count = len(json.loads(res_branch.output)["recent_decisions"])
    assert branch_count == main_count + 1
