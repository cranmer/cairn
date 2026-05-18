"""`cairn init` — scaffold a new cairn from a template."""

from __future__ import annotations

from pathlib import Path

import typer

from ..errors import CairnError
from ..git_ops import commit, get_user_identity, init_repo
from ..paths import REQUIRED_DIRS, STATE_FILES, CairnPaths
from ..template import default_template_root, render_from_path, render_from_url


def _validate_rendered(root: Path) -> None:
    """Confirm every required directory and state file exists after render."""
    for d in REQUIRED_DIRS:
        if not (root / d).is_dir():
            raise CairnError(f"template rendered without required directory: {d}")
    for f in STATE_FILES:
        if not (root / "state" / f).is_file():
            raise CairnError(f"template rendered without required state file: state/{f}")
    if not (root / "PROJECT.md").is_file():
        raise CairnError("template rendered without PROJECT.md")


def init(
    project_name: str = typer.Argument(..., help="Name of the new cairn (and its directory)."),
    template: str | None = typer.Option(
        None,
        "--template",
        help="Local path or cookiecutter URL. Defaults to Cairn's bundled template.",
    ),
    github_org: str | None = typer.Option(None, "--github-org", help="GitHub org (optional)."),
    force: bool = typer.Option(
        False, "--force", help="Overwrite an existing directory at the destination."
    ),
    no_input: bool = typer.Option(
        False, "--no-input", help="Run non-interactively; required for CI."
    ),
) -> None:
    """Initialize a new cairn at ``./<project_name>``."""
    dest_parent = Path.cwd()
    context = {"project_name": project_name, "github_org": github_org}

    try:
        identity = get_user_identity(None)
    except CairnError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=2) from None

    try:
        if template and (template.startswith("http://") or template.startswith("https://")
                         or template.startswith("git@") or template.endswith(".git")):
            rendered = render_from_url(
                template, dest_parent, context, no_input=no_input, force=force
            )
        elif template:
            rendered = render_from_path(Path(template), dest_parent, context, force=force)
        else:
            rendered = render_from_path(default_template_root(), dest_parent, context, force=force)
    except FileExistsError as exc:
        typer.echo(f"error: {exc} (pass --force to overwrite)", err=True)
        raise typer.Exit(code=1) from None
    except (CairnError, RuntimeError, FileNotFoundError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None

    try:
        _validate_rendered(rendered)
    except CairnError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None

    repo = init_repo(rendered)
    # Exclude anything inside the new .git/ directory (created by init_repo above).
    all_files = [
        p for p in rendered.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(rendered).parts
    ]
    commit(
        repo,
        all_files,
        message=f"Initial commit: scaffold cairn '{project_name}'",
        author=identity,
    )

    paths = CairnPaths(root=rendered)
    typer.echo(f"Initialized cairn at {paths.root}")
