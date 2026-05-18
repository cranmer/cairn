# 0009 — MCP server design

## Context

ADR-0008 reframed Cairn's access modes around client/server vocabulary and named client mode (formerly Mode B) as the primary surface — most cairn interactions happen from inside a project repo, a meeting transcript, a Slack thread, or wherever real work happens, with the cairn as a transparent backend the agent calls into. Stage 2 of the discovery/pairing work (ADR-0006) gives that mode a local-filesystem transport: a `cairn.toml` in the project repo points at a sibling cairn directory, and the agent dispatches CLI commands against it without `cd`.

The **MCP transport** is the next step. It collapses the remaining asymmetry between "cairn lives on my disk" and "cairn lives somewhere else, possibly shared by collaborators, possibly hosted by a research group" — same client UX, different network shape. With MCP available, an agent in any Claude Code session can issue cairn read/write operations as MCP tool calls without needing the cairn checked out locally, without `cd`-ing, and without per-session bootstrapping. The user-research signal motivating this is direct: real UX testing of client mode against the StellaForge code repo surfaced that the `cd`-and-shell-out pattern still feels like a workaround, even with `cairn.toml`. MCP is what makes the substrate genuinely invisible.

This ADR captures the design decisions for the v0 MCP server — enough to drive an implementation that can be UX-tested against real project work without overcommitting to specifics that need user signal to settle. Tool inventory, identity model, transport, and the relationship to the existing CLI are decided here. Concrete API shapes (parameter types, return schemas) are sketched and may iterate during implementation.

## Decision

### Role: a derived, substrate-faithful layer

The MCP server is a **derived view** over the cairn substrate. Per ARCHITECTURE.md Principle #2 (the repository is the source of truth) and the "substrate-as-specification" commitment:

- The MCP server **does not own state**. Every byte it returns is reproducible from the cairn's files on disk.
- Every write the MCP server accepts is materialized as the corresponding file mutation + git commit, identical in shape to what a CLI invocation would produce. The MCP server's writes are not a parallel write path; they go through the same Python functions the CLI calls.
- The MCP server can be stopped, deleted, and rebuilt from the repo. The repo survives it.
- Cached / derived data (vector indices, computed summaries) is rebuildable.

**Test of compliance:** if you delete the MCP server's working state and restart it pointing at the same cairn, the observable behavior should be identical.

### Transport: stdio for v0; HTTP later

V0 ships an **stdio transport** — the MCP server runs as a subprocess of the client (Claude Code), communicating over stdin/stdout with the standard MCP JSON-RPC framing. This matches how Claude Code natively expects to launch MCP servers, requires no networking config, and is the simplest possible deployment. Concretely: a `cairn mcp` subcommand on the existing `cairn` CLI starts the server; Claude Code's MCP config points at it.

The HTTP / WebSocket transports come later, with the same tool surface. Triggers for HTTP:

- Multi-collaborator sharing (one MCP server, many sessions hitting it).
- Hosting the cairn on a server (the cairn's files live on a remote host the user doesn't have checked out).
- Long-running background agents (literature monitor, etc.) writing into the cairn out-of-band.

Stdio is sufficient for the immediate UX-testing target (single-user, single-machine, cairn checked out locally, agent in any session).

### Identity model: explicit `author` per write, validated against `state/collaborators.yaml`

Every write tool takes an explicit `author` parameter (a collaborator id). The MCP server validates it against `state/collaborators.yaml` and refuses the call if the id is unknown — same behavior as the CLI today. No silent default-to-anyone.

**Why explicit-per-call rather than session-scoped or server-scoped:** Cairn's "attribution end-to-end" invariant requires every write to record the actor. A session-scoped identity (set once at session start) is hard to verify when an agent is doing autonomous work; a server-scoped identity (the MCP server has one identity for all writes) conflates multiple users and degrades attribution. Explicit-per-call is more verbose at the wire level but preserves the invariant.

For human users in a Claude Code session, the agent reads its initial identity once (from the bundled `orient` skill at session start) and passes it on every write tool call without bothering the user. For AI collaborators (Phase 5), the runtime configures the collaborator id at agent start and the agent uses it for the session's lifetime.

A `cairn_whoami()` read tool lets the agent confirm which identity the MCP server would accept for the calling client (useful for client-side validation and for the orient skill).

### Tool surface: thin wrapper over the existing Python API

The MCP server is a thin layer over `src/cairn/`'s existing functions. For each cairn CLI subcommand, there's an MCP tool that calls the same underlying function. The MCP server does **not** shell out to the CLI — it imports the Python package directly and calls the functions in-process. Same code paths, different framing.

This has two important consequences:

1. **The tool surface stays in sync with the CLI for free.** New CLI commands gain MCP tools by writing a thin handler; bugs fixed in one path are fixed in both.
2. **No subprocess overhead per call.** Tool calls are fast (Python function invocations, not process spawns).

#### Read tools (v0)

| Tool | Purpose | Returns |
|---|---|---|
| `cairn_status` | Compact project-state summary (mirrors `cairn status --json`) | structured `StatusSnapshot` |
| `cairn_whoami` | Identity the MCP server resolves for the calling client | `{collaborator_id, name, email}` or `null` |
| `cairn_get_collaborators` | List collaborators | list of Collaborator records |
| `cairn_get_decisions` | List decisions, optionally filtered (`since`, `author`, `related_to_id`) | list of Decision records |
| `cairn_get_open_questions` | List open questions | list of OpenQuestion records |
| `cairn_get_action_items` | List action items, optionally filtered (`assignee`, `status`, `due_before`) | list of ActionItem records |
| `cairn_get_goals` | List goals | list of Goal records |
| `cairn_get_findings` | List findings (returns summaries; fetch full content separately) | list of `{path, date, title, slug, author, related, exploration}` |
| `cairn_get_finding_content` | Return a finding's full markdown body + frontmatter by path | `{frontmatter, body}` |
| `cairn_get_meetings` | List meeting transcripts (path, date, title) | list of meeting summaries |
| `cairn_get_explorations` | List active/closed explorations (mirrors `explorations/README.md`) | list of `{name, owner, opened, status, ...}` |
| `cairn_get_exploration_manifest` | Read a specific exploration's manifest | manifest markdown |
| `cairn_get_project_md` | Return `PROJECT.md` content | string |
| `cairn_search` | Cross-cutting text search across the cairn | list of hits with kind/path/snippet |

`cairn_search` is initially a substring search across the substrate; semantic search (vector index) is a follow-on that doesn't affect the tool's signature. Same tool, smarter backend over time.

#### Write tools (v0)

| Tool | Wraps CLI | Notes |
|---|---|---|
| `cairn_add_decision` | `cairn decision add` | Requires `author`, `text`; optional `context`, `related` |
| `cairn_add_finding` | `cairn finding add` | Requires `author`, `title`, `body`; optional `related`, `slug`, `commit` (default true) |
| `cairn_add_action` | `cairn action add` | Requires `text`, `assignee`; optional `due_date`, `related` |
| `cairn_complete_action` | `cairn action complete` | Requires `id`, `by` |
| `cairn_add_open_question` | (no current CLI; ships alongside) | Adds an open question; same shape as decisions |
| `cairn_add_collaborator` | `cairn collaborator add` | Identity gate: only an existing collaborator can add another (or it's the first one) |
| `cairn_start_exploration` | `cairn exploration start` | Requires `description`, `as_id` |
| `cairn_close_exploration` | `cairn exploration close` | Requires `name`, `status`, `reason`, `closed_by` |

Every write tool returns the same shape: `{ok: bool, id?: str, path?: str, commit_sha?: str, message?: str}`. On error, the response includes a clear human-readable message and (where applicable) a machine-readable error code. The MCP server never silently corrupts state; failures are surfaced verbatim.

#### Notable omissions in v0

- **No `cairn_init` tool.** Scaffolding a new cairn is a server-mode action (you have to be standing in a directory to create one); not a client-mode concern. Use the CLI directly for init.
- **No `cairn_validate` tool.** Validation is a curation activity, more natural in server mode where the user is reviewing state. Future addition if UX testing reveals client-mode need.
- **No batch tools.** Each write is one call. If batched writes turn out to be the dominant client pattern, a `cairn_batch(writes=[...])` tool can be added later.

### Relationship to ADR-0006's `CairnTarget` abstraction

ADR-0006 deferred the `CairnTarget` abstraction until a second backend existed. **MCP is the second backend.** The CLI's discovery layer (cwd-walk → `.cairn` marker / `cairn.toml`) widens:

```
cairn.toml shapes:

[cairn]                              [cairn]
path = "../foo-cairn"                endpoint = "stdio:cairn mcp"
                                     # or in future:
                                     # endpoint = "https://cairn.example.org/projects/foo"
```

`resolve_cairn()` returns a `CairnTarget` union:

- `LocalPath(root)` for filesystem-resident cairns (today's behavior).
- `MCPEndpoint(url, transport)` for cairn-as-a-service.

CLI commands that only need read/write paths against the cairn dispatch on the target type. Concretely:

- `cairn decision add` with a `LocalPath` target → today's code path.
- `cairn decision add` with an `MCPEndpoint` target → opens an MCP client, calls `cairn_add_decision`, returns the result.

The agent in a Claude Code session has two paths: (a) call cairn CLI commands (which dispatch through `CairnTarget`), or (b) call MCP tools directly. Both paths converge in the same Python functions. The CLI-via-MCP path is what lets users keep `cairn …` muscle memory while operating against remote cairns.

The `CairnTarget` abstraction ships *with* the MCP server in this ADR's implementation, not before. The pairing remains: don't introduce abstractions without a second consumer.

### Configuration

The MCP server reads its target cairn from one of (in order):

1. The `--cairn-path` CLI flag passed to `cairn mcp`.
2. The `CAIRN_PATH` env var.
3. The cwd-walk from where `cairn mcp` was launched.

For Claude Code's MCP config, the canonical pattern is:

```json
{
  "mcpServers": {
    "cairn-myproject": {
      "command": "cairn",
      "args": ["mcp", "--cairn-path", "/Users/kyle/projects/myproject-cairn"]
    }
  }
}
```

One MCP server per cairn. Users with multiple projects register multiple `cairn-<name>` MCP servers in their Claude Code config; the tool names are not prefixed with the cairn name (the namespace is the server itself), so tool names stay short and `cairn_status` etc. work uniformly.

### Phase 3 scope vs Phase 5

This ADR is the Phase 3 work — the MCP server interface, the stdio transport, the v0 tool surface. **Phase 5 (AI collaborator runtime)** is unattended-AI work on top of the MCP server: scheduling (literature monitor runs weekly), structured permission model (which AI collaborators can write what), review queues (AI writes land on a dedicated git branch for human promotion). Phase 5 needs the MCP server to exist but does not add new tools to it — it adds *callers* of it.

This scoping keeps Phase 3 focused on the interface, which is what the user is eager to UX-test. Permissions and review queues belong with Phase 5 when the use cases are concrete.

### Implementation language and dependencies

- Python (matches the rest of the package).
- The official Anthropic Python MCP SDK (`mcp` package on PyPI). The `cairn mcp` subcommand uses it to handle JSON-RPC framing, lifecycle, and the stdio transport.
- Pydantic v2 (already a dep) for tool parameter/return schemas. The same models that validate state files double as MCP tool I/O schemas.

A new `cairn[mcp]` install extra carries the MCP SDK dependency; the base package works without it, and `cairn mcp` raises a clear "install with `pip install cairn[mcp]`" error if invoked without the extra installed.

### Minimum viable surface for UX testing

The smallest useful subset that exercises the client-mode story end-to-end against a real project repo:

**Tier 1 (must-have for first UX test):**
- `cairn_whoami`
- `cairn_status`
- `cairn_add_decision`
- `cairn_add_finding`
- `cairn_add_action`
- `cairn_complete_action`
- `cairn_get_open_questions`
- `cairn_get_action_items`

**Tier 2 (light extensions, expected immediately after):**
- `cairn_get_decisions`, `cairn_get_findings`, `cairn_get_finding_content`
- `cairn_add_open_question`
- `cairn_start_exploration`, `cairn_close_exploration`, `cairn_get_explorations`
- `cairn_search`

**Tier 3 (round out the surface):**
- Remaining read tools (collaborators, goals, meetings, project_md, manifest).
- `cairn_add_collaborator`.

Shipping Tier 1 + Tier 2 against Claude Code is the realistic v0 milestone for "UX-test with an MCP server."

## Consequences

- **A new top-level CLI subcommand `cairn mcp` is added** to the existing Typer app. Implementation lives in `src/cairn/mcp/` as its own subpackage. Imports from `cairn.mcp` are guarded so the package still works without the `[mcp]` extra installed.

- **The `CairnTarget` abstraction (deferred in ADR-0006) ships with the MCP work.** The CLI's discovery layer widens to return `LocalPath | MCPEndpoint`. Existing call sites that take a `CairnPaths` keep working unchanged; only commands that newly need to dispatch through a transport pick up the union.

- **`cairn.toml` schema grows the `endpoint` key**, mutually exclusive with `path`. Validation enforces exactly one of the two. The schema change is documented in ADR-0006's Implementation Note (forward-pointer).

- **A new optional dependency** (the `mcp` Python SDK) and a `cairn[mcp]` install extra. The base install footprint is unchanged for users who don't run an MCP server.

- **Phase 3 of the roadmap (MCP server alongside the repo) gains a concrete spec.** Phase 5 (AI collaborator runtime) layers on top: scheduling, permissions, review queues are Phase 5 concerns and do not extend the MCP tool surface defined here.

- **Per-call attribution is preserved end-to-end.** Every MCP write tool requires an explicit `author` field, validated against `state/collaborators.yaml`. The CLI's existing behavior carries over unchanged.

- **The orient skill picks up an MCP awareness step** (specified in PR R3): when running in a client-mode session with a cairn paired via MCP, the agent's orientation pulls from `cairn_status` instead of reading `cairn status` from a local checkout. Same information, different transport.

- **No proprietary tools or services are required.** The MCP server is one more Python subpackage of the existing CLI; users running cairn locally get the option of "add an MCP server" without changing how their cairn is stored, versioned, or shared.

- **Trigger for revisiting:** UX testing reveals that explicit-per-call `author` is too verbose for real agent loops (consider a session-scoped identity with periodic re-validation); or, an unanticipated tool need surfaces that doesn't fit the thin-wrapper-over-CLI model (the model is the constraint to break, not the surface to expand piecemeal); or, multi-collaborator concurrent-write scenarios surface conflicts the local CLI doesn't currently handle.

## Out of scope for this ADR

- **Semantic search index.** `cairn_search` ships with substring search; vector-index-backed semantic search is a follow-up that doesn't change the tool surface.
- **Permission model.** Phase 5 territory; explicit-per-call `author` is the v0 enforcement and is sufficient until automated AI collaborators are running unattended.
- **Caching strategy.** v0 reads from disk on every call; if performance becomes an issue, an in-memory cache invalidated by git HEAD changes is the natural next step.
- **Multi-cairn cross-references.** A user with several cairns (one per project) registers each as a separate MCP server in Claude Code's config. Cross-cairn queries are out of scope until the use case is concrete.
- **Authentication beyond `state/collaborators.yaml` lookup.** Remote-transport authentication (when HTTP / WebSocket land) is a future ADR. For stdio, the process boundary is the trust boundary.
