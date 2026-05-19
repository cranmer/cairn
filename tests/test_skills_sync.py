"""Tests for `cairn skills sync` — backfilling bundled skills into existing cairns."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from git import Repo
from typer.testing import CliRunner

from cairn.cli.app import app

runner = CliRunner()


def _init_cairn(cwd: Path, monkeypatch: pytest.MonkeyPatch, name: str = "p") -> Path:
    res = runner.invoke(app, ["init", name, "--no-input"], catch_exceptions=False)
    assert res.exit_code == 0, res.output
    root = cwd / name
    monkeypatch.chdir(root)
    return root


def test_sync_adds_missing_skill(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    """Simulate an older cairn: remove `bootstrap_from_repo`, then sync should restore it."""
    root = _init_cairn(cwd, monkeypatch)
    skills = root / "skills"
    boot = skills / "bootstrap_from_repo"
    assert boot.is_dir(), "fresh cairn must ship bootstrap_from_repo"
    # Pretend this is an older cairn — remove the skill from disk.
    shutil.rmtree(boot)
    Repo(root).index.remove(["skills/bootstrap_from_repo"], r=True, working_tree=False)

    res = runner.invoke(app, ["skills", "sync"], catch_exceptions=False)
    assert res.exit_code == 0, res.output
    assert boot.is_dir()
    assert (boot / "SKILL.md").is_file()
    assert "Added:" in res.output
    assert "bootstrap_from_repo" in res.output


def test_sync_skips_existing_skills_by_default(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    """If a skill already exists, sync leaves it alone (no overwrite) unless --force."""
    root = _init_cairn(cwd, monkeypatch)
    # Hand-edit an existing skill so we can verify it's preserved.
    target = root / "skills" / "orient" / "SKILL.md"
    target.write_text("# customized\n", encoding="utf-8")
    res = runner.invoke(app, ["skills", "sync"], catch_exceptions=False)
    assert res.exit_code == 0, res.output
    assert target.read_text(encoding="utf-8") == "# customized\n"


def test_sync_force_overwrites_existing_skills(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    root = _init_cairn(cwd, monkeypatch)
    target = root / "skills" / "orient" / "SKILL.md"
    target.write_text("# customized\n", encoding="utf-8")
    res = runner.invoke(app, ["skills", "sync", "--force"], catch_exceptions=False)
    assert res.exit_code == 0, res.output
    # The bundled orient SKILL.md is restored
    assert "# customized" not in target.read_text(encoding="utf-8")
    assert "Overwritten" in res.output


def test_sync_noop_when_everything_present(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    """A fresh cairn has all bundled skills already — sync should report no-op."""
    _init_cairn(cwd, monkeypatch)
    res = runner.invoke(app, ["skills", "sync"], catch_exceptions=False)
    assert res.exit_code == 0, res.output
    assert "already present" in res.output.lower()


def test_sync_commits_added_skills(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _init_cairn(cwd, monkeypatch)
    boot = root / "skills" / "bootstrap_from_repo"
    shutil.rmtree(boot)
    Repo(root).index.remove(["skills/bootstrap_from_repo"], r=True, working_tree=False)
    repo = Repo(root)
    before = repo.head.commit.hexsha
    res = runner.invoke(app, ["skills", "sync"], catch_exceptions=False)
    assert res.exit_code == 0, res.output
    after = repo.head.commit.hexsha
    assert before != after
    head_msg = repo.head.commit.message
    assert "Sync bundled skills" in head_msg


def test_sync_no_commit_flag(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _init_cairn(cwd, monkeypatch)
    boot = root / "skills" / "bootstrap_from_repo"
    shutil.rmtree(boot)
    Repo(root).index.remove(["skills/bootstrap_from_repo"], r=True, working_tree=False)
    repo = Repo(root)
    before = repo.head.commit.hexsha
    res = runner.invoke(
        app, ["skills", "sync", "--no-commit"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.output
    assert boot.is_dir()  # files restored
    assert repo.head.commit.hexsha == before  # but no new commit
