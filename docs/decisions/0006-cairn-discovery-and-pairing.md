# 0006 — Cairn discovery, project pairing, and skills install

## Context

ADR-0005 committed to B1 — global skills install + cairn discovery — as the planned Mode B answer, deferred. With Mode B coverage now in scope for Phase 2, the implementation question gets concrete: *given an agent in some arbitrary working directory, how does a cairn-aware skill or CLI command find the cairn it should operate on?*

ADR-0005 sketched a four-step resolution (cwd-walk for a `state/collaborators.yaml` marker → `CAIRN_PATH` env var → user-level config → ask). Walking the design forward revealed three problems:

1. **`state/collaborators.yaml` is a weak marker.** It's a state file that happens to exist in every cairn, not an unambiguous "this directory is a cairn" signal. Using it conflates schema validation concerns with discovery concerns and breaks if the file is missing or renamed later.

2. **A user-level config (`~/.config/cairn/config.toml`) puts the project↔cairn pairing in the wrong place.** The pairing is *information about the project* — which cairn does this code repo belong to? — not information about the user. Storing it per-user means: (i) the pairing doesn't travel when a new collaborator clones the project repo, (ii) the pairing doesn't survive moving between machines, (iii) the user has to maintain a mapping that scales linearly with their projects.

3. **MCP is a foreseeable future backend.** A near-term direction is for cairn to be reachable via an MCP server (so that writes can be remote, multi-user, or sandboxed) rather than only via a local directory. The discovery layer should be able to dispatch to either backend without rewrites.

The remedy is a small redesign of the discovery story. ADR-0005's *decision* (B1 over B2 / B3, global skills install as the v0 Mode B answer) still stands; this ADR supersedes only the four-step resolution sketch.

## Decision

### Three artifacts

1. **`.cairn` marker file** at the root of every cairn. Written by `cairn init`. Unambiguously identifies a directory as a cairn root. Contents may grow over time (currently: a header line and the cairn's canonical name); existence alone is sufficient for discovery. `cairn validate` flags pre-existing cairns missing the marker; `cairn init` is idempotent on an existing cairn root and adds the marker if absent.

2. **`cairn.toml` pointer file** at the root of a *project repo* that has been paired with a cairn. Written *only* by an explicit, user-invoked `cairn link <project-repo>` command — never as a side effect of `cairn init`. Schema accommodates both local and (future) MCP backends from day one:

   ```toml
   [cairn]
   # Local backend — relative paths resolved against this file's directory.
   path = "../foo-cairn"

   # Future MCP backend — mutually exclusive with `path`.
   # endpoint = "https://cairn.example.org/projects/foo"
   ```

   This is the *only* circumstance under which Cairn writes into a project repo. Reconciled with US-P-10 by being opt-in and user-initiated.

3. **Globally-installed skills** at `~/.claude/skills/cairn-<name>/`, copied from `templates/default/skills/` by an explicit `cairn skills install` command. Mirrors the symmetric `cairn skills uninstall`. Installation is never a side effect of `pipx install cairn`.

### Discovery algorithm

A single cwd-walk with two possible hits. Used by every cairn-touching CLI command and skill:

1. Walk upward from cwd. First hit wins:
   - `.cairn` found → the containing directory *is* the cairn; target is `LocalPath(<that dir>)`.
   - `cairn.toml` found → the containing directory is a *paired project repo*; parse the file and construct the target accordingly (`LocalPath` or, in future, `MCPEndpoint`).
2. Else, check `$CAIRN_PATH`. If set, target is `LocalPath($CAIRN_PATH)`.
3. Else, error with an actionable message: *"no cairn found from here. Run `cairn link <project-repo>` to pair this directory with an existing cairn, or set `$CAIRN_PATH`, or `cd` into a cairn."*

A user-level config is **not** part of the v0 discovery path. If multi-project ambient defaults turn out to be needed, they can be added as a later layer below `$CAIRN_PATH` without breaking anything above.

### `CairnTarget` abstraction

Discovery returns a `CairnTarget` value, not a raw path. v0 only constructs `LocalPath` targets. Every cairn-touching command — `cairn validate`, `cairn status`, `cairn finding add`, the skills' file-writing logic, etc. — accepts a `CairnTarget` rather than a `Path`. When the MCP backend lands, an `MCPEndpoint` target slots in without rewriting call sites.

The v0 `LocalPath` interface is the minimum needed by current commands: `root_path()`, `read_file()`, `write_file()`, `git_commit()`. Concrete; no premature abstraction.

## Consequences

- **ADR-0005 is partially superseded.** Its discovery sketch (steps 1–4 in the B1 section) is replaced by this ADR. The B1-vs-B2-vs-B3 decision and the deferral framing remain in force; a forward-reference note added to ADR-0005.
- **US-P-10 is updated** (done in the same series as this ADR) to name the `cairn link` opt-in exception explicitly, so the prohibition on bootstrap-time project-repo writes isn't mis-read as forbidding all project-repo writes ever.
- **Three new CLI commands** land in Phase 2: `cairn link`, `cairn skills install`, `cairn skills uninstall`. A `.cairn` marker write is added to `cairn init` and a backfill to `cairn validate`.
- **No user-level config file**, no `~/.cairnrc`, no `~/.config/cairn/`. If those become necessary later, they can be added behind discovery step 2 (env var); for v0 they're absent.
- **MCP forward-compat is structural, not speculative.** The `CairnTarget` abstraction is the only MCP-aware code shipped in v0. No MCP server, client, schema, or wire format work happens under this ADR — only that the dispatch layer is in the right shape to accept one later.
- **Pre-existing cairns** (this repo's tests, the project's own bootstrap fixtures) need `.cairn` markers backfilled. `cairn init` becomes idempotent on existing cairn roots to handle this; `cairn validate` warns on missing markers with a one-command fix.
- **Trigger for revisiting**: usage data showing that the `cairn link` opt-in friction is the dominant onboarding blocker (suggesting we should automate pairing in some flow), or a concrete need that the `CairnTarget` abstraction doesn't accommodate.

## Implementation note — Stage 1 (shipped)

The first implementation pass shipped: the `.cairn` marker (a small TOML file with `name = "<project>"`), the cwd-walk update in `paths.is_cairn_root` (checks the marker first, with `state/collaborators.yaml` retained as a transitional fallback so pre-marker cairns remain discoverable), the `cairn init` idempotency path that backfills the marker on existing cairn roots, and a `cairn validate` warning that surfaces a missing marker with a one-line backfill command. The `cairn link` pointer file and the `cairn skills install` global-install remain as Stage 2 and Stage 3.

**`CairnTarget` was *not* introduced in Stage 1.** With only a single backend (`LocalPath`), the abstraction would be shape without value — every command would route through `target = resolve_cairn(); paths = target.paths` for no behavioral difference, in tension with this repo's "don't add abstractions beyond what the task requires" convention. The existing `CairnPaths` value returned by `resolve_cairn()` already serves the local case. The abstraction is deferred until a real second backend (likely MCP) drives it; at that point `resolve_cairn()` can be widened to return a `CairnTarget` union, with `LocalPath` wrapping today's `CairnPaths` and call sites that only need paths continuing to use the local view. The change will be mechanical but should ride with the actual MCP work, not precede it.
