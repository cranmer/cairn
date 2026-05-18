"""US-P-03 — Add a collaborator."""

from __future__ import annotations

from pathlib import Path

import pytest
from git import Repo
from typer.testing import CliRunner

from cairn.cli.app import app
from cairn.io.state_io import load_collaborators
from cairn.paths import CairnPaths

runner = CliRunner()


def _init(cwd: Path, monkeypatch: pytest.MonkeyPatch, name: str = "p") -> Path:
    res = runner.invoke(
        app, ["init", name, "--no-input"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.output
    root = cwd / name
    monkeypatch.chdir(root)
    return root


def test_us_p_03_add_creates_entry(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _init(cwd, monkeypatch)
    res = runner.invoke(
        app,
        ["collaborator", "add", "--id", "maria", "--name", "Maria Santos", "--role", "postdoc"],
        catch_exceptions=False,
    )
    assert res.exit_code == 0, res.output
    collabs = load_collaborators(CairnPaths(root=root))
    assert len(collabs) == 1
    assert collabs[0].id == "maria"
    assert collabs[0].name == "Maria Santos"
    assert collabs[0].role == "postdoc"


def test_us_p_03_add_accepts_email(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    """The orient skill matches the current git user against collaborator
    email; the CLI must accept --email and the schema must round-trip it."""
    root = _init(cwd, monkeypatch)
    res = runner.invoke(
        app,
        [
            "collaborator", "add",
            "--id", "maria",
            "--name", "Maria Santos",
            "--role", "postdoc",
            "--email", "maria@example.com",
            "--github", "maria-s",
        ],
        catch_exceptions=False,
    )
    assert res.exit_code == 0, res.output
    collabs = load_collaborators(CairnPaths(root=root))
    assert collabs[0].email == "maria@example.com"
    assert collabs[0].github == "maria-s"


def test_us_p_03_id_must_be_unique(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    _init(cwd, monkeypatch)
    runner.invoke(
        app, ["collaborator", "add", "--id", "maria", "--name", "M", "--role", "postdoc"]
    )
    res = runner.invoke(
        app,
        ["collaborator", "add", "--id", "maria", "--name", "Other", "--role", "PI"],
        catch_exceptions=False,
    )
    assert res.exit_code != 0
    assert "already in use" in res.output.lower()


def test_us_p_03_required_fields_enforced(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    _init(cwd, monkeypatch)
    res = runner.invoke(app, ["collaborator", "add", "--id", "maria"], catch_exceptions=False)
    assert res.exit_code != 0


def test_us_p_03_optional_fields_accepted(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _init(cwd, monkeypatch)
    res = runner.invoke(
        app,
        [
            "collaborator", "add",
            "--id", "kyle",
            "--name", "Kyle Cranmer",
            "--role", "PI",
            "--github", "cranmer",
            "--expertise", "stats",
            "--expertise", "physics",
            "--notes", "Lab head",
        ],
        catch_exceptions=False,
    )
    assert res.exit_code == 0, res.output
    c = load_collaborators(CairnPaths(root=root))[0]
    assert c.github == "cranmer"
    assert c.expertise == ["stats", "physics"]
    assert c.notes == "Lab head"


def test_us_p_03_bulk_yaml_file(
    cwd: Path, monkeypatch: pytest.MonkeyPatch, tmp_path_factory
):
    root = _init(cwd, monkeypatch)
    bulk = tmp_path_factory.mktemp("bulk") / "team.yaml"
    bulk.write_text(
        "- id: maria\n"
        "  name: Maria Santos\n"
        "  role: postdoc\n"
        "- id: lit-monitor\n"
        "  name: Literature Monitor\n"
        "  role: literature monitor\n"
        "  type: ai-collaborator\n"
        "  trigger: weekly\n"
    )
    res = runner.invoke(
        app, ["collaborator", "add", "--yaml", str(bulk)], catch_exceptions=False
    )
    assert res.exit_code == 0, res.output
    collabs = load_collaborators(CairnPaths(root=root))
    assert {c.id for c in collabs} == {"maria", "lit-monitor"}
    ai = next(c for c in collabs if c.id == "lit-monitor")
    assert ai.type == "ai-collaborator"
    assert ai.trigger == "weekly"


def test_us_p_03_commit_attributed(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _init(cwd, monkeypatch)
    runner.invoke(
        app, ["collaborator", "add", "--id", "maria", "--name", "M", "--role", "postdoc"]
    )
    repo = Repo(root)
    head = next(repo.iter_commits())
    assert "maria" in head.message
    assert head.author.email == "test@example.com"
