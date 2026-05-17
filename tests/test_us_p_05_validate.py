"""US-P-05 — Validate a cairn."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from cairn.cli.app import app

runner = CliRunner()


def _bootstrap(cwd: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    runner.invoke(app, ["init", "p", "--pi-name", "PI", "--no-input"], catch_exceptions=False)
    root = cwd / "p"
    monkeypatch.chdir(root)
    runner.invoke(
        app, ["collaborator", "add", "--id", "kyle", "--name", "K", "--role", "PI"]
    )
    return root


def test_us_p_05_fresh_cairn_passes(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    _bootstrap(cwd, monkeypatch)
    res = runner.invoke(app, ["validate"], catch_exceptions=False)
    assert res.exit_code == 0
    assert "OK" in res.output


def test_us_p_05_missing_required_directory(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _bootstrap(cwd, monkeypatch)
    shutil.rmtree(root / "knowledge" / "findings")
    res = runner.invoke(app, ["validate"], catch_exceptions=False)
    assert res.exit_code != 0
    assert "knowledge/findings" in res.output


def test_us_p_05_yaml_parse_error(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _bootstrap(cwd, monkeypatch)
    (root / "state" / "decisions.yaml").write_text(
        "- id: D-001\n  date: 2026-05-01T00:00:00Z\n   bad-indent: x\n"
    )
    res = runner.invoke(app, ["validate"], catch_exceptions=False)
    assert res.exit_code != 0


def test_us_p_05_schema_violation(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _bootstrap(cwd, monkeypatch)
    bad = [{"id": "D-001", "date": "2026-05-01T00:00:00Z", "author": "kyle"}]  # missing "decision"
    (root / "state" / "decisions.yaml").write_text(yaml.safe_dump(bad))
    res = runner.invoke(app, ["validate"], catch_exceptions=False)
    assert res.exit_code != 0
    assert "D-001" in res.output


def test_us_p_05_dangling_related_reference(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _bootstrap(cwd, monkeypatch)
    runner.invoke(app, ["decision", "add", "--author", "kyle", "--text", "x"])
    raw = yaml.safe_load((root / "state" / "decisions.yaml").read_text())
    raw[0]["related"] = ["Q-999"]
    (root / "state" / "decisions.yaml").write_text(yaml.safe_dump(raw))
    res = runner.invoke(app, ["validate"], catch_exceptions=False)
    assert res.exit_code != 0
    assert "Q-999" in res.output
    assert "D-001" in res.output


def test_us_p_05_unknown_author(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _bootstrap(cwd, monkeypatch)
    bad = [
        {
            "id": "D-001",
            "date": "2026-05-01T00:00:00Z",
            "author": "ghost",
            "decision": "x",
        }
    ]
    (root / "state" / "decisions.yaml").write_text(yaml.safe_dump(bad))
    res = runner.invoke(app, ["validate"], catch_exceptions=False)
    assert res.exit_code != 0
    assert "ghost" in res.output


def test_us_p_05_meeting_filename_convention(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _bootstrap(cwd, monkeypatch)
    (root / "knowledge" / "meetings" / "notes.md").write_text("# bad name\n")
    res = runner.invoke(app, ["validate"], catch_exceptions=False)
    assert res.exit_code != 0
    assert "YYYY-MM-DD" in res.output


def test_us_p_05_strict_flag_surfaces_warnings(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _bootstrap(cwd, monkeypatch)
    # An orphan open question, status=open with no related and not referenced.
    q = [
        {
            "id": "Q-001",
            "raised_by": "kyle",
            "date": "2026-05-01T00:00:00Z",
            "question": "is anything related to this?",
        }
    ]
    (root / "state" / "open_questions.yaml").write_text(yaml.safe_dump(q))
    res_loose = runner.invoke(app, ["validate"], catch_exceptions=False)
    assert res_loose.exit_code == 0  # warning only, not error
    res_strict = runner.invoke(app, ["validate", "--strict"], catch_exceptions=False)
    # Strict mode adds a warning but exit code stays 0 (warnings don't fail);
    # we just check the warning text appeared.
    assert "orphan" in res_strict.output.lower()
