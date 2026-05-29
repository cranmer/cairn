# 0015 — `unregister_fixture` dev MCP tool and `cairn dev unregister-fixture` CLI

## Context

[ADR-0013](0013-server-side-fixture-scaffold-tool.md) gave the dev MCP server a
`scaffold_fixture` tool that seeds a cairn into the server's per-pid sandbox
and registers it in the isolated dev registry. The forward half of the fixture
lifecycle is complete; the inverse is not. ADR-0013 anticipated this gap
explicitly:

> The flag is one gate for the *category* "dev tools" rather than one flag per
> tool. A future `unregister_cairn` or `reset_cairn` follows the same gate.

Today the only teardown available is `cairn dev stop --all`, which kills the
server and wipes the entire per-pid sandbox. That is the right shape for "tear
down everything between test runs," but it is the wrong shape for two cases
the multi-user/multi-cairn methodology now exercises:

1. **Resetting one fixture mid-run.** A sub-agent in the
   `tests/agent_smoke/multi-user-multi-cairn/` recipe (the many-users-one-cairn
   scenario from `docs/scenario-many-users-one-cairn.html`) gets into a known
   state, runs assertions, and wants to rewind a single fixture without
   restarting the server every other test.
2. **Reclaiming a handle without dropping the rest.** A scaffold call can
   wedge a registered handle (mistyped `--as`, abandoned partial run). Today
   the only recovery is restarting the server, which is disproportionate.

There is a parallel question — *what about the local project repo on the
client?* — that this ADR explicitly does not answer with a server tool. The
server has no knowledge of where any client's project repo lives. The CLI
wrapper, which runs on the client, can offer optional local cleanup, but the
MCP tool stays strictly server-side.

## Decision

### A dev-only `unregister_fixture` MCP tool

The server exposes a new tool, gated by the same `--allow-dev-tools` flag as
`scaffold_fixture` and `list_fixtures`:

```python
unregister_fixture(
    name: str,
    keep_files: bool = False,
) -> {
    "unregistered": bool,        # False when the name wasn't in the registry
    "cairn": str,                # echo of `name`
    "removed_path": str | None,  # absolute path that was rm'd, or null
    "kept_files": bool,          # True if the dir was preserved
    "reason": str | None,        # set only on idempotent no-ops
}
```

Behavior:

1. **Idempotent on missing entries.** `lookup(name)` against the dev registry;
   if absent, return `{"unregistered": False, ..., "reason": "not_registered"}`
   without raising. Teardown scripts can run this twice without special-casing.
2. **Sandbox-scoped delete.** Capture the registered path, call
   `registry.unregister(name)`, then `shutil.rmtree(path)` only when both
   `keep_files` is False *and* the path resolves under the server's own
   `sandbox` directory. Paths outside the sandbox are left untouched and
   `kept_files: true` is returned. This is the hard architectural boundary:
   the tool can only ever delete things inside its own sandbox.
3. **Already-missing directory is success.** If the registered path resolves
   to nothing on disk (manually removed, prior crash), the tool reports
   `removed_path: null` rather than erroring. The registry entry is still
   removed.

The whitelist + path-safety shape mirrors `scaffold_fixture` deliberately:
nothing about a fixture name from the wire grants the server permission to
write or delete outside its sandbox.

### A `cairn dev unregister-fixture` CLI command

Parallel to `cairn dev scaffold-fixture`. Always operates against a remote dev
MCP server — fixtures scaffolded locally without `--remote` (the
one-user-many-cairns scenario in `docs/scenario-one-user-many-cairns.html`)
aren't registered anywhere and don't need this command; `rm -rf` or
`cairn unregister` handles those.

```
cairn dev unregister-fixture <name>
    [--remote <URL>]            # required; falls back to CAIRN_DEV_REMOTE_URL
    [--keep-files]              # forwarded to the MCP tool
    [--project-dir <dir>]       # optional, client-side only
```

`--remote` reuses the same env-var fallback as `cairn dev fixtures` and
`cairn dev scaffold-fixture --remote` (the helper landed in commit `116350e`).

The optional `--project-dir <dir>` flag is a **client-side** convenience for
the smoke-test harness simulating a collaborator's laptop. When supplied, the
CLI checks that `<dir>/cairn.toml` exists and its `name` matches `<name>`
*before* dispatching the server-side call — a typo'd path must not trigger
an irreversible server-side unregister + sandbox delete. If the pre-flight
passes, the CLI then makes the remote call and, on success, `shutil.rmtree(dir)`.
A mismatched or malformed `cairn.toml` is a refusal (exit 1) with the server
left untouched; the user asked to delete a specific paired project and the
CLI either does so safely or stops. A directory that simply doesn't exist
is treated as "nothing to clean" — the remote call still goes through, since
no local state can be corrupted by it. The server is never told the path.

### Gating

Same `--allow-dev-tools` flag as the other dev tools. The tool is registered
at server construction time, not gated at call time, so unauthorized callers
cannot discover its existence via `tools/list`. ADR-0013's commitment that the
flag covers the dev-tools *category* is exactly the point.

## Consequences

- **Single-fixture reset becomes a one-call operation.** The methodology at
  `tests/agent_smoke/multi-user-multi-cairn/` can rewind one shared cairn
  between scenarios without restarting the server or losing its
  state file entry, so port assignments and other state remain stable across
  the run.
- **Blast radius is exactly the sandbox.** The path-safety guard ensures the
  server-side tool only touches paths under its own per-pid sandbox dir. Any
  cairn registered at a path outside (which the existing
  `scaffold_fixture` path doesn't produce, but is defensible against future
  manual registry edits) is left strictly alone.
- **Idempotency is part of the contract.** Test cleanup that runs after a
  partial run, or runs twice by mistake, succeeds the same way both times.
  No "did this already happen?" branching in the harness.
- **Client project repos remain wholly user-managed.** The MCP tool never
  receives a project path, never deletes anything outside the sandbox, and
  has no opinion about whether a `cairn.toml` somewhere points at a now-
  vanished fixture. Stale client `cairn.toml` files are the user's (or
  harness's) responsibility — the CLI's `--project-dir` opt-in handles the
  common case.
- **No new gate, no new transport, no new file format.** The shape is
  isomorphic to ADR-0013: whitelist name in, structured result out, sandbox-
  bounded side effect.
- **Trigger for revisiting:** if a future need emerges to "reset" rather than
  "unregister" (re-run the scaffold steps to restore a known state without
  going through `unregister` + `scaffold`), a sibling `reset_fixture` tool
  fits naturally next to this one. Until that pressure exists, the simpler
  unregister-then-rescaffold path is enough.

## Alternatives considered

- **Reuse `cairn unregister` directly.** The existing CLI command removes an
  entry from whatever registry `CAIRN_REGISTRY_PATH` resolves to, which during
  a `cairn dev serve` run *is* the dev registry. But it does not delete the
  cairn directory, knows nothing about the sandbox, and is wired through the
  production CLI surface rather than the `cairn dev` namespace. Wrapping it
  in `cairn dev unregister-fixture` with the sandbox-aware delete is cleaner
  than asking test scripts to compose two commands and remember the path.
- **Make the CLI manage the local project repo by tracking scaffold history.**
  Would let `cairn dev unregister-fixture <name>` clean up the paired project
  without an explicit `--project-dir`. Requires the CLI to maintain client-
  side state (a registry of "I scaffolded X at path Y"), which is new persistent
  state for a command set that has otherwise stayed stateless. Rejected;
  the optional `--project-dir` flag covers the use case without inventing
  new state.
- **Allow the MCP tool to take a path.** Lets a sufficiently-trusted client
  ask the server to wipe arbitrary paths. Inconsistent with ADR-0013's
  name-only whitelist shape and a clear escalation of the dev-tools trust
  boundary. Rejected.
