"""US-P-02 — Initialize from a template."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from cairn.cli.app import app

runner = CliRunner()


def _make_minimal_template(tmp_path: Path) -> Path:
    """Build a tiny cookiecutter-style template under ``tmp_path``."""
    root = tmp_path / "alt-template"
    root.mkdir()
    (root / "cookiecutter.json").write_text(
        '{"project_name": "alt", "pi_name": "TODO", "github_org": ""}\n'
    )
    proj = root / "{{cookiecutter.project_name}}"
    proj.mkdir()
    (proj / "PROJECT.md").write_text(
        "# {{cookiecutter.project_name}} (alt template)\n\nPI: {{cookiecutter.pi_name}}\n"
    )
    (proj / "README.md").write_text("alt readme\n")
    (proj / ".gitignore").write_text("/scratch/\n")
    for d in ("state", "knowledge/meetings", "knowledge/findings",
              "knowledge/literature", "knowledge/provenance",
              "skills", "branches"):
        (proj / d).mkdir(parents=True)
    for f in ("decisions", "open_questions", "action_items", "goals", "collaborators"):
        (proj / "state" / f"{f}.yaml").write_text("[]\n")
    return root


def test_us_p_02_local_path_template(cwd: Path, tmp_path_factory):
    template_root = _make_minimal_template(tmp_path_factory.mktemp("tpl"))
    result = runner.invoke(
        app,
        [
            "init", "from-alt-template",
            "--template", str(template_root),
            "--pi-name", "Dr. Test",
            "--no-input",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    text = (cwd / "from-alt-template" / "PROJECT.md").read_text()
    assert "# from-alt-template (alt template)" in text
    assert "Dr. Test" in text


def test_us_p_02_defaults_to_bundled_template(cwd: Path):
    """No --template flag means the bundled default is used."""
    result = runner.invoke(
        app,
        ["init", "default-tpl-test", "--pi-name", "Default", "--no-input"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    # The bundled PROJECT.md mentions "Agent orientation file."
    text = (cwd / "default-tpl-test" / "PROJECT.md").read_text()
    assert "Agent orientation file" in text


def test_us_p_02_url_template_without_extra_errors_helpfully(cwd: Path, monkeypatch):
    """If cookiecutter isn't installed, --template <url> says so clearly."""
    import sys
    # Force ImportError on `from cookiecutter.main import cookiecutter`.
    monkeypatch.setitem(sys.modules, "cookiecutter", None)
    monkeypatch.setitem(sys.modules, "cookiecutter.main", None)
    result = runner.invoke(
        app,
        [
            "init", "ignored",
            "--template", "https://github.com/example/template",
            "--pi-name", "X",
            "--no-input",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "cookiecutter" in result.output.lower()
