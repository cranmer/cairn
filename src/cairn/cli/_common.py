"""Shared helpers for CLI subcommands."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import typer

from ..errors import CairnError, NotACairnError
from ..paths import CairnPaths, resolve_cairn


def resolve_or_exit(start: Path | None = None) -> CairnPaths:
    """Resolve the enclosing cairn or exit with a clear message."""
    try:
        return resolve_cairn(start)
    except NotACairnError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=2) from None


def exit_on(error: CairnError, code: int = 1) -> None:
    typer.echo(f"error: {error}", err=True)
    sys.exit(code)


@dataclass(frozen=True)
class RemoteTarget:
    """A cairn reachable via a remote HTTP MCP server."""

    endpoint: str
    cairn_name: str


def resolve_or_exit_with_remote(start: Path | None = None) -> CairnPaths | RemoteTarget:
    """Resolve the enclosing cairn, or a remote target from cairn.toml.

    Resolution order (per ADR-0006):
    1. Walk upward looking for a ``.cairn`` marker → local cairn.
    2. Walk upward looking for a ``cairn.toml`` pointer:
       - remote mode (endpoint + name) → RemoteTarget
       - local-path mode → CairnPaths(root=path)
       - local-registry mode → CairnPaths(root=registry lookup path)
    3. Raise typer.Exit(2) with a helpful message.
    """
    # 1. Look for a local cairn root.
    try:
        return resolve_cairn(start)
    except NotACairnError:
        pass

    # 2. Look for a cairn.toml pointer.
    from ..cairn_toml import CairnTomlError, find_pointer, load_pointer

    pointer_path = find_pointer(start or Path.cwd())
    if pointer_path is not None:
        try:
            pointer = load_pointer(pointer_path)
        except CairnTomlError as exc:
            typer.echo(f"error: invalid cairn.toml: {exc}", err=True)
            raise typer.Exit(code=1) from None

        if pointer.is_remote:
            assert pointer.endpoint is not None and pointer.name is not None
            return RemoteTarget(endpoint=pointer.endpoint, cairn_name=pointer.name)

        if pointer.path is not None:
            return CairnPaths(root=pointer.path)

        # Local-registry mode: look up the name in the user registry.
        if pointer.name is not None:
            from ..registry import lookup

            registered = lookup(pointer.name)
            if registered is None:
                typer.echo(
                    f"error: cairn.toml references registered cairn '{pointer.name}' "
                    f"but it is not in the local registry. "
                    f"Run `cairn register {pointer.name} <path>` to add it.",
                    err=True,
                )
                raise typer.Exit(code=1) from None
            return CairnPaths(root=registered.path)

    # 3. Nothing found.
    typer.echo(
        "error: no cairn found. Run from inside a cairn, or from a project repo "
        "with a cairn.toml pointer. See `cairn link`.",
        err=True,
    )
    raise typer.Exit(code=2) from None
