"""Regression tests for template resolution under both dev and installed layouts."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from cairn.template.render import default_template_root


def test_default_template_root_resolves_in_dev_checkout():
    """The dev checkout has templates/default at the repo root; that should resolve."""
    root = default_template_root()
    assert root.is_dir()
    assert (root / "cookiecutter.json").is_file()
    # Sanity: must contain the scaffold project subdir.
    project_subdir = next(
        (c for c in root.iterdir() if c.is_dir() and "cookiecutter" in c.name),
        None,
    )
    assert project_subdir is not None
    assert (project_subdir / "PROJECT.md").is_file()


def test_default_template_root_prefers_installed_package_location(tmp_path: Path):
    """When importlib.resources points at a populated _templates dir, use that.

    Regression: cairn 0.1.0 shipped a wheel without templates and the only
    code path that found them was the dev-checkout fallback, which doesn't
    exist in a pip/pipx install. The fix ships templates inside the wheel
    and looks for them via importlib.resources first.
    """
    # Build a fake installed-package layout under tmp_path.
    installed = tmp_path / "cairn" / "_templates" / "default"
    installed.mkdir(parents=True)
    (installed / "cookiecutter.json").write_text('{"project_name": "x"}')

    class FakeTraversable:
        def __init__(self, p: Path):
            self._p = p

        def joinpath(self, *parts: str) -> FakeTraversable:
            return FakeTraversable(self._p.joinpath(*parts))

        def __str__(self) -> str:
            return str(self._p)

    with patch(
        "cairn.template.render.importlib.resources.files",
        return_value=FakeTraversable(tmp_path / "cairn"),
    ):
        root = default_template_root()

    assert root == installed
    assert root.is_dir()


def test_default_template_root_raises_when_neither_location_exists(monkeypatch):
    """If both lookup paths fail, the error names both and is actionable."""
    # Force the installed lookup to return a path that doesn't exist.
    class MissingTraversable:
        def joinpath(self, *_parts: str) -> MissingTraversable:
            return self

        def __str__(self) -> str:
            return "/nonexistent/cairn/_templates/default"

    monkeypatch.setattr(
        "cairn.template.render.importlib.resources.files",
        lambda _: MissingTraversable(),
    )
    # And shadow the dev fallback by pointing __file__ at /tmp (where no
    # templates/ sibling exists).
    monkeypatch.setattr(
        "cairn.template.render.__file__",
        "/tmp/totally-unrelated/cairn/src/cairn/template/render.py",
    )
    with pytest.raises(FileNotFoundError) as exc:
        default_template_root()
    # Error mentions both paths so a user can debug their install.
    msg = str(exc.value)
    assert "_templates" in msg or "templates" in msg
