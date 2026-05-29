# 0013 — Server-side fixture scaffold for remote dev MCP servers

## Context

US-T-01 added the `cairn dev` subgroup so the multi-user/multi-cairn test methodology has a one-line setup: `cairn dev serve` starts an HTTP MCP server, `cairn dev scaffold-fixture` materializes a fixture project + paired cairn. The implementation assumed **client and server share a filesystem** — the scaffolder writes the cairn locally and the server (running on the same host) finds it via the user-level registry (ADR-0010).

That assumption breaks the moment the dev MCP server moves to a different host. Smoke-testing a remote dev server at `cairn-mcp-…wisc.edu` surfaced this concretely: the server had no cairns registered, the client had no way to register one (the registry stores a *server-side* path the client doesn't know and can't write to), and the result was a clean protocol handshake followed by every tool call returning `Error executing tool …: no cairn named 'X' registered`.

Three shapes were on the table:

1. **Client-side scaffold + `register_cairn` MCP tool** — the client scaffolds locally, then asks the server to add the name → path mapping. Works only when client and server share a filesystem (the path is meaningless to the server otherwise). Solves the local-dev case but not the remote case the wisc.edu deployment makes interesting.
2. **Client uploads cairn** — package the scaffolded cairn into a tarball / git bundle and push it. Large surface (transport, deduplication, partial upload resumption), and a remote-code-execution shape if the server later runs hooks on uploaded content. Out of scope for the test harness.
3. **Server-side scaffold tool, client triggers** — the client calls an MCP tool with a fixture *name*; the server scaffolds the cairn from its local fixture catalog into a sandbox dir, registers it, and returns the handle. The client then scaffolds only the project repo locally and writes `cairn.toml` pointing at the remote endpoint with the returned name.

Option 3 is the only one that handles the truly-remote case without inventing a file transport. It also keeps the security shape tight: the wire carries a fixture *name* (whitelist lookup against `cairn.dev.fixtures_data`), never arbitrary scaffold instructions or filesystem paths.

## Decision

### A dev-only `scaffold_fixture` MCP tool

The server exposes a new tool, conditionally registered:

```python
scaffold_fixture(
    name: str,                  # one of the known fixture keys
    as_name: str | None = None, # cairn handle to register; defaults to `name`
) -> {
    "cairn": str,               # the registered handle
    "fixture": str,             # echo of `name`
    "summary": {                # for client-side verification
        "collaborators": [...],
        "decisions": int,
        "questions": int,
        "findings": int,
    },
}
```

The server's behaviour:

1. Reject any `name` not in `cairn.dev.fixtures_data.FIXTURES`. Whitelist lookup; no path or content from the wire.
2. Pick a sandbox dir under `$XDG_CACHE_HOME/cairn/dev-servers/<pid>/cairns/<as_name>/`. The path is server-internal; clients never see it.
3. Run the same scaffold path the local CLI uses (`cairn.dev.fixtures.scaffold_fixture`'s cairn half — see "Responsibility split" below).
4. Register the result under `as_name` in the server's *dev registry* (see "Registry isolation").
5. Return the summary so the client can sanity-check that the server's fixture catalog matches its own.

Errors return `isError: true` with a structured message: unknown fixture name, name conflict in the dev registry, or sandbox write failure.

### Responsibility split: server scaffolds the cairn, client scaffolds the project

A fixture today bundles three things: a fictional **project repo** (files + commits), a paired **cairn** (state + seed data), and a `cairn.toml` linking them. For the remote case these live in different places:

- The **cairn** must live on the server — that's what the MCP tools read and write.
- The **project repo** must live on the client — that's where the user runs `cairn decision add` from.
- The `cairn.toml` lives in the project repo and points at the remote endpoint.

So `scaffold_fixture` scaffolds *only the cairn half*. The client, after the tool returns, materializes the project files using its own copy of `cairn.dev.fixtures_data` and writes `cairn.toml`. Both sides import the same module from the same package, so the fixture definition is the source of truth and there is no wire schema for fixture content.

If client and server have different `cairn` versions and the fixture catalog has drifted, the `summary` field on the response lets the client detect the mismatch (collaborator IDs / decision count differ from what its local fixture expects) and abort with a clear error rather than producing a half-broken pairing.

### Gating: `cairn mcp --allow-dev-tools`

A new flag on `cairn mcp` controls whether dev-only tools are registered. Default **off**. The tool is registered at server construction time, not gated at call time — so unauthorized callers cannot discover the tool's existence via `tools/list`.

```
cairn mcp --transport streamable-http --allow-dev-tools
```

`cairn dev serve` always passes the flag (it is, by definition, a dev surface). Production deployments must not pass it; deployment docs will say so explicitly.

The flag is one gate for the *category* "dev tools" rather than one flag per tool. A future `unregister_cairn` or `reset_cairn` follows the same gate.

### Registry isolation: dev mode uses a per-server XDG-cache registry

The dev server must not write into the user's production `~/.config/cairn/server.toml`. When `--allow-dev-tools` is set, `cairn mcp` resolves its registry from:

1. `--registry-path <file>` if explicitly passed, else
2. `$XDG_CACHE_HOME/cairn/dev-servers/<pid>/registry.toml`, else
3. (only when the flag is **off**, i.e. production) `~/.config/cairn/server.toml`.

`cairn dev serve` doesn't need to pass `--registry-path` explicitly — the per-pid default does the right thing. `cairn dev stop` removes the per-pid sandbox directory (including the registry) as part of its existing cleanup.

This also gives production deployments a way to use a non-default registry (multi-tenant servers, deployment-config-managed registries) without inventing a separate flag later.

### Client wiring: `cairn dev scaffold-fixture --remote <URL>`

A new flag on the existing scaffold command:

```
cairn dev scaffold-fixture coral-bleach \
    --dest /tmp/x \
    --remote https://cairn-mcp.example.com/mcp
```

The command:

1. Calls `scaffold_fixture(name="coral-bleach")` on the remote endpoint via `cairn.mcp.remote.call_tool`, reusing the existing token-resolution flow (`CAIRN_BEARER_TOKEN` / `credentials.toml`).
2. Verifies the returned `summary` matches the local fixture definition (same collaborator IDs, same counts). Aborts on mismatch.
3. Materializes the project repo locally at `<dest>/projects/<name>/` with the fictional project files, git history, and `cairn.toml` pointing at `<URL>` with the returned cairn name.
4. **Does not** create a local `<dest>/cairns/<name>/` directory — the cairn lives on the server.

`--remote` is mutually exclusive with `--http-endpoint`. The latter remains for the existing same-machine fixture flow (where the client both scaffolds the local cairn and writes the project's `cairn.toml`).

`--remote` implies `paired_via_http` for any fixture, so all three fixtures become remote-capable. The existing `paired_via_http` field on `Fixture` is retired in favour of "the *flag* determines the pairing mode."

## Consequences

- **Remote dev MCP servers become usable for the multi-user/multi-cairn methodology.** A single shared dev MCP can host fixtures for multiple test runs from multiple clients without ssh access to the server.

- **No new file-transport surface.** The wire stays JSON-RPC over HTTP. The fixture catalog is a versioned constant in the `cairn` package, not data that travels.

- **Security shape is tight by construction.** The tool accepts a name from a hardcoded whitelist; the sandbox path is server-internal; the gate is off by default; the registry is isolated. A leaked dev-server URL leaks the ability to scaffold one of three known fixtures into ephemeral cache, not arbitrary writes.

- **Slight ceremony at version skew.** When server and client `cairn` versions differ enough that the fixture catalog has drifted, the `summary`-field check catches it and reports a clean error instead of producing a half-broken pairing. Server operators can bump the fixture catalog without coordinating a synchronized client release, at the cost of the new client needing a corresponding bump.

- **`paired_via_http` on `Fixture` is removed.** The pairing mode becomes a property of the scaffold *invocation* (`--remote` vs `--http-endpoint` vs neither), not of the fixture definition. The `shared-physics-paper` fixture loses its special status; any fixture works in any mode.

- **Production-side `cairn mcp` is unchanged.** No new tool, no new flag in the default path, no new registry. The whole proposal is gated behind `--allow-dev-tools` which the production CLI never passes.

- **Cleanup is owned by `cairn dev stop`.** Killing a dev server removes its per-pid sandbox, including the registry and any scaffolded cairns. No orphan state survives a clean stop. Crash recovery (PID dir lingers after kill -9) is handled by the existing `list_servers()` stale-entry pruning, extended to also rm the sandbox dir.

- **Trigger for revisiting:** if remote-dev usage outgrows the three-fixture catalog and clients want to scaffold *user-defined* fixtures, this design needs to extend — either a structured fixture-content protocol or a file-upload transport. At that point security review reopens. Until then, name-only whitelist is the right shape.

## Alternatives considered

- **`register_cairn` MCP tool taking a server-side path.** Works for same-machine dev (client scaffolds locally, asks server to read at that path); does nothing for the remote case the wisc.edu deployment makes interesting. Rejected as half-solving the problem.

- **Client uploads a tarball / git bundle.** Solves the remote case but introduces a file-transport surface (chunking, validation, deduplication) and an RCE shape if the server ever runs hooks on uploaded content. Disproportionate complexity for a test harness. Rejected; flagged as the natural next step if user-defined fixtures become a requirement.

- **Pre-bake fixtures into the server's filesystem image at deployment time.** Operationally cumbersome (every fixture change requires a server redeploy), and the client still needs to learn the registered handles out-of-band. Rejected.

- **One gate flag per dev tool** (`--allow-register-cairn`, `--allow-scaffold-fixture`, …). Operator-hostile. Rejected in favour of one category gate (`--allow-dev-tools`) covering all dev-only tools.
