# ADR-0012: MCP over HTTP — server transport and CLI remote dispatch

**Date:** 2026-05-21
**Status:** accepted
**Related:** ADR-0006 (`cairn.toml` + `CairnTarget` deferred), ADR-0009 (MCP v0, stdio), ADR-0010 (one server, many cairns)

## Context

ADR-0009 shipped the MCP server over stdio only. ADR-0010 made one server address many cairns. Together they create a topology that stdio cannot serve:

- A long-running per-machine (or per-group) MCP server, not a per-session subprocess.
- Background Phase-5 agents (literature monitors, critique agents) that need a stable endpoint independent of any interactive client.
- A cairn hosted on a group box that every collaborator's Claude Code instance reaches without ssh-tunneling.

`cairn.toml`'s `endpoint` field has existed since ADR-0006 as unreachable schema: no CLI writes it, and the validator rejects it alongside any other field. This ADR closes those gaps across three stories.

## Decision

### US-P-11: HTTP transport for `cairn mcp`

`cairn mcp --transport {stdio,streamable-http,sse}` selects the transport. Default remains `stdio` so existing `claude mcp add cairn cairn mcp` setups continue to work unchanged. HTTP is strictly opt-in.

HTTP mode accepts `--host` (default `127.0.0.1`), `--port` (default `8765`), and `--path` (default `/mcp`), forwarded to FastMCP. The default host binding keeps the trust surface identical to stdio for single-user setups; `0.0.0.0` is permitted but the flag help names the trade-off.

The tool surface (Tier-1/2/3 from ADR-0009) is **identical** across transports — same names, parameters, and return shapes. Clients move between stdio and HTTP by changing connection config only.

Cairn ships no built-in auth in this slice. The help text and README direct operators at reverse-proxy / private-network patterns. The `author` parameter the server validates against `state/collaborators.yaml` remains **attribution, not authentication** — a future ADR binds caller identity (TLS / OIDC subject / bearer token) to the `author` claim.

### US-P-12: Remote pairing via `cairn link --endpoint`

`cairn link --endpoint <url> --name <cairn>` writes a remote-mode `cairn.toml` and prints client-neutral pairing info (endpoint + cairn name + auth-header hint) followed by Claude Code bootstrap hints.

The `cairn.toml` validator moves from "exactly one of N/P/E" to three explicit modes:

| Mode | Fields | Resolves to |
|---|---|---|
| local-path | `path = "..."` | filesystem path, relative to `cairn.toml`'s directory |
| local-registry | `name = "..."` | user registry (`~/.config/cairn/server.toml`) lookup |
| remote MCP | `endpoint = "..."` + `name = "..."` | HTTP MCP server at `endpoint`; `name` is the cairn handle |

Invalid combinations (rejected with actionable errors): empty pointer; `name` + `path`; `endpoint` + `path`; `endpoint` without `name`.

`cairn link --endpoint <url>` probes the URL before writing the pointer. `--no-probe` skips this for offline pairing.

Pairing travels with the repo. Credentials do not.

### US-P-13: Remote dispatch from CLI write commands

In a project repo with a remote-mode `cairn.toml`, the four Tier-1 write commands (`cairn decision add`, `cairn finding add`, `cairn action add`, `cairn action complete`) transparently dispatch over HTTP by invoking the matching MCP write tool with `cairn = <name>` and the user's arguments. No CLI shape changes.

**Credentials** live outside the cairn and the project repo. Resolution order:
1. `CAIRN_BEARER_TOKEN` environment variable
2. `~/.config/cairn/credentials.toml` keyed by endpoint URL (mode `0600` on write)

No third source. Credentials are never written into `cairn.toml` and never committed.

**Attribution**: `--author` defaults to the git-config user mapped to a `state/collaborators.yaml` id (existing local behavior). The CLI does not pre-validate in remote mode because `state/collaborators.yaml` lives on the remote; the server runs `_validate_author()` and surfaces an actionable error if the id is unknown.

**Failures are CLI-shaped, not SDK tracebacks:**
- Missing token: "no credentials configured for `<endpoint>`; set `CAIRN_BEARER_TOKEN` or add an entry to `~/.config/cairn/credentials.toml`."
- HTTP 401/403: "authentication failed against `<endpoint>`."
- Network unreachable: distinct from "remote rejected the call."
- Remote-side validation errors are passed through with the offending parameter named.

This lands the `MCPEndpoint` arm of `CairnTarget` anticipated by ADR-0006 and deferred by ADR-0009. `resolve_or_exit_with_remote()` in `_common.py` returns either `CairnPaths` (local) or `RemoteTarget(endpoint, cairn_name)`; write commands branch on the type. `LocalPath` operates on files (today's behavior, untouched); `RemoteTarget` opens a short-lived `streamable-http` client, calls the tool, closes.

**Reads are deliberately out of scope for this slice.** `cairn status`, `cairn validate`, `cairn agenda draft` against a remote-mode repo continue to error or no-op as today; agents handle reads through their MCP client. Writes-first is the minimum slice that restores the human-write path for remote cairns.

## Consequences

**Good:**
- Remote, shared cairns become accessible to CLI users without SSH tunnels.
- The substrate-as-specification commitment is preserved for remote mode: humans can write to a remote cairn with the same `cairn decision add` etc. they use locally.
- Stdio default means zero impact on existing stdio setups.
- `cairn.toml` validator now has a clear three-mode model instead of the ambiguous "exactly one" rule.

**Neutral / deferred:**
- No built-in auth in this slice. Operators use reverse proxies or private networks until a future ADR binds caller identity (TLS/OIDC) to the `author` claim.
- CLI-side reads against a remote cairn remain out of scope. The read half of `MCPEndpoint` follows once write-path UX has shaken out.

**Risks:**
- `asyncio.run()` in a CLI context will fail if the caller already has a running event loop (e.g., if a future Typer version goes async). Mitigated by the short-lived, single-call pattern — no long-lived connection.
