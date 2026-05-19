"""`cairn mcp` — run the MCP server over stdio.

See ADR-0009 and ADR-0010. Requires the ``[mcp]`` install extra.
"""

from __future__ import annotations

from pathlib import Path

import typer


def mcp(
    cairn_path: Path | None = typer.Option(
        None,
        "--cairn-path",
        help=(
            "Convenience: register a single ad-hoc cairn at this path (in addition "
            "to any cairns in the user-level registry) before starting the server. "
            "The name defaults to the directory basename. Useful for one-off runs "
            "and CI; for normal use, register cairns with `cairn register`."
        ),
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    name: str | None = typer.Option(
        None,
        "--name",
        help=(
            "Name to use for the ad-hoc cairn registered via --cairn-path. "
            "Defaults to the directory basename (minus a `-cairn` suffix)."
        ),
    ),
) -> None:
    """Run the MCP server over stdio (Tier-1 tools)."""
    try:
        from ..mcp.server import run
    except ImportError as exc:
        typer.echo(
            f"error: MCP server requires the [mcp] extra. "
            f"Install with: pip install 'cairn[mcp]'\n"
            f"(import error: {exc})",
            err=True,
        )
        raise typer.Exit(code=1) from None

    if cairn_path is not None:
        # Register the ad-hoc cairn in-process (not persisted to disk).
        from ..mcp import server as server_module
        from ..registry import (
            RegisteredCairn,
            RegistryError,
            load_registry,
            validate_name,
        )

        resolved = cairn_path.expanduser().resolve()
        ad_hoc_name = name or _default_name_for(resolved)
        try:
            validate_name(ad_hoc_name)
        except RegistryError as exc:
            typer.echo(f"error: {exc}", err=True)
            raise typer.Exit(code=1) from None

        persisted = load_registry()
        ad_hoc = RegisteredCairn(name=ad_hoc_name, path=resolved)
        combined = [*persisted, ad_hoc]

        # Patch load_registry so build_server sees the combined list.
        def patched_load_registry(*args, **kwargs):  # type: ignore[no-untyped-def]
            return combined

        # The server captured the symbol from cairn.registry at import time —
        # patch it there so tools see the ad-hoc entry too.
        import cairn.registry as registry_mod

        server_module.load_registry = patched_load_registry  # type: ignore[assignment]
        registry_mod.load_registry = patched_load_registry  # type: ignore[assignment]

    run()


def _default_name_for(path: Path) -> str:
    """Derive a default cairn name from a directory path."""
    base = path.name
    if base.endswith("-cairn"):
        base = base[: -len("-cairn")]
    # Normalize to kebab-case
    import re
    base = re.sub(r"[^a-z0-9-]+", "-", base.lower()).strip("-")
    return base or "cairn"
