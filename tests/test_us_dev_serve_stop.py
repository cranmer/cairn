"""Tests for the `cairn dev` subgroup (serve, stop, scaffold-fixture)."""

from __future__ import annotations

from typer.testing import CliRunner

from cairn.cli.app import app


def test_dev_subgroup_help_lists_three_commands() -> None:
    """`cairn dev --help` should list serve, stop, and scaffold-fixture."""
    runner = CliRunner()
    result = runner.invoke(app, ["dev", "--help"])
    assert result.exit_code == 0, result.output
    assert "serve" in result.output
    assert "stop" in result.output
    assert "scaffold-fixture" in result.output
