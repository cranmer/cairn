"""US-A-03 — Create an exploration branch."""

from __future__ import annotations

from pathlib import Path

import pytest
from git import Repo
from typer.testing import CliRunner

from cairn.cli.app import app

runner = CliRunner()


def _bootstrap(cwd: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    runner.invoke(app, ["init", "p", "--no-input"], catch_exceptions=False)
    root = cwd / "p"
    monkeypatch.chdir(root)
    runner.invoke(app, ["collaborator", "add", "--id", "kyle", "--name", "K", "--role", "PI"])
    return root


def test_us_a_03_creates_branch_with_owner_prefix(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    root = _bootstrap(cwd, monkeypatch)
    res = runner.invoke(
        app, ["branch", "start", "Try Alt Loss Function"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.output
    repo = Repo(root)
    assert "kyle/try-alt-loss-function" in [h.name for h in repo.heads]
    assert repo.active_branch.name == "kyle/try-alt-loss-function"


def test_us_a_03_writes_branch_manifest(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _bootstrap(cwd, monkeypatch)
    runner.invoke(app, ["branch", "start", "try alt loss"], catch_exceptions=False)
    manifest = root / "branches" / "kyle" / "try-alt-loss.md"
    assert manifest.is_file()
    text = manifest.read_text()
    assert "kyle/try-alt-loss" in text
    assert "try alt loss" in text


def test_us_a_03_updates_branches_readme_on_main(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    root = _bootstrap(cwd, monkeypatch)
    runner.invoke(app, ["branch", "start", "try alt loss"], catch_exceptions=False)
    repo = Repo(root)
    main_branch = "master" if "master" in [h.name for h in repo.heads] else "main"
    text = repo.git.show(f"{main_branch}:branches/README.md")
    assert "kyle/try-alt-loss" in text
    assert "kyle" in text


def test_us_a_03_user_left_on_new_branch(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _bootstrap(cwd, monkeypatch)
    runner.invoke(app, ["branch", "start", "try alt loss"], catch_exceptions=False)
    repo = Repo(root)
    assert repo.active_branch.name == "kyle/try-alt-loss"


def test_us_a_03_collision_prompts_for_resolution(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    _bootstrap(cwd, monkeypatch)
    runner.invoke(app, ["branch", "start", "try alt loss"], catch_exceptions=False)
    # Return to main before trying to create a same-named branch
    Repo(".").git.checkout("master" if "master" in [h.name for h in Repo(".").heads] else "main")
    res = runner.invoke(
        app, ["branch", "start", "try alt loss"], catch_exceptions=False
    )
    assert res.exit_code != 0
    assert "already exists" in res.output.lower()


def test_us_a_03_requires_as_when_multiple_collaborators(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    _bootstrap(cwd, monkeypatch)
    runner.invoke(app, ["collaborator", "add", "--id", "maria", "--name", "M", "--role", "postdoc"])
    res = runner.invoke(app, ["branch", "start", "explore X"], catch_exceptions=False)
    assert res.exit_code != 0
    assert "--as" in res.output


def test_us_a_03_as_flag_picks_collaborator(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    root = _bootstrap(cwd, monkeypatch)
    runner.invoke(app, ["collaborator", "add", "--id", "maria", "--name", "M", "--role", "postdoc"])
    res = runner.invoke(
        app, ["branch", "start", "explore X", "--as", "maria"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.output
    assert (root / "branches" / "maria" / "explore-x.md").is_file()


def test_us_a_03_unknown_as_id_errors(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    _bootstrap(cwd, monkeypatch)
    res = runner.invoke(
        app, ["branch", "start", "explore X", "--as", "ghost"], catch_exceptions=False
    )
    assert res.exit_code != 0
    assert "ghost" in res.output


def test_us_a_03_commits_attributed_to_user(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _bootstrap(cwd, monkeypatch)
    runner.invoke(app, ["branch", "start", "try alt loss"], catch_exceptions=False)
    repo = Repo(root)
    head = next(repo.iter_commits())
    assert "manifest" in head.message
    assert head.author.email == "test@example.com"
