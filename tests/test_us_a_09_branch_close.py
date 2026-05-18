"""US-A-09 — Close an exploration branch."""

from __future__ import annotations

from pathlib import Path

import pytest
from git import Repo
from typer.testing import CliRunner

from cairn.cli.app import app

runner = CliRunner()


def _bootstrap(cwd: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, str]:
    """Init a cairn with one collaborator and one exploration branch; return (root, main_name)."""
    runner.invoke(app, ["init", "p", "--no-input"], catch_exceptions=False)
    root = cwd / "p"
    monkeypatch.chdir(root)
    runner.invoke(
        app, ["collaborator", "add", "--id", "kyle", "--name", "K", "--role", "PI"]
    )
    repo = Repo(root)
    main_name = "master" if "master" in [h.name for h in repo.heads] else "main"
    runner.invoke(app, ["branch", "start", "try alt loss"], catch_exceptions=False)
    repo.git.checkout(main_name)
    return root, main_name


def test_us_a_09_abandoned_path(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root, _ = _bootstrap(cwd, monkeypatch)
    res = runner.invoke(
        app,
        [
            "branch", "close", "kyle/try-alt-loss",
            "--status", "abandoned",
            "--reason", "explored, did not pan out",
        ],
        catch_exceptions=False,
    )
    assert res.exit_code == 0, res.output
    manifest = (root / "branches" / "kyle" / "try-alt-loss.md").read_text()
    assert "## Closure" in manifest
    assert "Status**: abandoned" in manifest
    assert "explored, did not pan out" in manifest
    readme = (root / "branches" / "README.md").read_text()
    assert "## Closed branches" in readme
    assert "abandoned" in readme
    # The row should not still be in the active table:
    active_section = readme.split("## Closed branches", 1)[0]
    assert "`kyle/try-alt-loss`" not in active_section


def test_us_a_09_merged_path(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root, _main_name = _bootstrap(cwd, monkeypatch)
    repo = Repo(root)
    # Fast-forward merge: no new commit is created, so the test sidesteps the
    # environment's commit-signing infrastructure. cairn branch close only cares
    # that the branch is an ancestor of main — ff and no-ff both satisfy that.
    repo.git.merge("kyle/try-alt-loss", "--ff-only")
    res = runner.invoke(
        app,
        [
            "branch", "close", "kyle/try-alt-loss",
            "--status", "merged",
            "--reason", "findings promoted",
        ],
        catch_exceptions=False,
    )
    assert res.exit_code == 0, res.output
    manifest = (root / "branches" / "kyle" / "try-alt-loss.md").read_text()
    assert "Status**: merged" in manifest
    assert "Merge commit**:" in manifest


def test_us_a_09_refuses_merged_when_not_merged(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    _bootstrap(cwd, monkeypatch)  # branch is not merged
    res = runner.invoke(
        app,
        [
            "branch", "close", "kyle/try-alt-loss",
            "--status", "merged",
            "--reason", "lying",
        ],
        catch_exceptions=False,
    )
    assert res.exit_code != 0
    assert "not an ancestor" in res.output.lower()


def test_us_a_09_refuses_unknown_branch(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    _bootstrap(cwd, monkeypatch)
    res = runner.invoke(
        app,
        [
            "branch", "close", "kyle/never-existed",
            "--status", "abandoned",
            "--reason", "n/a",
        ],
        catch_exceptions=False,
    )
    assert res.exit_code != 0
    assert "does not exist" in res.output.lower()


def test_us_a_09_refuses_invalid_status(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    _bootstrap(cwd, monkeypatch)
    res = runner.invoke(
        app,
        [
            "branch", "close", "kyle/try-alt-loss",
            "--status", "shipped",
            "--reason", "x",
        ],
        catch_exceptions=False,
    )
    assert res.exit_code != 0
    assert "--status must be" in res.output.lower()


def test_us_a_09_refuses_empty_reason(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    _bootstrap(cwd, monkeypatch)
    res = runner.invoke(
        app,
        [
            "branch", "close", "kyle/try-alt-loss",
            "--status", "abandoned",
            "--reason", "   ",
        ],
        catch_exceptions=False,
    )
    assert res.exit_code != 0


def test_us_a_09_refuses_non_owner_slug_form(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    _bootstrap(cwd, monkeypatch)
    res = runner.invoke(
        app,
        [
            "branch", "close", "main",
            "--status", "abandoned",
            "--reason", "no",
        ],
        catch_exceptions=False,
    )
    assert res.exit_code != 0
    assert "owner" in res.output.lower() or "slug" in res.output.lower()


def test_us_a_09_refuses_when_not_on_main(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    _bootstrap(cwd, monkeypatch)
    # Switch to the exploration branch (i.e. not main)
    Repo(".").git.checkout("kyle/try-alt-loss")
    res = runner.invoke(
        app,
        [
            "branch", "close", "kyle/try-alt-loss",
            "--status", "abandoned",
            "--reason", "x",
        ],
        catch_exceptions=False,
    )
    assert res.exit_code != 0
    assert "switch to" in res.output.lower()


def test_us_a_09_refuses_dirty_working_tree_without_force(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    root, _ = _bootstrap(cwd, monkeypatch)
    # Make the working tree dirty by editing a tracked file.
    (root / "README.md").write_text("dirty\n")
    res = runner.invoke(
        app,
        [
            "branch", "close", "kyle/try-alt-loss",
            "--status", "abandoned",
            "--reason", "x",
        ],
        catch_exceptions=False,
    )
    assert res.exit_code != 0
    assert "uncommitted" in res.output.lower()


def test_us_a_09_unknown_closed_by_errors(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    _bootstrap(cwd, monkeypatch)
    # Add a second collaborator so --closed-by is required.
    runner.invoke(app, ["collaborator", "add", "--id", "maria", "--name", "M", "--role", "postdoc"])
    res = runner.invoke(
        app,
        [
            "branch", "close", "kyle/try-alt-loss",
            "--status", "abandoned",
            "--reason", "x",
            "--closed-by", "ghost",
        ],
        catch_exceptions=False,
    )
    assert res.exit_code != 0
    assert "ghost" in res.output


def test_us_a_09_closed_by_required_when_multiple_collaborators(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    _bootstrap(cwd, monkeypatch)
    runner.invoke(app, ["collaborator", "add", "--id", "maria", "--name", "M", "--role", "postdoc"])
    res = runner.invoke(
        app,
        [
            "branch", "close", "kyle/try-alt-loss",
            "--status", "abandoned",
            "--reason", "x",
        ],
        catch_exceptions=False,
    )
    assert res.exit_code != 0
    assert "--closed-by" in res.output


def test_us_a_09_commit_attributed_and_references_branch(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    root, _ = _bootstrap(cwd, monkeypatch)
    runner.invoke(
        app,
        [
            "branch", "close", "kyle/try-alt-loss",
            "--status", "abandoned",
            "--reason", "tried it",
        ],
        catch_exceptions=False,
    )
    head = next(Repo(root).iter_commits())
    assert "kyle/try-alt-loss" in head.message
    assert "abandoned" in head.message
    assert head.author.email == "test@example.com"
