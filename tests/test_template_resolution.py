"""Regression tests for template resolution.

The packaging bug these guard against: cairn 0.1.0 originally shipped
wheels with no template files at all, and the resolver could only find
templates in a dev-checkout layout. Both editable installs and dev
checkouts kept the suite green while the released wheel was broken.
The tests below exercise the resolver against the installed package's
own data, which is what a `pip`/`pipx` user actually has.
"""

from __future__ import annotations

from pathlib import Path

from cairn.template.render import default_template_root, render_from_path


def test_default_template_root_resolves():
    """The bundled template must be findable from the installed package."""
    root = default_template_root()
    assert root.is_dir(), f"default_template_root() returned non-directory {root}"
    assert (root / "cookiecutter.json").is_file()
    project_subdir = next(
        (c for c in root.iterdir() if c.is_dir() and "cookiecutter" in c.name),
        None,
    )
    assert project_subdir is not None
    assert (project_subdir / "PROJECT.md").is_file()
    assert (project_subdir / "state" / "collaborators.yaml").is_file()


def test_render_against_installed_package(tmp_path: Path):
    """Exercise the full render pipeline using whatever install is active.

    This is the assertion that catches the dev-vs-installed asymmetry: if
    template lookup is broken under a regular install, this test fails the
    same way the user's `cairn init` would.
    """
    out = render_from_path(
        default_template_root(),
        tmp_path,
        context={"project_name": "smoke", "github_org": ""},
    )
    assert (out / "PROJECT.md").is_file()
    assert (out / "state").is_dir()
    assert (out / "state" / "collaborators.yaml").is_file()
    assert (out / "skills" / "orient" / "SKILL.md").is_file()
    assert (out / ".claude" / "settings.json").is_file()
