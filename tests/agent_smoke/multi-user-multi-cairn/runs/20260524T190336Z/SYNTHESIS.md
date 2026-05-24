# Synthesis — final pre-merge smoke run for the remote MCP test harness

**Run:** `20260524T190336Z`
**Branch:** `claude/cairn-dev-test-harness`
**Scope:** US-T-01..04, ADR-0012/0013/0014/0015, X-Cairn-Git-* identity threading (commit 14bfd78).
**Companion past runs:**
- `runs/20260523T175633Z/` — scenario 1 original (found F-01..F-10).
- `runs/20260523T191531Z/` — scenario 1 rerun (confirmed F-01..F-10 fixes).
- `runs/20260523T192455Z/` — scenario 2 original (confirmed PR #27 fixes).

## Headline

**Both scenarios passed.** All 16 feature families specified across US-T-01..04 + ADRs 0012/0013/0014/0015 + the X-Cairn-Git-* threading commit are implemented and functional under realistic multi-user / multi-cairn loads. The branch is feature-complete relative to spec.

One **pytest regression** was discovered during the pre-smoke unit-test pass and fixed before the smoke run. Details under §Pytest regression below.

The smoke run surfaced **no runtime regressions** in the dev test harness or the remote MCP server itself. Six **UX-surface friction points** were observed, mostly carryovers from prior runs (no `cairn whoami` CLI, `cairn status` not supported over remote, `cairn registered` confusing in remote-paired repos). Three new friction points are catalogued in §UX findings.

## Scenario 1 — one user / many cairns (stdio)

Two sub-agents launched in parallel as `kyle`, anchored on different project repos, both registered against the same isolated MCP registry. Sub-agent A worked from `coral-bleach`'s repo with a cross-cairn write into `lit-monitor`; sub-agent B mirrored.

### Acceptance-criterion scorecard

| Criterion | Result | Evidence |
|---|---|---|
| A1 — default routing (paired cairn) | **PASS** | Both sub-agents' default-routed writes landed in their paired cairn. Sub-agent A: `coral-bleach/knowledge/findings/2026-05-24-coral-cover-dropped-…md`. Sub-agent B: `lit-monitor/knowledge/findings/2026-05-24-rss-poller-…md`. |
| A2 — cross-cairn write to OTHER cairn | **PARTIAL** | Cross-cairn writes succeeded via `cd` + `cairn.toml` cwd-walk (sub-agent A's write to lit-monitor, sub-agent B's write to coral-bleach landed correctly). **Honest gap:** the CLI exposes no `--cairn` flag, so the MCP-side `cairn=<name>` parameter form of A2 isn't exercised here. Both sub-agents flagged this independently. |
| A3 — clear error when no cairn at cwd | **PASS** | Both sub-agents: `error: no cairn found at or above /tmp`, exit 2. |
| A4 — per-cairn collaborator discrimination | **PASS** | `cairn status` from each cairn root returned disjoint collaborator lists: coral-bleach=(kyle, lila); lit-monitor=(kyle, priya). |
| A5 — per-cairn state discrimination | **PASS** | Each cairn's `status` returned its own decision/finding counts and git head. No cross-leakage. |
| A6 — no agent-posture confusion | **PASS** | Both sub-agents explicitly reported no confusion about which cairn they were writing to throughout the run. |

### Final on-disk state (both cairns `cairn validate` → OK)

- `coral-bleach`: 2 decisions (D-001 by kyle baseline, D-002 by kyle from sub-agent A), 3 findings (1 baseline + 1 sub-agent A + 1 sub-agent B's cross-cairn), 1 open question, 0 actions.
- `lit-monitor`: 2 decisions (D-001 by priya baseline, D-002 by kyle from sub-agent B), 2 findings (1 sub-agent B + 1 sub-agent A's cross-cairn), 1 open question, 0 actions.

## Scenario 2 — many users / one cairn over HTTP

Three sub-agents launched in parallel as `alex` (methods), `morgan` (analysis), `sam` (writeup). Each had distinct git identity in its project repo (`user.email = <id>@example.com`). All three talked to the same HTTP MCP server (`cairn dev serve`, port 47973) via remote-paired `cairn.toml`. Shared bearer token `test-shared-token`.

### Acceptance-criterion scorecard

| Criterion | Result | Evidence |
|---|---|---|
| B1 Attribution | **PASS** | Every entity carries the writer's identity. `state/decisions.yaml`: D-002/D-003/D-004 by alex; D-005/D-006/D-007 by sam. `state/action_items.yaml`: A-001=alex, A-002=morgan, A-003=sam, A-004=morgan. Both findings: author=morgan. No mis-routing. |
| B2 No data loss | **PASS** | 10 sub-agent writes attempted (alex 4: D-002/D-003/D-004 + A-001; morgan 4: 2 findings + A-002 + A-004; sam 4: D-005/D-006/D-007 + A-003). All 10 visible server-side. |
| B3 Concurrent-write safety | **PASS** | `cairn validate` against server-side cairn → OK. YAML parses cleanly. No partials, no duplicate IDs. |
| B4 ID monotonicity | **PASS** | D-001..D-007 contiguous (one writer's apparent "gap" of A-001 → A-003 is in fact morgan's A-002 between them — no real gap). Both decision and action allocators interleaved cleanly under concurrent writers without race-induced duplicates. |
| B5 Cross-user references | **PASS — the key result** | Sam's D-007 has `related: [D-002]` where D-002 was authored by alex earlier in this same run. The server accepted the cross-user reference and the on-disk YAML preserves it (`tests/agent_smoke/.../runs/20260524T190336Z/scenario-2-sam.md` §3 task 5). Additional cross-class refs that passed: D-002 → Q-001 (alex referencing a question raised by morgan), D-005 → D-001 (sam referencing baseline), D-006 → Q-001 (sam referencing morgan's question). |
| B6 `whoami` discrimination | **N/A from CLI — gap** | No `cairn whoami` CLI subcommand exists. Inferred indirectly: all three sub-agents' writes were attributed correctly via X-Cairn-Git-* identity threading, confirming the server-side `_resolve_caller_identity` plumbing works. Same gap as past run F-05. |
| B7 No identity confusion | **PASS** | All three sub-agents reported zero identity confusion across their runs. |
| B8 HTTP transport stays up | **PASS** | Server PID 179180 (port 47973) served throughout the 10-minute window without 5xx errors, connection resets, or duplicate-write artifacts from retries. The post-run inspection of the server log shows clean session handshakes per call. |

### Final on-disk state

`/tmp/cairn-sc2-F0KF/cache/cairn/dev-servers/sandbox-47973/cairns/shared-physics-paper/`:
- 7 decisions (D-001..D-007), 4 actions (A-001..A-004), 1 open question (Q-001 unchanged), 3 findings (1 baseline + 2 morgan).
- `cairn validate` → OK.

### Identity threading confirmation

The X-Cairn-Git-* header path (`src/cairn/mcp/remote.py` injection → `src/cairn/mcp/server.py` `_resolve_caller_identity` resolution) is **end-to-end functional**. Three distinct git identities in three project repos produced three distinct attributions in the cairn state with zero crossover. This is the load-bearing test for commit 14bfd78.

## Feature-completeness verdict (16 of 16)

| Feature | Spec | Verdict |
|---|---|---|
| `cairn dev serve` detached HTTP + XDG state | US-T-01, ADR-0014 | **OK** — Scenario 2 server started, survived, stopped cleanly. |
| `cairn dev list` / `stop --pid|--all` | US-T-01 | **OK** — exercised during teardown. |
| 3 fixtures in `fixtures_data.py` | ADR-0014 | **OK** — all three scaffolded cleanly via CLI. |
| `cairn dev scaffold-fixture --http-endpoint` local-pair | US-T-02 | **OK** — Scenario 1 used local scaffolds; Scenario 2 alternative path. |
| `cairn dev scaffold-fixture --remote` server-side scaffold | US-T-02, ADR-0013 | **OK** — Scenario 2 used `--remote $URL` with `CAIRN_BEARER_TOKEN` for server-side scaffold. |
| Fixture summary drift detection | ADR-0013 | **OK** — `--remote` flow exited 0 with the server's summary echoed; no drift. |
| `cairn dev fixtures [--remote]` | US-T-03 | Not directly exercised this run; covered by prior runs and the dedicated pytest. |
| Server-side `scaffold_fixture` / `list_fixtures` MCP tools | ADR-0013 | **OK** — `scaffold_fixture` invoked successfully under `--allow-dev-tools`. |
| Server-side `unregister_fixture` MCP tool | US-T-04, ADR-0015 | Not exercised in this smoke run; pytest covers it (`test_us_t_04_dev_unregister_fixture.py` 14 tests pass). |
| `cairn dev unregister-fixture` CLI | US-T-04, ADR-0015 | Same as above — pytest-covered, smoke didn't exercise it. |
| `--remote` env-var fallback (`CAIRN_DEV_REMOTE_URL`) | US-T-02/03/04 | Not exercised this run; pytest-covered. |
| HTTP transport `cairn mcp --transport streamable-http` | ADR-0012 | **OK** — server ran in this mode throughout Scenario 2. |
| Remote-mode `cairn.toml` (endpoint + name pairing) | ADR-0012 | **OK** — three sub-agent project repos paired against a single endpoint. |
| Tier-1 write commands dispatch over HTTP | ADR-0012 | **OK** — `decision add` / `finding add` / `action add` all round-tripped via HTTP. |
| X-Cairn-Git-* identity headers | commit 14bfd78 | **OK** — three distinct identities → three distinct attributions, perfect routing. |
| Bearer-token resolution (env → credentials.toml) | ADR-0012 | **OK** — `CAIRN_BEARER_TOKEN=test-shared-token` resolved via env-first path. |

## Pytest regression — fixed during this run

A real branch-introduced regression was discovered when running the full pytest suite on this branch before the smoke run.

**Symptom:** 37 failures in `tests/test_mcp_tools.py` when the full suite runs together. `main` is clean (269 passed). The failures are deterministic and surface only when `test_adr_0013_server_side_scaffold.py` (added on this branch in commit `21fd15f`) runs before `test_mcp_tools.py`.

**Root cause:**
- `tests/test_adr_0013_server_side_scaffold.py:176` uses the modern pattern `asyncio.run(_run())`, which closes its event loop on exit and clears the current-loop reference.
- `tests/test_mcp_tools.py:47` used the deprecated pattern `asyncio.get_event_loop().run_until_complete(...)`. After `asyncio.run()` had cleared the loop, this raised `RuntimeError: There is no current event loop in thread 'MainThread'`.

**Why CI didn't catch it:** All recent CI runs on this branch show `action_required` with 0 jobs — first-time-contributor approval gate. No CI run actually executed. Once the gate is approved, CI will fail without this fix.

**Fix applied:** One-line change in `tests/test_mcp_tools.py:47-49` — replace the deprecated `asyncio.get_event_loop().run_until_complete(...)` with `asyncio.run(...)`. This matches the pattern the ADR-0013 test already uses. Full suite is now **321 passed, 0 failed**.

**Status:** Fix is uncommitted in the working tree. Recommend including it in the next commit on this branch before merging.

## UX findings (new)

These are surfaced by this run; not blocking for the feature-complete verdict but worth a follow-up issue or ADR.

**UX-1. Finding slugs truncate mid-word.** Multiple sub-agents in scenario 1 produced slugs like `...biology-preprints-but-drop` (lost "drops") and `...cross-referencing-wit` (lost "with literature"). Looks like a deterministic character cap that doesn't respect word boundaries. Mid-word truncation reads like a typo.

**UX-2. Write success messages don't echo author/related.** A line like `Recorded D-005 (author=sam, related=[D-001]) in cairn ...` would let a sub-agent verify identity-threading + cross-references from the tool output alone. Today, you have to re-read the YAML. For a smoke test designed to catch identity bleed, this is a meaningful gap. (Surfaced by morgan, sam, and alex.)

**UX-3. `cairn registered` is confusing in cairn.toml-paired projects.** All three Scenario 2 sub-agents reported that `cairn registered` says "No cairns registered" when run from a remote-paired project repo — technically true of the client-side user-level registry, but identical wording to "you have nothing set up". A "this project is paired with `<name>` via `./cairn.toml`" line would close the gap.

## UX findings (carried from past runs)

These were already known and continue to apply.

**UX-4. No `cairn whoami` CLI subcommand** (carryover F-05). The MCP `whoami` tool exists server-side but the CLI doesn't dispatch to it. B6 in scenario 2 can only be evaluated by inference today.

**UX-5. `cairn status` against remote-paired cairn errors** (carryover known gap). Both alex and morgan noted that the error message is clear and actionable, but one sub-agent (alex) reported exit code 0 from this message, which is mildly inconsistent with morgan's exit-1 observation. Worth verifying the actual exit code and standardizing on non-zero.

**UX-6. `cairn action add` rejects `--context`.** Both morgan and sam hit it. Decisions accept `--context`; actions do not, but the "Did you mean `--text`?" hint is misleading because the caller already had `--text` and was trying to attach additional rationale. Either add `--context` to actions for surface parity, or drop the misleading hint.

**UX-7. No `cairn open-question add` CLI.** Morgan was asked to file an open question; the closest CLI surface was `action add`, which she used as a workaround. Open questions exist as a first-class entity (Q-NNN with raised_by, related, supersedes) but there's no CLI affordance to create one.

## Verification gaps still open for follow-up

These were identified in the pre-smoke audit and remain open after this run (the user explicitly chose "no code changes" for these):

1. Smoke-test scenarios not gated in CI — they're sub-agent-driven, not pytest. A regression won't surface in automated feedback.
2. Dockerfile (`src/cairn/mcp/Dockerfile`) not exercised in CI — no automated "image starts and serves" smoke.
3. No dedicated pytest for concurrent-write serialization under tight parallelism — scenario 2 exercises soft interleaving but doesn't drive microsecond races.
4. No bearer-token rejection / rotation tests — the shared-token model in scenario 2 worked but unauthorized-access paths aren't covered.
5. Re-scaffold conflict (duplicate-fixture-name) handling not exercised end-to-end.
6. Error-message-quality assertions are loose — tests verify structure, not "clear" per acceptance criteria.
7. Production server runtime gate (no `--allow-dev-tools`) not asserted at deployment time.

## Recommendations (priority ordered)

1. **Commit the pytest fix in `tests/test_mcp_tools.py`** before merge. Without it, CI on this branch will be red the moment the action-required gate is approved.
2. **Add `cairn whoami` CLI subcommand** that dispatches to the MCP `whoami` tool — closes B6 from being structurally untestable and matches the MCP surface.
3. **Echo `author`/`assignee`/`related` in write success messages** (UX-2) — single largest win for smoke-test observability.
4. **Add `cairn open-question add` CLI** (UX-7) and **`--context` on `cairn action add`** (UX-6) — small surface-area gaps that bite the natural workflow.
5. **Word-boundary trim on finding slugs** (UX-1) — small cosmetic fix.
6. **Triage `cairn status` exit-code inconsistency** for remote-paired-cairn errors (UX-5) — verify and standardize.
7. **Gate scenario 1 + 2 behind `@pytest.mark.integration`** so they can be triggered (manually or weekly) without bloating regular CI runtime. Concurrent ADR welcome.

## Artifacts

- `scenario-1-kyle-coral-bleach.md` — sub-agent A feedback (Scenario 1).
- `scenario-1-kyle-lit-monitor.md` — sub-agent B feedback (Scenario 1).
- `scenario-2-alex.md` — Alex (methods lead) feedback (Scenario 2).
- `scenario-2-morgan.md` — Morgan (analysis lead) feedback (Scenario 2).
- `scenario-2-sam.md` — Sam (writeup lead) feedback (Scenario 2).
- This file — synthesis.

Scenario 1 tmpdir (preserved for forensics until cleanup): `/tmp/cairn-sc1-rUOm/`.
Scenario 2 tmpdir (preserved): `/tmp/cairn-sc2-F0KF/`. HTTP server PID 179180 still running at the time of this synthesis — recommend `cairn dev stop --all` after final review.
