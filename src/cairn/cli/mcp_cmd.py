"""`cairn mcp` — run the MCP server over stdio or HTTP.

See ADR-0009, ADR-0010, and ADR-0011. Requires the ``[mcp]`` install extra.

Transport options (US-P-11):
- ``stdio`` (default): pipe-based, for Claude Code ``claude mcp add`` setups.
- ``streamable-http``: long-running HTTP server; use with ``--host`` / ``--port``.
- ``sse``: Server-Sent Events; legacy HTTP transport, still supported by some clients.

HTTP defaults are safe: ``--host 127.0.0.1`` keeps the trust surface the
same as stdio for single-user setups.  Binding ``0.0.0.0`` is allowed but
the help text names the trade-off (any process on the host can connect).

The tool surface is **identical** across transports — clients switch between
stdio and HTTP by changing connection config only.
"""

from __future__ import annotations

from pathlib import Path

import typer

_TRANSPORTS = ("stdio", "streamable-http", "sse")


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
    transport: str = typer.Option(
        "stdio",
        "--transport",
        help=(
            "Transport to use: stdio (default, for Claude Code `claude mcp add`), "
            "streamable-http (long-running HTTP server), or sse (legacy HTTP/SSE). "
            "HTTP is strictly opt-in; stdio setups continue to work unchanged."
        ),
    ),
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        help=(
            "Host to bind (HTTP transports only). Defaults to 127.0.0.1 so only "
            "local processes can connect. Use 0.0.0.0 to accept remote connections "
            "(ensure you have a reverse proxy or network-level access control)."
        ),
    ),
    port: int = typer.Option(
        8765,
        "--port",
        help="Port to listen on (HTTP transports only).",
    ),
    path: str = typer.Option(
        "/mcp",
        "--path",
        help="URL path to mount the MCP endpoint (HTTP transports only).",
    ),
) -> None:
    """Run the MCP server (stdio by default; use --transport for HTTP)."""
    if transport not in _TRANSPORTS:
        typer.echo(
            f"error: unknown transport '{transport}'. "
            f"Valid values: {', '.join(_TRANSPORTS)}",
            err=True,
        )
        raise typer.Exit(code=1)

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

    if transport == "stdio":
        run()
    else:
        run(transport=transport, host=host, port=port, path=path)


def _default_name_for(path: Path) -> str:
    """Derive a default cairn name from a directory path."""
    base = path.name
    if base.endswith("-cairn"):
        base = base[: -len("-cairn")]
    import re
    base = re.sub(r"[^a-z0-9-]+", "-", base.lower()).strip("-")
    return base or "cairn"
