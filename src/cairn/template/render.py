"""Template rendering for ``cairn init``.

The bundled default template uses cookiecutter's directory and variable
convention (``{{cookiecutter.foo}}``) so it is compatible with the
cookiecutter ecosystem. The renderer here does the substitution itself
with Jinja2 — there is no runtime dependency on the cookiecutter library
for the local-template path. For URL-based templates (US-P-02), the
``cookiecutter`` extra must be installed; it is imported lazily.
"""

from __future__ import annotations

import importlib.resources
import json
import shutil
from pathlib import Path
from typing import Any

from jinja2 import Environment


def default_template_root() -> Path:
    """Return the path to the bundled default template.

    Resolution order:

    1. ``<cairn-package>/_templates/default/`` — the location used in
       wheels built by hatchling (the ``force-include`` rule in
       pyproject.toml copies the repo's ``templates/`` into the wheel
       under this prefix). This path is the one a ``pip install`` or
       ``pipx install`` user hits.
    2. ``<repo-root>/templates/default/`` — the development-checkout
       layout, where the repo root is three directories above this
       file. Used during editable installs and when running tests.
    """
    try:
        installed = importlib.resources.files("cairn").joinpath("_templates", "default")
        # ``installed`` is a Traversable; we need a real filesystem path. For
        # wheels installed on disk this is always a Path; only zipped installs
        # would differ (we don't ship those).
        installed_path = Path(str(installed))
        if installed_path.is_dir():
            return installed_path
    except (ModuleNotFoundError, AttributeError, OSError):
        pass

    here = Path(__file__).resolve()
    dev_candidate = here.parents[3] / "templates" / "default"
    if dev_candidate.is_dir():
        return dev_candidate

    raise FileNotFoundError(
        "default template not found in either the installed package "
        f"(cairn/_templates/default) or the dev checkout ({dev_candidate}). "
        "If this is a pip/pipx install, the wheel may be missing template "
        "data — reinstall from a recent build."
    )


def _read_cookiecutter_defaults(template_root: Path) -> dict[str, Any]:
    config = template_root / "cookiecutter.json"
    if not config.exists():
        return {}
    return json.loads(config.read_text(encoding="utf-8"))


def _project_subdir(template_root: Path) -> Path:
    for child in template_root.iterdir():
        if child.is_dir() and "{{" in child.name and "cookiecutter" in child.name:
            return child
    raise FileNotFoundError(
        f"no '{{{{cookiecutter.*}}}}' project directory inside {template_root}"
    )


def _render_str(template_str: str, context: dict[str, Any], env: Environment) -> str:
    return env.from_string(template_str).render(cookiecutter=context)


def render_from_path(
    template_root: Path,
    dest_parent: Path,
    context: dict[str, Any],
    *,
    force: bool = False,
) -> Path:
    """Render a local cookiecutter-style template into ``dest_parent``.

    Returns the path of the rendered project directory.
    """
    defaults = _read_cookiecutter_defaults(template_root)
    merged = {**defaults, **{k: v for k, v in context.items() if v is not None}}
    project_template = _project_subdir(template_root)
    env = Environment(keep_trailing_newline=True, autoescape=False)
    project_dir_name = _render_str(project_template.name, merged, env)
    dest = dest_parent / project_dir_name
    if dest.exists():
        if not force:
            raise FileExistsError(f"refusing to overwrite existing path: {dest}")
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    for src in sorted(project_template.rglob("*")):
        rel = src.relative_to(project_template)
        rendered_parts = [_render_str(part, merged, env) for part in rel.parts]
        out_path = dest.joinpath(*rendered_parts)
        if src.is_dir():
            out_path.mkdir(parents=True, exist_ok=True)
            continue
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if src.name == ".gitkeep":
            out_path.write_bytes(b"")
            continue
        try:
            text = src.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            out_path.write_bytes(src.read_bytes())
            continue
        out_path.write_text(_render_str(text, merged, env), encoding="utf-8")

    return dest


def render_from_url(
    url: str,
    dest_parent: Path,
    context: dict[str, Any],
    *,
    no_input: bool = False,
    force: bool = False,
) -> Path:
    """Render a remote cookiecutter template.

    Requires the optional ``cookiecutter`` extra. Imported lazily so the
    base install does not pull it in.
    """
    try:
        from cookiecutter.main import cookiecutter  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "URL-based templates require the cookiecutter extra: "
            "`pip install cairn[cookiecutter]`"
        ) from exc

    out = cookiecutter(
        url,
        no_input=no_input,
        extra_context=context,
        output_dir=str(dest_parent),
        overwrite_if_exists=force,
    )
    return Path(out)
