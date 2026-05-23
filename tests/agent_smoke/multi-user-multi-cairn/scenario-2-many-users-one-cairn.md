# Scenario 2 — Many users, one cairn

## What this scenario validates

A single shared cairn is written to concurrently by **three distinct human users**, each emulated by an isolated sub-agent. The MCP server is configured for **HTTP transport** (the deployment topology the multi-user case actually demands; stdio would force per-user subprocesses). Each user has their own identity in `state/collaborators.yaml`, their own bearer token (since US-P-13's credential model is per-server-not-per-user, we share the token but vary the `author` parameter — this is the documented "attribution, not authentication" posture from Issue #22).

The scenario validates:

- **Attribution correctness.** Each user's writes land in the cairn with that user's `author` field, never silently re-attributed.
- **Concurrent-write safety.** Three users writing decisions / findings / actions to the same state files in rapid succession do not lose writes, corrupt YAML, or produce inconsistent state.
- **Identity resolution.** `whoami` called from each sub-agent's session returns *that user's* suggested id (where applicable), not a globally-shared one — the suggestion logic walks each session's local git config.
- **`bootstrap_from_repo`'s ambiguous-authorship pattern** (the `type="unknown"` / `repo-history` collaborator from earlier in the cairn iteration history) works in a real multi-author context: a sub-agent acting as the orchestrator can write findings attributed to `repo-history` and later sub-agents acting as humans can write decisions attributed to themselves, all referencing each other's IDs correctly via `related`.
- **Cross-user references.** A decision authored by user A that references an open question raised by user B resolves correctly (`related` validates against the cairn-wide id index, not per-user).
- **No mis-routing.** No user accidentally writes as another user (which would be an attribution bug, not a security one — see scope notes).

## Companion user story

Acceptance-test material for **US-P-11** (HTTP transport), **US-P-13** (CLI remote dispatch), the multi-user implications of **ADR-0009** (MCP server design), and the per-call `author` validation that's been Cairn's posture since v0.

> **US-T-MC-2 (test scenario):** As a research group sharing a single cairn over HTTP, we want each collaborator's Claude Code session to write to the cairn under their own identity, with attribution preserved, no cross-user mis-routing, and clean concurrent-write behavior when more than one of us is capturing at the same time.

### Acceptance criteria

B1. **Attribution.** With three users (`alex`, `morgan`, `sam`) registered as collaborators in the shared cairn, parallel writes from three sub-agents produce entries whose `author` (decisions, findings) or `assignee` / `raised_by` fields exactly match the sub-agent that issued the write. No write ends up attributed to a different user.

B2. **No data loss.** After all sub-agents finish, the total count of decisions / findings / actions / open-questions in the cairn equals the sum of writes attempted across all sub-agents. (Each sub-agent's feedback reports how many of each type it attempted; the orchestrator sums and compares.)

B3. **Concurrent-write safety.** No state-file YAML is corrupted. `cairn validate` exits 0 after the run. No partial writes (e.g., a decisions.yaml that has a half-written entry or a duplicate id).

B4. **ID monotonicity.** Decision IDs are unique and dense (`D-001` through `D-N` with no gaps), even under concurrent allocation by three writers. Same for actions and open questions. (Gaps would indicate a write that allocated an ID and then failed to land.)

B5. **Cross-user references.** A decision authored by `alex` that lists `Q-002` (raised by `morgan`) in its `related` field successfully validates server-side. The `related` validation must resolve against cairn-wide IDs, not be confused by parallelism.

B6. **`whoami` discrimination.** Each sub-agent's `whoami()` call returns metadata reflecting that sub-agent's git identity — different `git_email` per agent, different `suggested_id` per agent — *not* a single shared identity bleeding across the run. This tests that `whoami`'s git-config probing happens in the calling process's environment, not the server's.

B7. **No agent-posture violations under concurrency.** The agents should not get confused about "who they are" mid-run. Each sub-agent's feedback should report a consistent identity throughout — no instances of "I think I'm Alex but the writes are being attributed to Morgan" type confusion.

B8. **HTTP transport stays up.** No 502s, no connection resets, no half-completed-and-retried writes producing duplicates. If the HTTP server crashes, the test fails regardless of other criteria.

### Disqualifying observations

- A write attributed to the wrong user (e.g., `alex`'s sub-agent issues `add_decision(author="alex", ...)` and the file shows `author: morgan`).
- A duplicate entity ID (`D-007` appearing twice from concurrent allocators).
- A YAML parse error in any state file after the run.
- `cairn validate` exiting non-zero with broken cross-references.
- The MCP server returning HTTP 500 / connection-reset / timeout under the modest concurrency this scenario applies (3 sub-agents, maybe ~30 writes total).

## Sub-agent recipe

Use **3 sub-agents launched in parallel**:

- **Alex** — methods lead. Identity: `alex` in the shared cairn. Workload weighted toward decisions and actions.
- **Morgan** — analysis. Identity: `morgan`. Workload weighted toward findings and open questions.
- **Sam** — writeup. Identity: `sam`. Workload weighted toward decisions that *reference* Morgan's findings and Alex's earlier decisions (the cross-user-reference acceptance test).

Each sub-agent's environment:

- A unique `git config user.email` (Alex: `alex@example.com`; Morgan: `morgan@example.com`; Sam: `sam@example.com`) so `whoami`'s suggestion logic has something to discriminate on.
- Shared bearer token (`CAIRN_BEARER_TOKEN=test-shared-token`) — this is the documented "attribution, not authentication" model. The token authorizes the connection; the `author` parameter on each write claims the identity. The test is whether the *honest* claim is preserved correctly, not whether dishonest claims are blocked.
- Each sub-agent works in its own tmpdir (a project repo paired with the shared cairn via `cairn.toml` with `endpoint = "http://127.0.0.1:<port>"` and `name = "shared-physics-paper"`).
- The shared cairn `shared-physics-paper` is registered in the MCP server's registry and the HTTP server is started before sub-agents launch.

### Per-sub-agent prompt frame

> *You are <NAME>, a contributor to the shared-physics-paper project. You're in `<project-repo-path>`, which is paired with the cairn `shared-physics-paper` over HTTP. Your collaborator id in that cairn is `<id>`. Read your work backlog at `<backlog-path>` and walk through the tasks in order. For every write, you must pass your own `author` (or `raised_by` / `assignee` / `by`) parameter naming `<id>`. For tasks that reference earlier entries (decisions or questions raised by Alex / Morgan / Sam), use the explicit `related` parameter with the entity IDs the backlog names. When done, fill in the feedback template at `<feedback-path>`.*

### Concurrency expectations

The orchestrator launches all three sub-agents within ~1 second of each other (parallel Agent tool calls in a single message). Each runs to completion independently. The HTTP server stays up throughout. Because Claude-Agent-style sub-agents have non-trivial per-tool-call latency, the actual write concurrency is **soft** — there *will* be interleaving but not microsecond-tight races. This is realistic for the deployment topology the scenario emulates (a research group whose members work in parallel sessions, not a load-test farm).

If we need tighter concurrency than the soft interleaving naturally produces, the orchestrator can post-test by scripting direct MCP calls in tight loops — that's an optional extension, not part of the base scenario.

## What the orchestrator (me) does

1. Build the run tmpdir.
2. Scaffold the `shared-physics-paper` cairn. Pre-register all three collaborators (`alex`, `morgan`, `sam`) via `cairn collaborator add` with their respective emails and roles. Also register `repo-history` (`type="unknown"`) for the ambiguous-authorship cross-check (see B5 prereq).
3. Start the cairn MCP server in HTTP mode: `cairn mcp --transport streamable-http --host 127.0.0.1 --port <port>`. Background.
4. For each sub-agent, build their tmpdir project repo, write a `cairn.toml` with `endpoint` + `name = "shared-physics-paper"`, and stage their work backlog.
5. Launch all three sub-agents in parallel (background Agent calls).
6. When all three complete, kill the HTTP server.
7. Run `cairn validate` against the cairn → must exit 0 (criterion B3).
8. Read the cairn's state files; cross-check counts and attribution against each sub-agent's feedback report (criteria B1, B2, B4, B5).
9. Score each criterion; write per-scenario section of `SYNTHESIS.md`.

## Out of scope

- **Authentication binding.** Issue #22 was explicit: attribution, not authentication. We don't test "what if Alex's sub-agent tries to claim it's Morgan." That's a real concern for production deployments but it's a future ADR.
- **Cross-machine deployment.** Both the MCP server and all sub-agents run on the same machine. Network-mediated failures (loss, partition, replay) are out of scope; HTTP loopback is reliable enough that they shouldn't surface naturally.
- **Long-running sessions.** Each sub-agent finishes in minutes. Session keep-alive, mid-session credential rotation, long-poll behaviors aren't exercised.
- **High concurrency.** Three users is enough for the realistic group-research deployment. If the test exposes concurrency issues even at three, that's signal; if everything passes at three, we believe ten is fine without testing it.
- **Reads-from-CLI.** Per US-P-13, CLI reads in remote mode are out of scope for the surface shipped in PR #25. This scenario respects that — sub-agents write via MCP and read either via MCP tools or by inspecting their own write outputs.
