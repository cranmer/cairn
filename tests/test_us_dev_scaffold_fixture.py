"""Tests for `cairn dev scaffold-fixture`."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from cairn.cli.app import app


@pytest.mark.parametrize(
    "fixture_name,expected_collaborators",
    [
        ("coral-bleach", ["kyle", "lila"]),
        ("lit-monitor", ["kyle", "priya"]),
    ],
)
def test_scaffold_fixture_local_pairing(
    fixture_name: str,
    expected_collaborators: list[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Local-pairing fixtures (scenarios 1.A / 1.B) should produce a
    project dir + paired cairn with the right collaborators and a
    ``name = ...`` cairn.toml."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["dev", "scaffold-fixture", fixture_name, "--dest", str(tmp_path / "run")],
    )
    assert result.exit_code == 0, result.output

    project_dir = tmp_path / "run" / "projects" / fixture_name
    cairn_dir = tmp_path / "run" / "cairns" / fixture_name
    assert project_dir.is_dir()
    assert cairn_dir.is_dir()

    # cairn.toml — local pairing has `name`, no `endpoint`.
    toml_text = (project_dir / "cairn.toml").read_text()
    assert f'name = "{fixture_name}"' in toml_text
    assert "endpoint" not in toml_text

    # Collaborators seeded.
    collaborators_yaml = yaml.safe_load(
        (cairn_dir / "state" / "collaborators.yaml").read_text()
    )
    actual_ids = sorted(c["id"] for c in collaborators_yaml)
    assert actual_ids == sorted(expected_collaborators)

    # At least one decision and one open question.
    decisions = yaml.safe_load((cairn_dir / "state" / "decisions.yaml").read_text())
    assert len(decisions) >= 1
    questions = yaml.safe_load(
        (cairn_dir / "state" / "open_questions.yaml").read_text()
    )
    assert len(questions) >= 1


def test_scaffold_fixture_http_pairing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """shared-physics-paper uses HTTP pairing — cairn.toml must include endpoint."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))

    runner = CliRunner()
    endpoint = "http://127.0.0.1:9999"
    result = runner.invoke(
        app,
        [
            "dev", "scaffold-fixture", "shared-physics-paper",
            "--dest", str(tmp_path / "run"),
            "--http-endpoint", endpoint,
        ],
    )
    assert result.exit_code == 0, result.output

    project_dir = tmp_path / "run" / "projects" / "shared-physics-paper"
    toml_text = (project_dir / "cairn.toml").read_text()
    assert f'endpoint = "{endpoint}"' in toml_text
    assert 'name = "shared-physics-paper"' in toml_text


def test_scaffold_fixture_http_pairing_requires_endpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without --http-endpoint, the http fixture should error clearly."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["dev", "scaffold-fixture", "shared-physics-paper", "--dest", str(tmp_path / "run")],
    )
    assert result.exit_code != 0
    assert "endpoint" in result.output.lower()


def test_scaffold_fixture_unknown_name_errors_clearly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    runner = CliRunner()
    result = runner.invoke(
        app, ["dev", "scaffold-fixture", "ghost-fixture", "--dest", str(tmp_path / "run")]
    )
    assert result.exit_code != 0
    assert "ghost-fixture" in result.output
    assert (
        "coral-bleach" in result.output
        and "lit-monitor" in result.output
        and "shared-physics-paper" in result.output
    ), "error should list the known fixtures"
