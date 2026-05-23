# Synthesis — multi-user / multi-cairn UX test run 2 (post-fix verification)

**Run:** `20260523T191531Z`
**Branch:** `claude/multi-user-multi-cairn-rerun-1`
**Plan:** `tests/agent_smoke/multi-user-multi-cairn/` (PR #26, merged)
**Fixes under test:** PR #27, merged into main as `d104a6d`.
**Previous run:** `runs/20260523T175633Z/` (the run that produced findings F-01..F-10).

## Headline

**Every previously-flagged scenario-1 regression that this run could reach
via the CLI is fixed.** Both sub-agents independently confirmed:

- `cairn status`, `cairn validate`, `cairn orient`, `cairn collaborator add`
  now all work from a paired project repo cwd (F-03).
- The pointer-resolution error names the pointed-at cairn and tells the user
  to `cairn register` it (F-04).
- `cairn --version` works at the root (F-07).
- `cairn decision add` output now includes the state file path and echoes
  accepted `--related` ids (F-08).
- Finding slug truncation no longer leaves a dangling trailing hyphen (F-06).

F-09 (`branch: "current"` in `cairn status --json`) is still present, as
expected — it was deferred from the previous run and the CLAUDE.md backlog
tracks it under the ADR-0008 rename.

F-01 (HTTP transport startup) and F-02 (MCP session handshake) sit on a
code path this run doesn't exercise — both fixes have unit + integration
test coverage merged with PR #27 (`tests/test_multi_user_multi_cairn_fixes.py`),
so they're covered without re-running scenario 2 here. Scenario 2 should
be re-run as its own follow-up if a full multi-user concurrency check is
wanted.

## What this run validates

| Finding | Severity (run 1) | Status this run |
|---|---|---|
| F-01 — HTTP transport startup | CRITICAL | Covered by `test_f01_http_server_actually_starts` (unit). Not re-tested here. |
| F-02 — MCP session handshake | CRITICAL | Covered by `test_f02_remote_call_tool_round_trip` and `test_f02_remote_finding_add_round_trip`. Not re-tested here. |
| F-03 — Routing asymmetry | HIGH | **Confirmed fixed.** Both sub-agents ran `status/validate/orient/collaborator add` from project repo cwd; all succeeded. |
| F-04 — Error masked F-03 | MEDIUM | **Confirmed fixed.** Sub-agent A's task 11 hit a stale pointer; error named the cairn and pointed to `cairn register`. Quote: `error: cairn 'this-does-not-exist' is not registered. Add it with \`cairn register this-does-not-exist <path>\`. See \`cairn registered\`.` |
| F-05 — No `cairn whoami` at CLI | MEDIUM | **Still deferred.** Sub-agent B confirmed: `cairn whoami` → `No such command 'whoami'.` |
| F-06 — Slug trailing hyphen | LOW | **Confirmed fixed.** Sub-agent A: `...-througho.md` (no trailing dash). Sub-agent B: `...-relevant-to-base.md` (no trailing dash, slug exactly 60 chars). |
| F-07 — `cairn --version` flag | LOW | **Confirmed fixed.** Returns `0.0.1.dev109+gd104a6d4a`. |
| F-08 — Terse `decision add` output | LOW | **Confirmed fixed.** Both sub-agents got `Recorded D-002 in state/decisions.yaml; related: Q-001.` |
| F-09 — `branch: "current"` in JSON | LOW | **Still deferred** (CLAUDE.md backlog). Both sub-agents reported the field unchanged, as predicted by the backlog. |
| F-10 — `--type` help omits group/unknown | LOW | Patched as part of the F-03 commit; not separately re-tested here. |

## Acceptance criteria — scenario 1 (re-graded)

The original A1–A6 didn't all line up with the CLI surface this run
exercised; with F-03 fixed, the natural mapping is much cleaner.

| Criterion | Result |
|---|---|
| A1 default routing in paired-cwd | **PASS for both writes and reads** (was: PASS writes / FAIL reads in run 1) |
| A2 explicit cross-cairn write | **PASS** — both sub-agents `cd`'d to the other project repo and writes routed correctly to that cairn (no `--cairn` flag at the CLI; cwd-switching is the CLI's analog of MCP's `cairn=<name>` param) |
| A3 error on unknown cairn | **PASS** — F-04 fix means the error now actually names the cairn from cairn.toml and recommends `cairn register` + `cairn registered`; this is functionally the MCP "error names registered cairns" criterion ported to the CLI |
| A4 `whoami` discrimination | **N/A — gap** — F-05 still deferred; the methodology can't test this from the CLI alone |
| A5 per-cairn `status` data | **PASS** — confirmed cleanly, both sub-agents got correct cairn-specific counts directly from the project repo cwd |
| A6 no agent posture confusion | **PASS** — both sub-agents reported zero identity uncertainty; routing was "invisible-but-correct" (sub-agent B's wording) |

**Bonus: cross-cairn-write observability.** Sub-agent A noted "1 total in
status but 2 files on disk" at baseline; sub-agent B noted a "pre-seeded
extra finding" on lit-monitor. Both observations were the same effect: a
finding the *other* sub-agent had just written via cross-cairn dispatch.
Verified on disk: every write is attributed correctly, no mis-routing, no
duplicates. The methodology's "flag anything you didn't write" guidance
worked exactly as designed — sub-agents saw the other's writes, flagged
them, and the orchestrator confirmed correctness from the ground truth.

## New observations from this run

Nothing rises to the severity of the run-1 findings, but two small items
worth noting for future-passes follow-up:

### O-1 (LOW) — No `cairn collaborator remove`

Sub-agent B's task 11 added a `testperson` collaborator and was told in the
backlog to "manually clean up by editing collaborators.yaml" — i.e. the
backlog itself acknowledges the CLI gap. There's no `cairn collaborator
remove`. Adding a removal command is small surface area but worth doing
alongside F-05 (CLI whoami) as part of a "CLI parity with MCP read/list/
remove surface" pass.

### O-2 (LOW) — Slug truncation still mid-word

F-06's fix was the minimum: strip trailing `-` after truncation. The
truncation point itself is still character-based (60 chars), so long
titles still chop mid-word (`througho` for "throughout", `base` for
"baseline"). Both sub-agents noted this as a cosmetic issue, not a
blocker. A word-boundary-aware truncation (rewind to the last `-` within
budget) would be a nice polish — say a one-line change to `_kebab`.

### O-3 (informational) — `cairn status` header is now genuinely useful

Both sub-agents called out the `Cairn 'coral-bleach' [/tmp/.../cairns/
coral-bleach]` header line as making routing legible — it's the affordance
that lets you confirm at a glance which cairn the cwd resolved to. Worth
preserving across formats. Sub-agent A suggested adding `cairn_path` to
the JSON output for parity.

## Methodology notes

- **Same fixtures (regenerated, not reused).** Both project repos and both
  cairns were scaffolded fresh in tmpdir per the same fixture spec as run
  1, so this is a like-for-like comparison of pre- and post-fix behavior.
- **CLI-only adaptation still in force.** No cairn MCP server was
  registered against the orchestrator's parent Claude session, so
  sub-agents continued to drive the CLI rather than MCP tools. The F-01
  and F-02 fixes therefore aren't *user-visible* in this run, but they're
  covered by the integration tests in PR #27 that spawn a real HTTP server
  subprocess.
- **Cross-confirmation across sub-agents** (run-1's main methodological
  win) held up again — both independently called out F-04, F-06, F-08
  fixes in identical terms; both independently flagged F-05 and F-09 as
  still-deferred without prompting; both caught the cross-cairn-write
  effect (run-1's "no silent mis-routing" check) under the same name.
- **No regressions surfaced.** Every behavior the run-1 fixes targeted is
  now where you'd expect it; nothing that was working broke. The full
  test suite at HEAD (`d104a6d4a`) is 269 passing, 0 failing.

## Recommendations

1. **Scenario 2 follow-up.** Now unblocked. With F-01 and F-02 fixed, the
   three-collaborator HTTP-transport scenario can run as designed. The
   fixture from run 1 (`shared-physics-paper` cairn + project repo +
   three sub-agent backlogs) is reusable; just regenerate it against
   current main.
2. **F-05 and O-1 as a pair.** A small "CLI read/identity parity" PR
   adding `cairn whoami` and `cairn collaborator remove` would close the
   two outstanding CLI gaps both sub-agents flagged. Each is ~30 lines.
3. **F-09 rename.** Already in CLAUDE.md backlog. The JSON output's
   `branch: "current"` is the visible symptom; can ride along with the
   bigger ADR-0008 user-facing rename pass.
4. **O-2 word-boundary slug.** Optional polish. One-line change.

The methodology pattern (`tests/agent_smoke/multi-user-multi-cairn/`) is
stable enough to re-use for these and any future scenario re-runs. Each
run produces a synthesis under `runs/<timestamp>/` so the comparison set
is now two entries deep.

## Artifacts

- `runs/20260523T191531Z/scenario-1-kyle-coral-bleach.md` — sub-agent A feedback
- `runs/20260523T191531Z/scenario-1-kyle-lit-monitor.md` — sub-agent B feedback
- `runs/20260523T191531Z/SYNTHESIS.md` — this file

For comparison: `runs/20260523T175633Z/SYNTHESIS.md` (the original run, with
the full F-01..F-10 finding catalog).
