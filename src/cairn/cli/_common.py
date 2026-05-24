"""Shared helpers for CLI subcommands."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import typer

from ..errors import CairnError, NotACairnError
from ..paths import CairnPaths, resolve_cairn


def resolve_or_exit(start: Path | None = None) -> CairnPaths:
    """Resolve the enclosing cairn or exit with a clear message.

    Cairn-marker-only resolution (no ``cairn.toml`` walk).  Most CLI
    commands now use :func:`resolve_target` instead so they honor a
    project repo's ``cairn.toml`` pairing; reach for this helper only
    when ``cairn.toml`` resolution would be wrong (e.g. ``cairn link``
    is itself the command that creates pointers).
    """
    try:
        return resolve_cairn(start)
    except NotACairnError as exc:
        _hint_pointer_if_any(start)
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=2) from None


def _hint_pointer_if_any(start: Path | None) -> None:
    """If a ``cairn.toml`` exists at or above cwd, mention it in the error.

    Helps users distinguish "no pairing configured" from "this command
    doesn't yet honor the pointer" — see finding F-04 in the
    multi-user/multi-cairn test run synthesis.
    """
    from ..cairn_toml import find_pointer

    cwd = (start or Path.cwd()).resolve()
    pointer_path = find_pointer(cwd)
    if pointer_path is not None:
        typer.echo(
            f"note: a cairn.toml pointer exists at {pointer_path} but this "
            f"command does not yet honor it.",
            err=True,
        )


def require_local_target(target: CairnPaths | RemoteTarget, command: str) -> CairnPaths:
    """Return *target* as :class:`CairnPaths`, exiting if it is remote.

    For commands that have no remote-MCP implementation yet (status,
    validate, exploration, etc.), this gives the user a clear error
    instead of silently falling through to a local lookup.
    """
    if isinstance(target, RemoteTarget):
        typer.echo(
            f"error: `cairn {command}` is not supported against a remote-MCP "
            f"cairn yet (this project repo is paired with "
            f"'{target.cairn_name}' at {target.endpoint}).",
            err=True,
        )
        raise typer.Exit(code=1)
    return target


def exit_on(error: CairnError, code: int = 1) -> None:
    typer.echo(f"error: {error}", err=True)
    sys.exit(code)


# ---------------------------------------------------------------------------
# Remote-target support (US-P-13 / ADR-0012)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RemoteTarget:
    """Represents a remote-MCP cairn target resolved from a project-repo cairn.toml."""

    endpoint: str
    cairn_name: str
    token: str | None  # None if not configured (CLI will error on write attempt)


def resolve_target(
    start: Path | None = None,
) -> CairnPaths | RemoteTarget:
    """Resolve the cairn target for a CLI write command.

    Resolution order:
    1. Walk upward from *start* (default: cwd) looking for a ``cairn.toml``
       pointer file in a project repo.
       - local-path mode → resolve the pointed-at filesystem path.
       - local-registry mode → look up the registered cairn.
       - remote-MCP mode → return a ``RemoteTarget``.
    2. If no ``cairn.toml`` found, fall back to ``resolve_cairn()`` (looks
       for a ``.cairn`` marker in the cwd tree).

    Exits with a clear error if resolution fails.
    """
    from ..cairn_toml import CairnTomlError, find_pointer, load_pointer
    from ..registry import RegistryError, lookup

    cwd = (start or Path.cwd()).resolve()
    pointer_path = find_pointer(cwd)

    if pointer_path is not None:
        try:
            pointer = load_pointer(pointer_path)
        except CairnTomlError as exc:
            typer.echo(f"error: {exc}", err=True)
            raise typer.Exit(code=1) from None

        if pointer.is_remote:
            # remote-MCP mode
            assert pointer.endpoint is not None
            assert pointer.name is not None
            from ..credentials import resolve_token
            token = resolve_token(pointer.endpoint)
            return RemoteTarget(
                endpoint=pointer.endpoint,
                cairn_name=pointer.name,
                token=token,
            )

        if pointer.path is not None:
            # local-path mode
            try:
                return resolve_cairn(pointer.path)
            except NotACairnError as exc:
                typer.echo(f"error: {exc}", err=True)
                raise typer.Exit(code=1) from None

        if pointer.name is not None:
            # local-registry mode
            try:
                entry = lookup(pointer.name)
            except RegistryError as exc:
                typer.echo(f"error: registry lookup failed: {exc}", err=True)
                raise typer.Exit(code=1) from None
            if entry is None:
                typer.echo(
                    f"error: cairn '{pointer.name}' is not registered. "
                    f"Add it with `cairn register {pointer.name} <path>`. "
                    f"See `cairn registered`.",
                    err=True,
                )
                raise typer.Exit(code=1) from None
            try:
                return resolve_cairn(entry.path)
            except NotACairnError as exc:
                typer.echo(f"error: {exc}", err=True)
                raise typer.Exit(code=1) from None

    # No cairn.toml found — fall back to local cairn discovery.
    return resolve_or_exit(start)
