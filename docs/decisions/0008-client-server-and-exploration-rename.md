# 0008 — Client/server access modes; rename cairn "branch" to "exploration"

## Context

Two pieces of long-running vocabulary in the Cairn codebase have caused recurring confusion in real UX testing:

**"Mode A" and "Mode B"** (introduced in ADR-0005) name access patterns by which Claude Code SessionStart hook fired. They are developer-facing labels: useful when reasoning about harness internals, opaque to a user who just wants to know "am I doing this right?" Real bootstrap sessions surfaced the cost — the agent confidently reported "this is Mode A" when in fact the session had been opened in the user's project repo, because the bootstrap doc's closing template told it to. Users (and agents) need labels that map onto mental models they already have.

**"Branch"** is overloaded. Git uses it to mean a parallel line of commits. Cairn uses it (today) to mean a tracked alternative line of project inquiry — materialized as a git branch in the cairn repo, an entry in `branches/README.md`, and a `branches/<name>.md` manifest. In a Mode B (client) session inside a project repo, "let's create a branch" reasonably means *either* the git branch the user expects from their normal workflow *or* the cairn-internal tracking concept. The agent has had to guess. In one observed case, it guessed the cairn meaning silently, when the user expected the git meaning.

ADR-0007 establishes "augmentation, not replacement" as a principle. That principle has direct vocabulary consequences: where Cairn introduces a concept that collides with a name the user already knows from their native tools, the user's existing meaning wins and the Cairn concept needs a different word.

This ADR resolves both issues together because they are deeply related — the rename only makes sense in light of the access-mode reframe, and the reframe makes the rename obvious.

## Decision

### Access modes: rename Mode A/B to server/client

- **Client mode** (formerly Mode B). The everyday case. The user is in their project's code repo, on a Zoom call, in a Slack thread, in any of the native channels where real work happens. An agent listens in that channel and writes structured notes into the cairn as a side effect. The cairn is a backend the agent calls into; the user need not perceive it. Local-filesystem transport is the v0 implementation; future MCP transport is the same mode with a different network shape — indistinguishable from the user's seat.

- **Server mode** (formerly Mode A). The maintenance / curation case. A user opens Claude Code inside the cairn directory to debrief deeply, restructure state, run reports, plan a meeting, or spelunk through accumulated history. The cairn's SessionStart hook fires and runs `cairn status` for context; bundled `SKILL.md` files at `<cairn>/skills/<name>/SKILL.md` are still procedural prose (real slash commands arrive with ADR-0006 Stage 3). Server mode is real and useful but expected to be a minority of total interactions.

The client/server framing dissolves three problems at once:

1. The local-vs-MCP asymmetry disappears: both are client mode with different transports.
2. The bootstrap-time overclaim is fixable with a crisp rule: mode is set the moment Claude Code launched, by the cwd it was launched from. No retroactive promotion via `cd`.
3. "Client mode is primary" inverts the priority signal: when a design or doc choice is in tension between client and server experience, client wins.

### Rename: cairn "branch" → "exploration"

Throughout Cairn's user-facing surface, the concept currently called "branch" becomes **exploration**:

| Surface | Before | After |
|---|---|---|
| CLI verb | `cairn branch start` / `cairn branch close` | `cairn exploration start` / `cairn exploration close` |
| Template directory | `branches/` | `explorations/` |
| Template index file | `branches/README.md` | `explorations/README.md` |
| Per-exploration manifest | `branches/<name>.md` | `explorations/<name>.md` |
| Bundled skills | `start-branch`, `resolve-branch` | `start-exploration`, `resolve-exploration` |
| Schema field on findings | `branch: str \| None` | `exploration: str \| None` |
| Architectural principle (ARCHITECTURE.md §4) | "Branches as first-class" | "Explorations as first-class" (softened — see Consequences) |

The underlying git mechanism does not change: a cairn exploration still corresponds to a git branch in the cairn repo. Cairn's user-facing language gets out of git's way; git keeps using "branch" for the git-level concept. The CLI's exploration commands continue to operate on a git branch under the hood, just named for what the user is doing rather than the mechanism.

### Default verb interpretation in client mode

Per the "augmentation, not replacement" principle (ADR-0007), the default interpretation of "let's create a branch" in a **client-mode session** (typically inside a project repo) is **a git branch in the project repo** — the git-native answer the user already expects from their normal workflow. A cairn exploration is the *explicit* alternative, offered when the discussion is rationale-heavy and would benefit from a tracked manifest (e.g., "let's record this as an exploration to compare against the main approach").

The `start-exploration` skill, post-rename, includes an explicit disambiguation step that surfaces both interpretations when ambiguous and never silently picks one.

### Pre-1.0 rename, no migration tooling

Cairn has no users in the wild today (stealth phase). The rename is mechanical and lands in one PR (PR R2). No backward compatibility shims, no migration helpers, no field aliases. Existing in-repo fixtures and the framework's own template are updated as part of the rename; a single ADR (this one) is the historical record that the prior names existed.

## Consequences

- **ADR-0005 is partially superseded.** Its "Mode A v0; Mode B deferred" commitment is reversed by this ADR: client mode (formerly Mode B) is now the primary surface; server mode (formerly Mode A) remains as the maintenance/curation path. The "Trigger for revisiting" criterion in ADR-0005 — *real users reporting two-session friction* — has been met by the StellaForge UX experiment. A forward-pointer note is added to ADR-0005.

- **ARCHITECTURE.md §Architectural Principles** gets a new principle (ADR-0007's "Augmentation, not replacement") and Principle #4 ("Branches as first-class") softens to acknowledge that cairn explorations are *optional augmentations*, not a required workflow step. A user who tracks every parallel line of inquiry via project-repo git branches and never creates a cairn exploration is using Cairn correctly.

- **`cairn validate` is unchanged.** No schema migration is needed beyond the field rename, because no existing cairns in the wild use the old name.

- **`AGENT-BOOTSTRAP.md` and bundled `SKILL.md` files need a substantive rewrite** to drop Mode A/B vocabulary, lead with client-mode as the default, and clarify when server mode is appropriate. Landed in PR R3 after this ADR is approved and the rename ships.

- **README.md and `docs/overview.html` / `docs/splash.html`** lead with the client-mode story under the augmentation principle, rather than the current "Mode A is the v0 working convention" framing.

- **The `branch` directory in any pre-rename fixture cairns** (notably the smoke-test infrastructure) needs to be regenerated by re-scaffolding from the post-rename template, not migrated. Same applies to any test fixtures that hardcode `branches/`.

- **Future MCP work** (Phase 3 / Phase 5) is now framed as a transport variant of client mode, not a new mode. The `CairnTarget` abstraction deferred in ADR-0006's Implementation Note remains deferred under the same logic — MCP arrives when the second backend has a concrete consumer, and at that point client mode picks up an `MCPEndpoint` transport alongside `LocalPath`.

- **Trigger for revisiting:** none anticipated for the renames. If real users adopt Cairn and then propose alternative vocabulary that lands better than "exploration," reconsider — but pre-users, no churn cost justifies preemptive uncertainty.
