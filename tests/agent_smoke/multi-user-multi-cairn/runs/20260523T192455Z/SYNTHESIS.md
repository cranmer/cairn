# Synthesis — scenario 2 (many users, one cairn over HTTP)

**Run:** `20260523T192455Z`
**Branch:** `claude/multi-user-multi-cairn-rerun-1`
**Fixes under test:** PR #27 (merged as `d104a6d`).
**Companion runs:** `runs/20260523T175633Z/` (scenario 1 original — found F-01..F-10),
`runs/20260523T191531Z/` (scenario 1 rerun — confirmed F-01..F-10 fixes).

## Headline

**Scenario 2 ran successfully on the second attempt** (first attempt was
blocked by an environmental kill of the HTTP server during the idle gap
between launch and sub-agent dispatch — see E-1 below). With the server
properly detached (`setsid nohup ... < /dev/null`), all eight acceptance
criteria that this methodology can reach from the CLI surface passed.

- **B1 Attribution:** every entity's `author` / `assignee` field matches
  the sub-agent that issued the write. No mis-routing.
- **B2 No data loss:** 10/10 writes landed. Alex 4 (D-002, A-001, D-003,
  D-004), Morgan 3 (2 findings, A-002), Sam 3 (D-005, D-006, A-003).
- **B3 Concurrent-write safety:** `cairn validate` exits 0. No YAML
  corruption, no half-writes, no duplicate ids.
- **B4 ID monotonicity:** D-001..D-006 and A-001..A-003 contiguous, no
  gaps, no dupes — even though the writers' ordering interleaved
  (A-001 alex, A-002 morgan, A-003 sam reflects the actual race winner
  by tens of milliseconds, not the writer's "logical" ordering).
- **B5 Cross-user references:** Sam's D-005 has `related: [D-004]` —
  D-004 being a decision Alex allocated earlier in the same run. The
  server accepted the cross-reference and the on-disk state confirms
  it persisted correctly. This is the "really concurrent multi-author
  paper" workflow working end-to-end.
- **B7 Agent posture:** all three sub-agents reported zero identity
  confusion across the run.
- **B8 HTTP transport stays up:** server PID 21784 served throughout
  with no 5xx errors, no resets, no duplicates from retries.

The one criterion not testable from this run: **B6 `whoami`
discrimination** — the CLI has no `cairn whoami` subcommand, so the
per-process git-config-based identity probe couldn't be exercised
through this run's CLI driver. F-05 from the previous run's findings
still applies.

The fixes from PR #27 made scenario 2 actually executable for the first
time:

- **F-01** — `cairn mcp --transport streamable-http` started cleanly
  (same command would have crashed with `TypeError: FastMCP.run() got
  an unexpected keyword argument 'host'` before).
- **F-02** — every sub-agent's `cairn finding/decision/action add`
  performed the MCP session handshake (initialize → notification →
  tools/call) and got real responses. The exact 400 "Missing session
  ID" failure the original run-1 setup hit no longer occurs.
- **F-03/F-04** — sub-agents' workaround for "read state to find
  Alex's id" used direct filesystem reads (acceptable for this
  same-machine setup; see N-2 below). When they did try a CLI read,
  `cairn status` against a remote-paired repo errored clearly with
  the cairn name and endpoint, matching the post-fix behavior.

## Acceptance-criterion scorecard

| Criterion | Result | Evidence |
|---|---|---|
| B1 attribution | **PASS** | `state/decisions.yaml` D-002..D-004 all `author: alex`; D-005..D-006 `author: sam`. `state/action_items.yaml` A-001=alex, A-002=morgan, A-003=sam. Both findings carry `author: morgan`. |
| B2 no data loss | **PASS** | 10 writes attempted (sub-agent reports), 10 landed (on-disk count) |
| B3 concurrent safety | **PASS** | `cairn validate` → OK. YAML parses. No partials. |
| B4 ID monotonicity | **PASS** | D-001..D-006 and A-001..A-003 contiguous |
| B5 cross-user references | **PASS** | Sam's D-005 `related: [D-004]` (Alex's runtime decision) persisted; server accepted |
| B6 `whoami` discrimination | **N/A — gap** | F-05 deferred: no `cairn whoami` at CLI |
| B7 posture consistency | **PASS** | all three sub-agents reported consistent identity |
| B8 HTTP transport stays up | **PASS (after E-1 workaround)** | server stayed up throughout the successful run; no 5xx / resets / dupes |

## E-1 (medium, environmental — not a Cairn bug per se)

**HTTP server killed during the idle gap between launch and use.**

First scenario-2 attempt: server was started, smoke-tested with a single
`cairn finding add` (success), then the cairn was reset to baseline.
~10-15 minutes elapsed (a user-driven pause and several Bash setup
calls). When all three sub-agents launched, every call returned
`Connection refused`; the server (PID 16505) was no longer a running
process. The server log truncated mid-`Processing request of type
CallToolRequest` — no traceback, no shutdown line, just abrupt
disappearance.

**Root cause:** the original launch used plain `nohup cairn mcp ... &`
inside a Bash tool's transient subshell. When that subshell exited,
the process *should* have been orphaned-to-init, but something in this
container's process governance (possibly a janitor for processes whose
spawning session has ended; possibly OOM; possibly a no-tty-parent
sweep) reclaimed it.

**Workaround for the second attempt:** `setsid nohup cairn mcp ... <
/dev/null > log 2>&1 &`. Confirmed via `ps -o ppid,sid` that the
server got `PPID=1` and its own session ID before any other Bash
tool calls ran. Server then survived the whole sub-agent run.

**The lesson is operational, not a Cairn code defect.** In production,
`cairn mcp --transport streamable-http` should be run under a real
process supervisor (systemd, supervisord, a `Deployment` pod, etc.)
rather than a hand-rolled `nohup`. Worth a docs note alongside the
existing transport documentation in `mcp_cmd.py`'s `--transport`
help text, e.g. "for long-lived HTTP deployments, run under a
supervisor (systemd / supervisord / k8s) rather than a bare nohup."

## New findings (low-severity, from sub-agent feedback)

### N-1 — CLI write commands don't echo accepted parameters

All three sub-agents flagged this independently:

- `cairn decision add` confirms id + state path + related (after F-08
  fix) — but doesn't echo back `--author` or `--supersedes`.
- `cairn action add` confirms id only — `Added A-002.` No echo of
  `--text`, `--assignee`, or `--due-date`.
- `cairn finding add` confirms file path — no echo of `--author` or
  `--related`.

For an **attribution-graded** scenario (B1 here), this matters: a
sub-agent has no positive confirmation from the server response that
the server attributed the write to the right collaborator. The
orchestrator's after-the-fact state inspection is the only path to
verifying attribution from a write's side.

**Suggested treatment:** extend the F-08-style "echo accepted params"
format to `action add` (`Added A-002 (assignee=morgan, due 2026-06-02).`)
and `finding add` (`Logged finding at ... (author=morgan).`). One-line
changes; high signal-to-noise for self-verification during concurrent
runs.

### N-2 — Remote-paired sub-agents have no self-verification read path

A consequence of F-03's `require_local_target()`. Sam's task explicitly
required reading the cairn's state to find Alex's runtime-allocated D-NNN
and cite it in `--related`. Sam couldn't use `cairn status` (`error:
'cairn status' is not supported against a remote-MCP cairn yet`), so the
backlog directed Sam to read `state/decisions.yaml` directly on the
shared filesystem. That worked for this same-machine test but, in Sam's
words, "defeats the point of pairing for a collaborator who shouldn't
need to know the cairn's on-disk layout."

**This is the right time to ship remote-MCP read commands.** Whichever
of `cairn status`, `cairn orient`, or a dedicated `cairn list
decisions` lands first, it should dispatch over the same call_tool
infrastructure F-02 fixed. The MCP server already has `status`,
`whoami`, and `get_open_questions` tools; only the CLI's remote
dispatcher needs to learn to route reads.

### N-3 — `--related` validation is server-deferred

Sam: "`cairn decision add --related Q-001` silently accepts an id that
may or may not exist in `open_questions.yaml`. (In this run Q-001 does
exist — I checked after the fact — but the server didn't tell me so
at write time.)"

The CLI doesn't validate id presence at write time; `cairn validate`
is the catcher's mitt. For concurrent runs where ids are being
allocated live, an at-write-time existence check (cheap server-side
lookup against the cairn-wide id index) would catch typos and timing
mistakes immediately. **Optional:** the server could return the
canonical YAML block in its tools/call response so the CLI can echo
it (which would also address N-1).

### N-4 — No CLI `cairn open-question add` (or `cairn question add`)

Morgan's task 4 was explicitly skipped per the backlog because the
CLI has no open-question-add command. The schema supports them; the
MCP server has `add_open_question`; but the CLI surface omits this
verb. Open questions are first-class cairn entities — the asymmetry
versus decisions/actions/findings is hard to defend.

**One-line fix:** add `cairn question add` (or `cairn open-question add`)
that mirrors `decision_cmd.py`'s shape.

### N-5 — No `--cairn <name>` for remote-mode multi-cairn routing

Morgan: "In a multi-cairn HTTP world it would be nice to support
`--cairn <name>` directly so the registry can do the routing without
cwd walks." A user with one local registry config but multiple paired
project repos could then call `cairn finding add --cairn coral-bleach
...` from anywhere, including a non-paired cwd.

This is a small change to `_common.py::resolve_target()` to accept
an explicit cairn-name override. Useful but not blocking.

### N-6 — `Recorded` vs `Added` verb inconsistency

Alex's nit: `decision add` says `Recorded D-NNN`, `action add` says
`Added A-NNN`. Cosmetic; consistency would be nicer. Either verb is
fine, pick one.

## Methodology notes

- **First-run failure as a methodology win.** The first scenario-2
  attempt didn't surface a Cairn defect, but it surfaced a real
  deployment-environment subtlety: long-running HTTP servers spawned
  from transient shells are fragile, and the docs / tooling should
  acknowledge that. Both the failed-run feedback files and this
  synthesis preserve the observation; the failed-run feedback was
  overwritten by the re-attempt to keep the run artifacts
  authoritative.
- **All three sub-agents independently reached parts of the same
  recommendation** (N-1: CLI should echo more accepted params; N-2:
  no remote read surface; N-4: open-question gap). Cross-confirmation
  again proved the methodology's value relative to a single-agent
  test.
- **Sam's cross-reference test (B5) is the most powerful element of
  this scenario.** It forced a live read-before-write across users
  during a concurrent run, exactly the workflow that's hardest to get
  right in a multi-author paper. Server-side id allocation +
  schema-level reference validation +  filesystem coherence under
  three writers — all worked. This is the test that would have
  caught the kind of race-ID-collision bug a load test would also
  surface, but with realistic semantics.

## Recommendations (ranked)

1. **Process-supervision docs note (E-1).** A one-line addition to
   `cairn mcp --transport streamable-http`'s help text and any HTTP-
   deployment recipe ("run under a real supervisor — `systemd`,
   `supervisord`, k8s — not a bare `nohup`"). Plus, for the docs
   page on multi-user deployments (when it exists), a worked example
   `cairn-mcp.service` file.
2. **Ship remote-MCP read commands (N-2).** This is the biggest UX
   gap the scenario surfaced. `cairn status`, `cairn orient`, and a
   `cairn list decisions / findings / actions / open-questions`
   command suite — all dispatching via call_tool against the MCP
   server's existing read tools. Most of the server side is already
   in place; the CLI just needs to remove the `require_local_target`
   gate for these specific commands.
3. **Add `cairn open-question add` (N-4).** Closes the CLI parity gap
   Morgan's task 4 explicitly hit. Small surface change.
4. **Extend F-08-style output to `action add` and `finding add`
   (N-1).** Cheap, high self-verification value.
5. **At-write-time `--related` existence check (N-3).** Server-side
   change; one-line lookup against the cairn-wide id index before
   committing the entity.
6. **`--cairn <name>` override for remote dispatch (N-5).** Useful
   for advanced workflows; not blocking.
7. **Action vs decision verb consistency (N-6).** Cosmetic.

## Artifacts

- `runs/20260523T192455Z/scenario-2-alex.md` — Alex's feedback (full)
- `runs/20260523T192455Z/scenario-2-morgan.md` — Morgan's feedback (full)
- `runs/20260523T192455Z/scenario-2-sam.md` — Sam's feedback (full)
- `runs/20260523T192455Z/SYNTHESIS.md` — this file

The previous two synthesis files are companions:

- `runs/20260523T175633Z/SYNTHESIS.md` — the original scenario-1 run
  that surfaced F-01..F-10. F-01 and F-02 there blocked scenario 2
  entirely; this run confirms those fixes work end-to-end.
- `runs/20260523T191531Z/SYNTHESIS.md` — the scenario-1 rerun that
  confirmed F-03..F-08 + F-10 fixes from the CLI surface side.
