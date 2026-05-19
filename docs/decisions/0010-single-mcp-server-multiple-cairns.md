# 0010 — Single MCP server, multiple cairns

## Context

ADR-0009 specified a per-cairn MCP server: each cairn gets its own `cairn mcp` subprocess, registered separately in the client's MCP config. During the Tier-1 implementation walkthrough, a deployment-overhead concern surfaced before any code shipped: for a researcher with N cairns (one per project), Claude Code would spawn N Python subprocesses on every session start. The per-process cold-start cost is real (~100–300 ms each), the MCP-config bloat is noticeable, and adding a new project means editing the client config. The shape doesn't scale gracefully past 2–3 cairns.

The natural alternative is the **wandb model**: one client, one server, many projects, with project name as an API parameter. wandb's `wandb.init(project="my-project")` pattern is widely understood and works at single-digit project counts as easily as at thousands. The same pattern fits MCP cleanly — every tool takes a `cairn` parameter that names which cairn to operate on, the user's MCP config has one entry, and registering a new cairn doesn't require client-config changes.

The cost of staying with per-cairn-server isn't catastrophic (it works), but the cost of switching is small (no users yet, the work hasn't started). Better to land on the right shape now than to refactor after the first deployed users.

## Decision

### One MCP server per user, many cairns

A single `cairn mcp` subprocess serves all of the user's registered cairns. The set of cairns is read from a user-level registry file at server startup; the registry maps a short *cairn name* (used as an API parameter) to a filesystem path.

```toml
# ~/.config/cairn/server.toml
[cairns]
stellaforge = "/Users/cranmer/projects/stellaforge-cairn"
nanogpt     = "/Users/cranmer/projects/nanogpt-cairn"
```

Cairn names are kebab-case, must be unique within the registry, and have no required relationship to the on-disk directory name (the registry is the source of truth for what the cairn is *called* via MCP).

### Every MCP tool takes a `cairn` parameter

Both read and write tools accept `cairn: str` as their first parameter, naming the target cairn. The server resolves the name against the registry, validates that the path is a cairn root (has `.cairn` marker or legacy fallback per ADR-0006), and then dispatches the rest of the tool's logic against that cairn.

**Single-cairn convenience.** When the registry has exactly one entry, the `cairn` parameter defaults to it. Single-cairn users never have to pass it. As soon as a second cairn is registered, the parameter becomes required and an omitted `cairn` raises a clear error listing the registered names.

The convenience-by-default is a kindness for the single-cairn case (which is the common case for one-person teams or first-time users), not a permanent contract. Users who want to make the cairn explicit always-on can pass it always.

### New CLI commands

Two new commands manage the registry and project-repo pairing:

| Command | Purpose |
|---|---|
| `cairn register <name> <path>` | Add or update a cairn in the user-level registry. Validates that `<path>` is a cairn root before writing. |
| `cairn unregister <name>` | Remove an entry from the registry. Does not touch the cairn itself. |
| `cairn registered` | List currently registered cairns (name + path). |

`cairn link <project-repo>` (the Stage 2 / ADR-0006 command) continues to write the project-repo's `cairn.toml`. It picks up the `name` field so the project repo records which registered cairn it pairs with, not just the path:

```toml
# <project-repo>/cairn.toml
[cairn]
name = "stellaforge"
# Optional fallback for when the user hasn't registered an MCP server:
# path = "../stellaforge-cairn"
```

An agent in a project repo reads `cairn.toml` to learn the cairn's name and includes that name on every MCP tool call.

### Convenience launcher: `cairn mcp --cairn-path <path>`

For the simplest possible "I just want to try this" path, `cairn mcp` accepts an inline `--cairn-path <path>` flag that registers a single ad-hoc cairn (name defaults to the directory basename minus a `-cairn` suffix) without touching the user-level registry. The server still serves it through the same tool surface; the `cairn` parameter defaults to the ad-hoc name.

This is for trying things out and for CI. Real use registers cairns explicitly.

### Identity and attribution unchanged

Per-call `author` validation against `state/collaborators.yaml` (ADR-0009's decision) is unaffected by this revision. The author lookup happens per-cairn — adding a collaborator in one cairn does not authorize that id in another.

### Registry file format

Plain TOML, mirroring `cairn.toml`'s shape. No schema versioning in v0; the file is two-section and small enough that future migrations are trivial. Validation: the server refuses to start if the file is unparseable, with a clear error pointing at the offending line.

## Consequences

- **ADR-0009 is partially superseded.** Specifically:
  - The "Configuration" section's per-cairn `mcpServers` example is replaced by a single `cairn` entry. Users register multiple cairns via `cairn register`, not via multiple MCP server entries in Claude Code's config.
  - The "Tool surface" section's tool signatures gain a leading `cairn: str` parameter.
  - The "Minimum viable surface for UX testing" tool list is unchanged in size — just adds the parameter.
  - A forward-pointer note added to ADR-0009 at its top, marking these sections as superseded by ADR-0010.

- **The MCP client (Claude Code) config simplifies to a single entry**, regardless of how many cairns the user has:

  ```json
  {
    "mcpServers": {
      "cairn": {
        "command": "cairn",
        "args": ["mcp"]
      }
    }
  }
  ```

  A user with 5 cairns has the same config as a user with 1. Adding a 6th cairn doesn't touch the client config.

- **Deployment overhead drops from O(N) to O(1)** in number of cairns. One Python subprocess per session start.

- **Cross-cairn queries become possible** in a follow-up tool (e.g., `find_similar_findings_across_cairns(query, limit)`). Out of scope for v0 — flagged as a natural extension.

- **`cairn.toml`'s schema** gains `name` alongside `path` / `endpoint`. The agent in a Mode B / client-mode session reads `name` and passes it on every MCP tool call.

- **A user-level config file** (`~/.config/cairn/server.toml`) now exists. This is a slight departure from earlier statements in ADR-0006's Implementation Note ("No user-level config file"); the trade is intentional. The registry is small, has obvious format, and exists only when the user runs an MCP server — it does not affect direct-CLI users. Updated in ADR-0006's Implementation Note alongside this PR.

- **Phase 5 (AI collaborator runtime) gets simpler.** A scheduled literature-monitor agent talking to multiple cairns becomes one MCP connection, not N. The runtime doesn't need to manage per-cairn connection lifecycles.

- **Trigger for revisiting:** if the registry file grows beyond ~20 entries for any individual user (suggests a separate cairn-discovery mechanism — maybe directory-scan), or if cross-cairn permission models surface (some cairns should be read-only for some clients), or if remote MCP transport (HTTP, deferred from ADR-0009) needs per-cairn authentication that doesn't fit at the server level.
