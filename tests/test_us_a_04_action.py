"""US-A-04 — Mark an action item complete (and US-P style coverage for `cairn action add`)."""

from __future__ import annotations

from pathlib import Path

import pytest
from git import Repo
from typer.testing import CliRunner

from cairn.cli.app import app
from cairn.io.state_io import load_actions
from cairn.paths import CairnPaths

runner = CliRunner()


def _bootstrap(cwd: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    runner.invoke(app, ["init", "p", "--no-input"], catch_exceptions=False)
    root = cwd / "p"
    monkeypatch.chdir(root)
    runner.invoke(app, ["collaborator", "add", "--id", "kyle", "--name", "K", "--role", "PI"])
    return root


def test_action_add_auto_id_and_records_assignee(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _bootstrap(cwd, monkeypatch)
    res = runner.invoke(
        app,
        ["action", "add", "--assignee", "kyle", "--text", "draft outline"],
        catch_exceptions=False,
    )
    assert res.exit_code == 0, res.output
    actions = load_actions(CairnPaths(root=root))
    assert len(actions) == 1
    assert actions[0].id == "A-001"
    assert actions[0].assignee == "kyle"
    assert actions[0].status == "open"


def test_action_add_unknown_assignee_errors(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    _bootstrap(cwd, monkeypatch)
    res = runner.invoke(
        app,
        ["action", "add", "--assignee", "ghost", "--text", "x"],
        catch_exceptions=False,
    )
    assert res.exit_code != 0
    assert "ghost" in res.output


def test_action_add_due_date_parsed(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _bootstrap(cwd, monkeypatch)
    runner.invoke(
        app,
        [
            "action", "add",
            "--assignee", "kyle",
            "--text", "ship it",
            "--due-date", "2026-06-15",
        ],
        catch_exceptions=False,
    )
    a = load_actions(CairnPaths(root=root))[0]
    assert a.due_date.isoformat() == "2026-06-15"


def test_action_add_bad_due_date_errors(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    _bootstrap(cwd, monkeypatch)
    res = runner.invoke(
        app,
        ["action", "add", "--assignee", "kyle", "--text", "x", "--due-date", "tomorrow"],
        catch_exceptions=False,
    )
    assert res.exit_code != 0


def test_us_a_04_complete_records_history_and_does_not_delete(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    root = _bootstrap(cwd, monkeypatch)
    runner.invoke(app, ["action", "add", "--assignee", "kyle", "--text", "ship it"])
    res = runner.invoke(app, ["action", "complete", "A-001"], catch_exceptions=False)
    assert res.exit_code == 0, res.output
    actions = load_actions(CairnPaths(root=root))
    assert len(actions) == 1  # not deleted
    completed = actions[0]
    assert completed.status == "complete"
    assert completed.completed_by == "kyle"
    assert completed.completed_at is not None


def test_us_a_04_completer_defaults_to_assignee(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    root = _bootstrap(cwd, monkeypatch)
    runner.invoke(app, ["action", "add", "--assignee", "kyle", "--text", "x"])
    runner.invoke(app, ["action", "complete", "A-001"])
    a = load_actions(CairnPaths(root=root))[0]
    assert a.completed_by == "kyle"


def test_us_a_04_complete_by_other_collaborator(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    root = _bootstrap(cwd, monkeypatch)
    runner.invoke(app, ["collaborator", "add", "--id", "maria", "--name", "M", "--role", "postdoc"])
    runner.invoke(app, ["action", "add", "--assignee", "kyle", "--text", "x"])
    res = runner.invoke(
        app, ["action", "complete", "A-001", "--by", "maria"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.output
    a = load_actions(CairnPaths(root=root))[0]
    assert a.completed_by == "maria"


def test_us_a_04_complete_unknown_id_errors(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    _bootstrap(cwd, monkeypatch)
    res = runner.invoke(app, ["action", "complete", "A-999"], catch_exceptions=False)
    assert res.exit_code != 0
    assert "A-999" in res.output


def test_us_a_04_complete_already_complete_errors(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    _bootstrap(cwd, monkeypatch)
    runner.invoke(app, ["action", "add", "--assignee", "kyle", "--text", "x"])
    runner.invoke(app, ["action", "complete", "A-001"])
    res = runner.invoke(app, ["action", "complete", "A-001"], catch_exceptions=False)
    assert res.exit_code != 0
    assert "already complete" in res.output.lower()


def test_us_a_04_commit_message_references_id(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    root = _bootstrap(cwd, monkeypatch)
    runner.invoke(app, ["action", "add", "--assignee", "kyle", "--text", "ship it"])
    runner.invoke(app, ["action", "complete", "A-001"])
    repo = Repo(root)
    head = next(repo.iter_commits())
    assert "A-001" in head.message
    assert head.author.email == "test@example.com"
