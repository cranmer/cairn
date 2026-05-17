"""US-P-04 — Record a decision."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from git import Repo
from typer.testing import CliRunner

from cairn.cli.app import app
from cairn.io.state_io import load_decisions
from cairn.paths import CairnPaths

runner = CliRunner()


def _bootstrap(cwd: Path, monkeypatch: pytest.MonkeyPatch, name: str = "p") -> Path:
    runner.invoke(app, ["init", name, "--pi-name", "PI", "--no-input"], catch_exceptions=False)
    root = cwd / name
    monkeypatch.chdir(root)
    runner.invoke(
        app, ["collaborator", "add", "--id", "kyle", "--name", "Kyle", "--role", "PI"]
    )
    return root


def test_us_p_04_auto_id_starts_at_d_001(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _bootstrap(cwd, monkeypatch)
    res = runner.invoke(
        app,
        ["decision", "add", "--author", "kyle", "--text", "Use stratified resampling"],
        catch_exceptions=False,
    )
    assert res.exit_code == 0, res.output
    decisions = load_decisions(CairnPaths(root=root))
    assert decisions[0].id == "D-001"


def test_us_p_04_auto_id_increments(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _bootstrap(cwd, monkeypatch)
    runner.invoke(app, ["decision", "add", "--author", "kyle", "--text", "First"])
    runner.invoke(app, ["decision", "add", "--author", "kyle", "--text", "Second"])
    ids = [d.id for d in load_decisions(CairnPaths(root=root))]
    assert ids == ["D-001", "D-002"]


def test_us_p_04_timestamp_is_iso_utc(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _bootstrap(cwd, monkeypatch)
    runner.invoke(app, ["decision", "add", "--author", "kyle", "--text", "Decided"])
    text = (root / "state" / "decisions.yaml").read_text()
    assert re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", text)


def test_us_p_04_unknown_author_errors(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    _bootstrap(cwd, monkeypatch)
    res = runner.invoke(
        app,
        ["decision", "add", "--author", "ghost", "--text", "x"],
        catch_exceptions=False,
    )
    assert res.exit_code != 0
    assert "unknown author" in res.output.lower()


def test_us_p_04_related_must_exist(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    _bootstrap(cwd, monkeypatch)
    res = runner.invoke(
        app,
        ["decision", "add", "--author", "kyle", "--text", "x", "--related", "Q-999"],
        catch_exceptions=False,
    )
    assert res.exit_code != 0
    assert "Q-999" in res.output


def test_us_p_04_supersedes_sets_back_reference(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _bootstrap(cwd, monkeypatch)
    runner.invoke(app, ["decision", "add", "--author", "kyle", "--text", "Original"])
    res = runner.invoke(
        app,
        [
            "decision", "add",
            "--author", "kyle",
            "--text", "Replacement",
            "--supersedes", "D-001",
        ],
        catch_exceptions=False,
    )
    assert res.exit_code == 0, res.output
    decisions = load_decisions(CairnPaths(root=root))
    by_id = {d.id: d for d in decisions}
    assert by_id["D-001"].superseded_by == "D-002"
    assert by_id["D-002"].supersedes == "D-001"


def test_us_p_04_supersedes_unknown_errors(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    _bootstrap(cwd, monkeypatch)
    res = runner.invoke(
        app,
        ["decision", "add", "--author", "kyle", "--text", "x", "--supersedes", "D-099"],
        catch_exceptions=False,
    )
    assert res.exit_code != 0
    assert "D-099" in res.output


def test_us_p_04_commit_message_references_id(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _bootstrap(cwd, monkeypatch)
    runner.invoke(app, ["decision", "add", "--author", "kyle", "--text", "Use SMOTE"])
    repo = Repo(root)
    head = next(repo.iter_commits())
    assert head.message.startswith("D-001:")
    assert head.author.email == "test@example.com"
