"""Short-lived HTTP MCP client for remote-cairn write dispatch (US-P-13).

Implements the MCP streamable-HTTP transport handshake using stdlib
``urllib.request`` so no extra dependencies beyond ``mcp>=1.0`` are
needed.  Each CLI invocation:

1. POSTs ``initialize`` and captures the ``Mcp-Session-Id`` response
   header (the session token the server assigns).
2. POSTs ``notifications/initialized`` to acknowledge the handshake.
3. POSTs the ``tools/call`` for the requested tool.

Steps 1 and 2 are required by the MCP spec; without them the server
rejects ``tools/call`` with ``HTTP 400 "Missing session ID"``.

Error mapping:
- Missing token           → ``RemoteAuthError``
- HTTP 401/403            → ``RemoteAuthError``
- Network unreachable     → ``RemoteNetworkError``
- Remote validation error → ``RemoteCallError`` (message forwarded)
- Unknown/unexpected      → ``RemoteCallError``
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

# Protocol version we claim during initialize.  MCP servers negotiate
# downward so claiming a recent version is safe; the server echoes back
# whichever version it actually supports.
_PROTOCOL_VERSION = "2025-06-18"
_CLIENT_INFO = {"name": "cairn-cli", "version": "0"}
_SESSION_HEADER = "Mcp-Session-Id"
_ACCEPT = "application/json, text/event-stream"


class RemoteError(Exception):
    """Base for all remote-dispatch errors."""


class RemoteAuthError(RemoteError):
    """Authentication failed or no credentials configured."""


class RemoteNetworkError(RemoteError):
    """Could not reach the remote server."""


class RemoteCallError(RemoteError):
    """The remote server returned an error for the tool call."""


def call_tool(
    endpoint: str,
    tool_name: str,
    arguments: dict[str, Any],
    *,
    token: str | None = None,
) -> dict[str, Any]:
    """Call *tool_name* on the MCP server at *endpoint*.

    Performs the streamable-HTTP session handshake (initialize +
    notifications/initialized) before the actual ``tools/call``.

    *arguments* maps directly to the tool's parameter list.
    Returns the tool's response dict.
    Raises a ``RemoteError`` subclass on any failure.
    """
    session_id = _initialize_session(endpoint, token)
    _send_initialized_notification(endpoint, token, session_id)
    response = _request(
        endpoint,
        token,
        session_id,
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        },
    )
    return _extract_tool_result(endpoint, response)


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------


def _initialize_session(endpoint: str, token: str | None) -> str:
    """POST initialize and return the session id the server assigned."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": _PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": _CLIENT_INFO,
        },
    }
    raw, response_headers = _post(endpoint, token, None, payload, expect_response=True)
    session_id = response_headers.get(_SESSION_HEADER)
    if not session_id:
        # Some servers may use a different case or omit it on initialize errors.
        for key in response_headers:
            if key.lower() == _SESSION_HEADER.lower():
                session_id = response_headers[key]
                break
    if not session_id:
        raise RemoteCallError(
            f"server at {endpoint} did not return an {_SESSION_HEADER} "
            f"header on initialize; cannot establish a session"
        )
    # Surface a clear error if initialize itself failed.
    data = _decode_jsonrpc(endpoint, raw)
    if "error" in data:
        err = data["error"]
        msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
        raise RemoteCallError(f"initialize failed at {endpoint}: {msg}")
    return session_id


def _send_initialized_notification(
    endpoint: str, token: str | None, session_id: str
) -> None:
    """POST the initialized notification (no response expected)."""
    payload = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    _post(endpoint, token, session_id, payload, expect_response=False)


def _request(
    endpoint: str,
    token: str | None,
    session_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    raw, _ = _post(endpoint, token, session_id, payload, expect_response=True)
    return _decode_jsonrpc(endpoint, raw)


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------


def _post(
    endpoint: str,
    token: str | None,
    session_id: str | None,
    payload: dict[str, Any],
    *,
    expect_response: bool,
) -> tuple[bytes, dict[str, str]]:
    """POST *payload* as JSON; return (raw_body, response_headers).

    For notifications (expect_response=False) the body is discarded and
    the call returns an empty bytes object.
    """
    body = json.dumps(payload).encode()
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": _ACCEPT,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if session_id:
        headers[_SESSION_HEADER] = session_id

    req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read() if expect_response else b""
            response_headers = {k: v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise RemoteAuthError(
                f"authentication failed against {endpoint} (HTTP {exc.code})"
            ) from None
        try:
            err_body = exc.read().decode(errors="replace")
        except Exception:
            err_body = ""
        raise RemoteCallError(
            f"HTTP {exc.code} from {endpoint}: {err_body[:200]}"
        ) from None
    except urllib.error.URLError as exc:
        raise RemoteNetworkError(
            f"could not reach {endpoint}: {exc.reason}"
        ) from None
    except OSError as exc:
        raise RemoteNetworkError(f"network error calling {endpoint}: {exc}") from None

    return raw, response_headers


def _decode_jsonrpc(endpoint: str, raw: bytes) -> dict[str, Any]:
    """Parse a JSON-RPC response, accepting either JSON or SSE framing."""
    if raw.startswith(b"data:") or b"\ndata:" in raw[:200]:
        return _parse_sse_response(raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RemoteCallError(
            f"unexpected non-JSON response from {endpoint}: {exc}"
        ) from None


def _extract_tool_result(endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
    """Pull the tool's payload out of a JSON-RPC ``tools/call`` response."""
    if "error" in data:
        err = data["error"]
        msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
        raise RemoteCallError(f"remote error from {endpoint}: {msg}")

    result = data.get("result")
    if result is None:
        raise RemoteCallError(
            f"unexpected MCP response shape from {endpoint}: {data}"
        )

    # MCP tools/call wraps the payload under result.content[0].text (JSON string)
    # or directly as result if FastMCP serialised it flat.
    if isinstance(result, dict) and "content" in result:
        content = result["content"]
        if isinstance(content, list) and content:
            first = content[0]
            if isinstance(first, dict) and first.get("type") == "text":
                try:
                    return json.loads(first["text"])
                except (json.JSONDecodeError, KeyError):
                    return first
        return result
    if isinstance(result, dict):
        return result
    # Scalar or list result — wrap for uniform handling.
    return {"result": result}


def _parse_sse_response(raw: bytes) -> dict[str, Any]:
    """Extract the JSON-RPC response from an SSE data stream."""
    for line in raw.decode(errors="replace").splitlines():
        if line.startswith("data:"):
            payload = line[len("data:"):].strip()
            if payload and payload != "[DONE]":
                try:
                    return json.loads(payload)
                except json.JSONDecodeError:
                    continue
    raise RemoteCallError("could not parse SSE response")


def probe(endpoint: str, *, token: str | None = None, timeout: int = 10) -> bool:
    """Return True if *endpoint* is reachable (any 2xx or 4xx response).

    A 4xx means the server is up but the request was bad (auth, path) —
    still "reachable". Only network errors return False.
    """
    headers: dict[str, str] = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(endpoint, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except urllib.error.HTTPError:
        return True  # server responded → reachable
    except (urllib.error.URLError, OSError):
        return False
