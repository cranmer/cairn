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
    name: str = typer.Argument(..., help="Short kebab-case name to address the cairn by."),
    path: Path = typer.Argument(
        ...,
        help="Path to the cairn directory.",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
) -> None:
    """Add or update a cairn in the user-level MCP registry."""
    try:
        registry_register(name, path)
    except RegistryError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    typer.echo(f"Registered '{name}' → {path.resolve()} (registry: {registry_path()}).")


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
            f"Add one with: cairn register <name> <path>"
        )
        return
    typer.echo(f"# Registered cairns ({registry_path()})\n")
    name_width = max(len(c.name) for c in cairns)
    for c in cairns:
        typer.echo(f"  {c.name:<{name_width}}  {c.path}")
