"""`cairn mcp` — run the MCP server over stdio or HTTP.

See ADR-0009, ADR-0010, ADR-0012, and ADR-0013. Requires the ``[mcp]`` install extra.
"""

from __future__ import annotations

import os
from pathlib import Path

import typer

_VALID_TRANSPORTS = ("stdio", "streamable-http", "sse")


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
            "Transport to use: 'stdio' (default, for claude mcp add), "
            "'streamable-http' (long-running HTTP server), or 'sse' (SSE HTTP). "
            "stdio keeps the same trust surface as before. "
            "HTTP is opt-in; default binding is 127.0.0.1 (safe for single-user). "
            "Binding 0.0.0.0 expands the trust surface — use a reverse proxy "
            "with auth for group deployments."
        ),
    ),
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        help="Host to bind for HTTP transports (default: 127.0.0.1).",
    ),
    port: int = typer.Option(
        8765,
        "--port",
        help="Port to listen on for HTTP transports (default: 8765).",
    ),
    path: str = typer.Option(
        "/mcp",
        "--path",
        help="URL path for the MCP endpoint in HTTP transports (default: /mcp).",
    ),
    allowed_host: list[str] = typer.Option(
        [],
        "--allowed-host",
        help=(
            "Extra Host header values to accept for HTTP transports (repeatable). "
            "Required when fronting the server with a reverse proxy under a public "
            "hostname, since the MCP SDK's DNS-rebinding protection otherwise only "
            "accepts 127.0.0.1/localhost. Example: "
            "--allowed-host cairn.example.com"
        ),
    ),
    registry_path: Path | None = typer.Option(
        None,
        "--registry-path",
        help=(
            "Override the registry file location for this server only. "
            "Sets CAIRN_REGISTRY_PATH in-process. Used by `cairn dev serve` "
            "to give each dev server its own sandboxed registry (ADR-0013)."
        ),
    ),
    allow_dev_tools: bool = typer.Option(
        False,
        "--allow-dev-tools",
        help=(
            "Register dev-only MCP tools (currently: scaffold_fixture). "
            "Off by default; production deployments must NOT pass this. "
            "`cairn dev serve` always passes it (ADR-0013)."
        ),
    ),
    sandbox_path: Path | None = typer.Option(
        None,
        "--sandbox-path",
        help=(
            "Directory under which the scaffold_fixture dev tool writes "
            "cairns. Required when --allow-dev-tools is set."
        ),
    ),
) -> None:
    """Run the MCP server over stdio (default) or HTTP."""
    if transport not in _VALID_TRANSPORTS:
        typer.echo(
            f"error: invalid --transport '{transport}'. "
            f"Valid values: {', '.join(_VALID_TRANSPORTS)}.",
            err=True,
        )
        raise typer.Exit(code=1)

    if registry_path is not None:
        os.environ["CAIRN_REGISTRY_PATH"] = str(registry_path.expanduser())

    if allow_dev_tools and sandbox_path is None:
        typer.echo(
            "error: --allow-dev-tools requires --sandbox-path.",
            err=True,
        )
        raise typer.Exit(code=2)

    try:
        from ..mcp.server import _ensure_registry_loadable, build_server
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

        import cairn.registry as registry_mod

        server_module.load_registry = patched_load_registry  # type: ignore[assignment]
        registry_mod.load_registry = patched_load_registry  # type: ignore[assignment]

    _ensure_registry_loadable()
    if transport == "stdio":
        transport_info = {"transport": "stdio", "endpoint": None}
    else:
        transport_info = {
            "transport": transport,
            "endpoint": f"http://{host}:{port}{path}",
        }
    server = build_server(
        allow_dev_tools=allow_dev_tools,
        sandbox_path=sandbox_path,
        transport_info=transport_info,
    )

    if transport == "stdio":
        server.run()
        return

    # mcp>=1.27 takes host/port/path via settings, not run() kwargs.
    server.settings.host = host
    server.settings.port = port
    if allowed_host:
        # Extend the SDK's default localhost allowlist rather than replace it,
        # so docker-internal health checks and Traefik's forwarded request both
        # work. The SDK matches "host:*" against "host:port", so we add both
        # the bare hostname (no port — matches Host: cairn.example.com) and
        # a "host:*" variant for completeness.
        from mcp.server.transport_security import TransportSecuritySettings

        existing = server.settings.transport_security
        existing_hosts = list(existing.allowed_hosts) if existing else []
        existing_origins = list(existing.allowed_origins) if existing else []
        for h in allowed_host:
            if h not in existing_hosts:
                existing_hosts.append(h)
            wildcard = f"{h}:*"
            if wildcard not in existing_hosts:
                existing_hosts.append(wildcard)
            for scheme in ("https", "http"):
                origin = f"{scheme}://{h}"
                if origin not in existing_origins:
                    existing_origins.append(origin)
                origin_wildcard = f"{scheme}://{h}:*"
                if origin_wildcard not in existing_origins:
                    existing_origins.append(origin_wildcard)
        server.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=existing_hosts,
            allowed_origins=existing_origins,
        )
    if transport == "streamable-http":
        server.settings.streamable_http_path = path
        server.run(transport="streamable-http")
    else:  # sse
        server.settings.sse_path = path
        server.run(transport="sse")


def _default_name_for(p: Path) -> str:
    """Derive a default cairn name from a directory path."""
    base = p.name
    if base.endswith("-cairn"):
        base = base[: -len("-cairn")]
    import re

    base = re.sub(r"[^a-z0-9-]+", "-", base.lower()).strip("-")
    return base or "cairn"
