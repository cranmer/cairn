# Scenario 1 — One user, many cairns

## What this scenario validates

A single user has multiple active research projects, each with its own cairn registered against one shared MCP server. The user opens parallel Claude Code sessions in different project repos and expects:

- Each session reaches **the correct cairn** without confusion.
- Cross-cairn write attempts (deliberate or accidental) are clearly resolved or refused.
- The `cairn` MCP parameter routing (per ADR-0010) does what its description claims — defaults to the only registered cairn when there's one, requires explicit naming when there are several.
- `cairn link --name <handle>` pairing actually translates into agent behavior — the agent in a paired project repo writes to that cairn without being told.
- The MCP server's `whoami` / `status` / `list_skills` calls return the right cairn-specific state.
- The user's mental model is stable: they don't have to repeatedly disambiguate, but when there *is* ambiguity, the surface communicates it clearly.

The scenario explicitly does **not** test concurrent writes to the *same* cairn — that's scenario 2.

## Companion user story

This is acceptance-test material for the existing **ADR-0010** ("Single MCP server, multiple cairns") plus the **US-P-12** project-repo pairing surface. A standalone user-story phrasing for the test scenario:

> **US-T-MC-1 (test scenario):** As a researcher running multiple cairn-equipped projects, I want my Claude Code sessions in any given project's repo to reach the right cairn automatically — no manual selection per command, no cross-talk, and clear errors if I attempt to operate on a cairn that isn't the one paired with my current working directory.

### Acceptance criteria

A1. With two cairns (`coral-bleach` and `lit-monitor`) registered in the same user-level registry, an agent session opened in the project repo paired with `coral-bleach` writes a finding via `add_finding(author, title, body)` — *no `cairn` parameter passed* — and the finding lands in `coral-bleach`'s `knowledge/findings/`, not `lit-monitor`'s. The single-cairn default must NOT apply here (two cairns are registered); the agent must determine which cairn from the `cairn.toml` at cwd's project repo root.

A2. The same agent, asked to log a finding to "the other project", correctly passes `cairn="lit-monitor"` (the other registered name) and the write lands in `lit-monitor`. The agent should reach for the explicit parameter; the orchestrator scoring this criterion checks that the cross-cairn write succeeded and landed in the right place.

A3. An agent attempting to write to a non-existent cairn (e.g., `cairn="ghost"`) gets a clear MCP error naming the registered cairns. The error message in the feedback should mention both `coral-bleach` and `lit-monitor`.

A4. `whoami(cairn="coral-bleach")` and `whoami(cairn="lit-monitor")` return different collaborator lists (the cairns have different collaborator entries pre-seeded). The agent's feedback should report that the two whoami calls returned distinct results, not identical.

A5. `status` called with each cairn name in turn returns cairn-specific state — counts of decisions, findings, recent activity, etc. — not a merged view.

A6. The agent reports no instances of "I'm confused which cairn this is for" in its feedback (i.e., its mental model stayed consistent across the run).

### Disqualifying observations (would fail this scenario)

- A write going to the wrong cairn (silent mis-routing).
- The agent asking the user for the cairn name when `cairn.toml` already pairs the project repo with one.
- `whoami` or `status` returning the wrong cairn's data.
- The agent attempting to merge state across cairns (e.g., asking "which cairn has more findings" and reading both — that's fine; *writing* to the wrong one based on the answer is not).
- The MCP server crashing or returning malformed responses under any of the above.

## Sub-agent recipe

Use **2 sub-agents launched in parallel** (one Agent tool invocation per sub-agent, both with `run_in_background=true` for genuine parallelism; the orchestrator collects when both complete).

### Sub-agent A — "Kyle working on coral-bleach"

**Working directory:** `<run-tmpdir>/projects/coral-bleach/` (the project repo paired with cairn `coral-bleach`).
**Identity:** collaborator id `kyle` (registered in both cairns; this matters for A4).
**Environment:** `XDG_CONFIG_HOME` set to a shared tmpdir so both sub-agents see the same MCP registry. Both cairns (`coral-bleach`, `lit-monitor`) are registered. The MCP server is configured for stdio transport (no HTTP needed for this scenario).
**Work backlog:** see `fixtures/coral-bleach/work-backlog.md` — three tasks:
  1. Log a finding ("coral cover dropped to 30% in 2024 transects") to the project this repo is paired with. *No `cairn` parameter*.
  2. Record a decision about a sampling protocol change, attributed to `kyle`.
  3. Cross-check: ask the agent to also log a quick finding to `lit-monitor` ("the new paper on bleaching is worth tracking") — this exercises explicit cross-cairn write.

**Prompt frame** (paraphrase the agent will receive):

> *You are Kyle, working on the coral-bleach project. You're in `<project-repo-path>`, which is paired with a cairn named `coral-bleach`. You have access to a separately-registered cairn `lit-monitor` for the literature-tracking project. Walk through the tasks in `work-backlog.md` in order. For each task, use the MCP tools rather than the CLI. When the task says "to the project this repo is paired with", do not pass a `cairn` parameter — the project's `cairn.toml` should resolve it. When the task names a different cairn, pass the `cairn` parameter explicitly. At the end, fill in the feedback template at `<feedback-path>`.*

### Sub-agent B — "Kyle working on lit-monitor"

Mirror of A, but rooted in `<run-tmpdir>/projects/lit-monitor/` and its own work backlog. Cross-write task targets `coral-bleach`.

The two sub-agents run **concurrently** to exercise parallel session behavior — they share the registry and the MCP server but operate on different cairns.

## What the orchestrator (me) does

1. Build the run tmpdir, the two cairns, the two project repos, the shared MCP-registry config.
2. Confirm both cairns scaffold cleanly and `cairn registered` lists both.
3. Confirm `cairn link --name <cairn> <project-repo>` writes the right `cairn.toml` in each project repo.
4. Launch sub-agents A and B in parallel via the Agent tool (background mode).
5. When both complete, read their feedback files.
6. Score against A1–A6 above; collect anything in the "additional observations" section of their feedback.
7. Write the per-scenario section of `runs/<timestamp>/SYNTHESIS.md`.

## Out of scope for this scenario

- **HTTP transport.** Scenario 1 uses stdio. (Scenario 2 exercises HTTP.)
- **Concurrent writes to the same cairn.** That's scenario 2.
- **Cross-machine setup.** Both sub-agents run on the same machine, against the same MCP registry. Multi-machine setup is a follow-up if HTTP+registry-sync behaviors need their own scenario.
- **Conflict scenarios** — e.g., two parallel writes to *the same* cairn from cross-cairn workers. Theoretically possible if the cross-write timing aligns, but the workload is small enough that it's unlikely. If it happens we capture it; we don't drive it.
