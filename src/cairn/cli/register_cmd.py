"""`cairn register / unregister / registered` — manage the MCP server's cairn registry.

The registry maps short cairn names to filesystem paths, used as MCP API
parameters. Lives at ``~/.config/cairn/server.toml`` (or under
``$XDG_CONFIG_HOME``). See ADR-0010.
"""

from __future__ import annotations

from pathlib import Path

import typer

from ..registry import (
    RegistryError,
    load_registry,
    registry_path,
)
from ..registry import (
    register as registry_register,
)
from ..registry import (
    unregister as registry_unregister,
)


def register(
    name: str = typer.Argument(
        ...,
        help=(
            "Short handle you choose for this cairn. This is the name MCP "
            "tools will accept as their `cairn` parameter (e.g., "
            "`add_decision(cairn=\"<name>\", ...)`). It does NOT need to "
            "match the cairn's directory name or any internal identifier — "
            "pick something short. Kebab-case, lowercase, max 31 chars."
        ),
    ),
    path: Path = typer.Argument(
        ...,
        help="Path to the cairn directory. With --init, the cairn is created here if missing.",
    ),
    init: bool = typer.Option(
        False,
        "--init",
        help=(
            "Create a new cairn at <path> first if no cairn exists there, then "
            "register it. Equivalent to `cairn init <basename> && cairn register`. "
            "Without this flag, --path must already be a cairn root."
        ),
    ),
) -> None:
    """Add or update a cairn in the user-level MCP registry."""
    resolved = path.expanduser().resolve()

    if not resolved.exists():
        if not init:
            typer.echo(
                f"error: {resolved} does not exist. "
                f"If you meant to create a new cairn there, re-run with --init "
                f"(or run `cairn init {resolved.name}` from {resolved.parent} first).",
                err=True,
            )
            raise typer.Exit(code=1)
        # --init: scaffold a new cairn at this path before registering.
        _init_cairn_at(resolved)

    if not resolved.is_dir():
        typer.echo(f"error: {resolved} is not a directory", err=True)
        raise typer.Exit(code=1)

    from ..paths import is_cairn_root

    if not is_cairn_root(resolved):
        if not init:
            typer.echo(
                f"error: {resolved} is not a cairn root. "
                f"If you want to scaffold a new cairn here, re-run with --init.",
                err=True,
            )
            raise typer.Exit(code=1)
        # Directory exists but isn't a cairn — scaffold (will create files inside).
        _init_cairn_at(resolved)

    try:
        registry_register(name, resolved)
    except RegistryError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    typer.echo(f"Registered '{name}' → {resolved} (registry: {registry_path()}).")
    typer.echo(
        "\nIf you haven't yet, register the cairn MCP server with Claude Code "
        "(one-time, ever — same command regardless of how many cairns you have):\n"
        "  claude mcp add cairn cairn mcp\n"
        "Then restart any open Claude Code sessions to pick it up."
    )


def _init_cairn_at(path: Path) -> None:
    """Scaffold a new cairn at ``path`` by invoking the init command in-process."""
    parent = path.parent
    project_name = path.name
    parent.mkdir(parents=True, exist_ok=True)

    # Run init from the parent so it creates ./<project_name>.
    import os

    from .init_cmd import init as init_command

    saved = os.getcwd()
    try:
        os.chdir(parent)
        # Typer expects to be invoked through the CLI runner; calling the
        # function directly with Argument defaults is awkward. Use the runner
        # for a single command invocation.
        from typer.testing import CliRunner

        from .app import app

        result = CliRunner().invoke(
            app, ["init", project_name, "--no-input"], catch_exceptions=False
        )
        if result.exit_code != 0:
            typer.echo(result.output, err=True)
            typer.echo(
                f"error: `cairn init {project_name}` failed (exit {result.exit_code})",
                err=True,
            )
            raise typer.Exit(code=1)
        typer.echo(result.output.strip())
    finally:
        os.chdir(saved)

    # Silence linter for the unused import (kept for parity).
    _ = init_command


def unregister(
    name: str = typer.Argument(..., help="Cairn name to remove from the registry."),
) -> None:
    """Remove a cairn from the user-level MCP registry."""
    try:
        removed = registry_unregister(name)
    except RegistryError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    if not removed:
        typer.echo(f"No cairn named '{name}' in the registry.")
        raise typer.Exit(code=1)
    typer.echo(f"Unregistered '{name}'.")


def registered() -> None:
    """List currently registered cairns."""
    cairns = load_registry()
    if not cairns:
        typer.echo(
            f"No cairns registered (registry: {registry_path()}).\n"
            f"Add one with: cairn register <name> <path>\n"
            f"  or:        cairn register <name> <path> --init   (scaffold + register in one step)"
        )
        return
    typer.echo(f"# Registered cairns ({registry_path()})\n")
    name_width = max(len(c.name) for c in cairns)
    for c in cairns:
        typer.echo(f"  {c.name:<{name_width}}  {c.path}")
