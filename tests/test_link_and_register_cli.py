"""CLI tests for `cairn link` and `cairn register --init` (PR #15 follow-up).

These exercise the UX flows that came out of the first round of real
testing: linking from outside the cairn via ``--name``, register's
``--init`` shortcut, and the better error when register's path is
missing.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cairn.cli.app import app

runner = CliRunner()


@pytest.fixture
def isolated_xdg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return tmp_path


def test_register_init_scaffolds_and_registers(
    isolated_xdg: Path, monkeypatch: pytest.MonkeyPatch
):
    """`cairn register foo /path --init` creates the cairn + registers it."""
    target = isolated_xdg / "fresh-cairn"
    monkeypatch.chdir(isolated_xdg)
    res = runner.invoke(
        app, ["register", "fresh", str(target), "--init"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.output
    assert (target / ".cairn").is_file(), "cairn marker should exist after --init"
    assert (target / "PROJECT.md").is_file()

    # And it's registered
    listed = runner.invoke(app, ["registered"], catch_exceptions=False)
    assert "fresh" in listed.output
    assert str(target) in listed.output


def test_register_without_init_errors_on_missing_path(
    isolated_xdg: Path, monkeypatch: pytest.MonkeyPatch
):
    """Without --init, register refuses a nonexistent path with actionable error."""
    monkeypatch.chdir(isolated_xdg)
    res = runner.invoke(
        app, ["register", "ghost", str(isolated_xdg / "nope")], catch_exceptions=False
    )
    assert res.exit_code != 0
    assert "does not exist" in res.output.lower()
    assert "--init" in res.output


def test_register_without_init_errors_on_non_cairn_dir(
    isolated_xdg: Path, monkeypatch: pytest.MonkeyPatch
):
    """A pre-existing directory that isn't a cairn should error with the --init hint."""
    plain = isolated_xdg / "plain"
    plain.mkdir()
    monkeypatch.chdir(isolated_xdg)
    res = runner.invoke(
        app, ["register", "ghost", str(plain)], catch_exceptions=False
    )
    assert res.exit_code != 0
    assert "not a cairn root" in res.output.lower()
    assert "--init" in res.output


def test_link_with_name_works_outside_cairn(
    isolated_xdg: Path, monkeypatch: pytest.MonkeyPatch
):
    """`cairn link <project> --name <handle>` works from anywhere, not just inside the cairn."""
    cairn_dir = isolated_xdg / "demo-cairn"
    monkeypatch.chdir(isolated_xdg)
    runner.invoke(
        app, ["register", "demo", str(cairn_dir), "--init"], catch_exceptions=False
    )
    project = isolated_xdg / "my-project"
    project.mkdir()
    # Run link from a third directory — neither the cairn nor the project
    third = isolated_xdg / "elsewhere"
    third.mkdir()
    monkeypatch.chdir(third)
    res = runner.invoke(
        app, ["link", str(project), "--name", "demo"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.output
    pointer = project / "cairn.toml"
    assert pointer.is_file()
    assert 'name = "demo"' in pointer.read_text()


def test_link_default_project_repo_is_cwd(
    isolated_xdg: Path, monkeypatch: pytest.MonkeyPatch
):
    """Running `cairn link --name <handle>` from inside a project repo links cwd."""
    cairn_dir = isolated_xdg / "demo-cairn"
    monkeypatch.chdir(isolated_xdg)
    runner.invoke(
        app, ["register", "demo", str(cairn_dir), "--init"], catch_exceptions=False
    )
    project = isolated_xdg / "my-project"
    project.mkdir()
    monkeypatch.chdir(project)
    res = runner.invoke(
        app, ["link", "--name", "demo"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.output
    assert (project / "cairn.toml").is_file()


def test_link_with_unregistered_name_errors_clearly(
    isolated_xdg: Path, monkeypatch: pytest.MonkeyPatch
):
    """`--name` referring to a handle not in the registry errors with guidance."""
    project = isolated_xdg / "my-project"
    project.mkdir()
    monkeypatch.chdir(isolated_xdg)
    res = runner.invoke(
        app, ["link", str(project), "--name", "ghost"], catch_exceptions=False
    )
    assert res.exit_code != 0
    assert "not registered" in res.output.lower()
    assert "cairn register" in res.output


def test_init_emits_next_steps_message(
    isolated_xdg: Path, monkeypatch: pytest.MonkeyPatch
):
    """`cairn init` ends with a discoverable Next steps: hint."""
    monkeypatch.chdir(isolated_xdg)
    res = runner.invoke(
        app, ["init", "step-test", "--no-input"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.output
    assert "Next steps:" in res.output
    assert "cairn collaborator add" in res.output
    assert "cairn register" in res.output
    assert "cairn link" in res.output
    assert "claude mcp add cairn cairn mcp" in res.output


def test_register_reminds_to_wire_up_mcp(
    isolated_xdg: Path, monkeypatch: pytest.MonkeyPatch
):
    """`cairn register` reminds the user to add the MCP server to Claude Code."""
    target = isolated_xdg / "fresh"
    monkeypatch.chdir(isolated_xdg)
    res = runner.invoke(
        app, ["register", "fresh", str(target), "--init"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.output
    assert "claude mcp add cairn cairn mcp" in res.output


def test_orient_prints_project_md_and_status(
    isolated_xdg: Path, monkeypatch: pytest.MonkeyPatch
):
    """`cairn orient` shows PROJECT.md content and the status block."""
    monkeypatch.chdir(isolated_xdg)
    runner.invoke(app, ["init", "ori", "--no-input"], catch_exceptions=False)
    monkeypatch.chdir(isolated_xdg / "ori")
    runner.invoke(
        app, ["collaborator", "add", "--id", "kyle", "--name", "K", "--role", "PI"]
    )
    res = runner.invoke(app, ["orient"], catch_exceptions=False)
    assert res.exit_code == 0, res.output
    # PROJECT.md content (starts with a markdown header in the bundled template)
    assert "#" in res.output
    # Status content
    assert "Collaborators:" in res.output
    # Separator between the two
    assert "-" * 20 in res.output


def test_link_reminds_to_wire_up_mcp(
    isolated_xdg: Path, monkeypatch: pytest.MonkeyPatch
):
    """`cairn link --name ...` reminds the user to add the MCP server to Claude Code."""
    cairn_dir = isolated_xdg / "demo-cairn"
    monkeypatch.chdir(isolated_xdg)
    runner.invoke(
        app, ["register", "demo", str(cairn_dir), "--init"], catch_exceptions=False
    )
    project = isolated_xdg / "my-project"
    project.mkdir()
    monkeypatch.chdir(project)
    res = runner.invoke(
        app, ["link", "--name", "demo"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.output
    assert "claude mcp add cairn cairn mcp" in res.output
