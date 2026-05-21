"""Remote MCP dispatch for CLI write commands (US-P-13).

When a project repo's ``cairn.toml`` specifies a remote endpoint, the CLI
write commands use this module to dispatch over HTTP instead of writing local
files.  Each call opens a short-lived streamable-http MCP client, calls the
tool, and closes.  No long-lived connection or in-memory session state.

Credentials are resolved via ``cairn.credentials.load_bearer_token``
(env var ``CAIRN_BEARER_TOKEN`` first, then ``~/.config/cairn/credentials.toml``).
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from ..credentials import load_bearer_token
from ..errors import CairnError


class RemoteDispatchError(CairnError):
    """Raised when a remote MCP tool call fails."""


def dispatch_tool(
    endpoint: str,
    cairn_name: str,
    tool_name: str,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Call an MCP tool on a remote cairn server.

    ``endpoint`` is the HTTP base URL (e.g. ``https://cairn.example.com``).
    ``cairn_name`` is the cairn handle on that server.
    ``tool_name`` is the MCP tool name (e.g. ``add_decision``).
    ``args`` are the tool arguments (excluding ``cairn``, which is added here).

    Returns the parsed JSON result dict from the server.
    Raises ``RemoteDispatchError`` on any failure (network, auth, or server-side).
    """
    token = load_bearer_token(endpoint)
    try:
        return asyncio.run(_dispatch_async(endpoint, cairn_name, tool_name, args, token))
    except RemoteDispatchError:
        raise
    except Exception as exc:
        raise RemoteDispatchError(f"unexpected error calling {tool_name} on {endpoint}: {exc}") from exc


async def _dispatch_async(
    endpoint: str,
    cairn_name: str,
    tool_name: str,
    args: dict[str, Any],
    token: str | None,
) -> dict[str, Any]:
    try:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
    except ImportError as exc:
        raise RemoteDispatchError(
            f"remote dispatch requires the [mcp] extra. "
            f"Install with: pip install 'cairn[mcp]' (import error: {exc})"
        ) from None

    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    mcp_url = endpoint.rstrip("/")

    full_args = {**args, "cairn": cairn_name}

    try:
        async with streamablehttp_client(mcp_url, headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, full_args)
    except Exception as exc:
        _raise_from_http_exc(exc, endpoint)

    if result.isError:
        error_text = result.content[0].text if result.content else "unknown server error"
        raise RemoteDispatchError(error_text)

    if not result.content:
        return {}

    raw = result.content[0].text
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"message": raw}


def _raise_from_http_exc(exc: Exception, endpoint: str) -> None:
    """Translate low-level exceptions into user-facing RemoteDispatchError."""
    msg = str(exc)
    lowered = msg.lower()
    if "401" in msg or "unauthorized" in lowered:
        raise RemoteDispatchError(
            f"authentication failed against {endpoint}. "
            f"Check your bearer token (CAIRN_BEARER_TOKEN or "
            f"~/.config/cairn/credentials.toml)."
        ) from exc
    if "403" in msg or "forbidden" in lowered:
        raise RemoteDispatchError(
            f"access denied by {endpoint} (HTTP 403). "
            f"Verify your credentials have write access."
        ) from exc
    if "404" in msg or "not found" in lowered:
        raise RemoteDispatchError(
            f"MCP endpoint not found at {endpoint}. "
            f"Verify the URL and that the server is running."
        ) from exc
    if any(k in lowered for k in ("connection refused", "connect error", "unreachable", "name or service not known")):
        raise RemoteDispatchError(
            f"network unreachable: could not connect to {endpoint}. "
            f"Check the URL and that the server is running."
        ) from exc
    raise RemoteDispatchError(
        f"error calling remote cairn at {endpoint}: {exc}"
    ) from exc
