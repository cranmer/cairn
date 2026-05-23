# Sub-agent feedback — scenario-1 / Kyle on lit-monitor (run 2)

## 1. Identity

- Sub-agent role: Kyle on lit-monitor (paired project repo)
- Collaborator id used for writes: kyle
- Working directory: /tmp/cairn-run-20260523T191531Z/projects/lit-monitor/
- Cairn(s) reachable from this session: lit-monitor, coral-bleach (both visible in `cairn registered`)
- Transport: n/a — used the `cairn` CLI directly (no MCP server in this run)
- Endpoint (if http): n/a

## 2. Environment sanity check

- `whoami()` (no cairn param) returned: n/a — `cairn whoami` is not a CLI subcommand
  (`No such command 'whoami'`). I confirmed identity by passing `--author kyle` to each
  write command instead. Only an MCP client would expose `whoami()`; this scenario
  drove the CLI.
- `status()` for each reachable cairn — baseline before any writes:
  - lit-monitor: collaborators=2 (kyle, priya), decisions=1, open_questions=1,
    findings=0, actions=0, git=master @ 03b465d
  - coral-bleach: not read until after I `cd`d into its project repo for task 5/6;
    at the post-write check it showed decisions=2, open_questions=1, findings=4
    (existing 3 + the one I just added). No baseline snapshot was taken before the
    write, so I can't report its pre-write counts from this session, but the work
    backlog only required the lit-monitor baseline (1 decision, 0 findings,
    1 open question, 2 collaborators), which matched exactly.
- Surprising? No. The backlog's stated lit-monitor baseline matched the actual
  `cairn status` output verbatim. Registry shows both cairns with the expected
  paths.

## 3. Work backlog completion

### Task 1: Registry visibility (`cairn registered` → both cairns)

- Intended: Confirm both lit-monitor and coral-bleach show in the user-level registry.
- Tool call(s) made: `cairn registered`
- Result: success — both cairns listed with their absolute paths under
  `/tmp/cairn-run-20260523T191531Z/cairns/`.
- Entity id allocated: n/a
- Author / raised_by / assignee: n/a
- Cross-references passed: n/a
- Notable: Output also identified the registry file as
  `/tmp/cairn-run-20260523T191531Z/config/cairn/server.toml`, confirming
  `XDG_CONFIG_HOME` override is taking effect.

### Task 2: Confirm pairing from the project repo (the regression target)

- Intended: From `projects/lit-monitor/` cwd, `cairn status` should return
  lit-monitor's state without error. Previous run errored here.
- Tool call(s) made: `cairn status` (cwd = `projects/lit-monitor/`)
- Result: success. Returned `Cairn 'lit-monitor'` with collaborators=2 (kyle, priya),
  decisions=1, open_questions=1, findings=0, actions=0. Matches the backlog's
  stated expected baseline exactly.
- Entity id allocated: n/a
- Notable: **Post-fix behaviour confirmed.** The project-repo → cairn pairing
  resolves correctly. Header line includes the cairn root path, which is helpful
  for confirming you're not accidentally on the wrong cairn.

### Task 3: Log a finding to the paired cairn (lit-monitor)

- Intended: `cairn finding add` from project repo cwd; default-route to lit-monitor.
- Tool call(s) made:
  `cairn finding add --author kyle --title "Coral Reefs journal RSS feed is unreliable" --body "Items arrive 2 to 3 weeks late; we should add a polling fallback."`
- Result: success.
- Entity id allocated: file path
  `knowledge/findings/2026-05-23-coral-reefs-journal-rss-feed-is-unreliable.md`.
  No `F-NNN` style id was printed — only the file path. (Findings are date+slug
  rather than numbered, which matches the schema.)
- Author / raised_by / assignee: --author kyle
- Cross-references: none passed (no `--related` flag used)
- Notable: Output was a single line:
  `Logged finding at knowledge/findings/2026-05-23-coral-reefs-journal-rss-feed-is-unreliable.md.`
  Clean and unambiguous.

### Task 4: Record decision (exercise the fixed output format)

- Intended: `cairn decision add` with `--related Q-001`. Capture verbatim output.
- Tool call(s) made:
  `cairn decision add --author kyle --text "Add a polling fallback for RSS feeds older than 7 days" --context "RSS unreliability finding logged above." --related Q-001`
- Result: success.
- Entity id allocated: D-002
- Author: kyle
- Cross-references passed: Q-001
- Verbatim output: `Recorded D-002 in state/decisions.yaml; related: Q-001.`
- Notable: Output format looks clean — id, file location, and the resolved
  related-list. Compares favourably against whatever the previous run saw
  (the backlog flags this as a fix area but doesn't quote the old output).

### Task 5: Cross-cairn finding write to coral-bleach

- Intended: From `projects/coral-bleach/` cwd, log a finding via the coral-bleach
  pairing. Confirm slug truncation behaviour.
- Tool call(s) made:
  `cd .../projects/coral-bleach/ && cairn finding add --author kyle --title "Transect-methodology paper (arxiv 2403.04567) relevant to baseline debate" --body "Connects to coral-bleach Q-001 on baseline-year choice."`
- Result: success.
- Entity id allocated: file path
  `knowledge/findings/2026-05-23-transect-methodology-paper-arxiv-2403-04567-relevant-to-base.md`.
- Slug check: the slug portion
  `transect-methodology-paper-arxiv-2403-04567-relevant-to-base` is exactly
  60 characters and ends with `-base` (a real token boundary — `baseline`
  truncated to `base`). **No dangling trailing hyphen.** Matches the post-fix
  expectation called out in the backlog: still mid-word truncation (expected),
  but no stray `-` at the end (the fix).
- Author: kyle
- Cross-references: none passed; the cross-cairn link is described in the body
  text rather than via a `--related` field.
- Notable: I did not pass an explicit `--cairn coral-bleach` flag — routing was
  by cwd. This worked. The work backlog also did not ask for an explicit cairn
  flag; it relied on cwd routing.

### Task 6: Sanity cross-read (status from each cwd)

- Intended: `cairn status` from each project repo cwd; counts should differ.
- Tool call(s) made: `cairn status` from `projects/lit-monitor/` and again from
  `projects/coral-bleach/`.
- Result: success, counts differ as expected.
  - lit-monitor: decisions=2, open_questions=1, findings=2, collaborators=2
  - coral-bleach: decisions=2, open_questions=1, findings=4, collaborators=2
- Notable: lit-monitor showed findings=2, not 1, despite my only logging one
  finding to it during this run. Checking
  `cairns/lit-monitor/knowledge/findings/` showed there was a pre-existing
  `2026-05-23-methods-comparison-paper-arxiv-2403-04567-is-worth-a-closer.md`
  already on disk — apparently part of the seeded fixture, not something I
  wrote. This isn't a problem, but it means the baseline-vs-final delta is
  +1 finding on lit-monitor (mine), not +2. If the orchestrator is comparing
  the post-state to the *backlog's stated baseline*, they should be aware that
  the seeded fixture for lit-monitor already had a finding on disk that the
  baseline ("0 findings") didn't account for — or perhaps the baseline count
  was wrong. Worth flagging.

### Task 7: Orient from project repo

- Intended: `cairn orient | head -15` from lit-monitor project repo. Per F-03 fix,
  should work.
- Tool call(s) made: `cairn orient | head -15`
- Result: success — printed lit-monitor's `ORIENT.md` (or its template equivalent).
  First 15 lines render the project title (`# lit-monitor`), an Overview placeholder
  ("TODO: One or two paragraphs..."), Current focus placeholder, and a Related
  repositories preamble. All TODOs because the cairn is a fresh fixture.
- Notable: Post-fix behaviour confirmed. No errors from project-repo cwd.
- Side note: The content is largely template TODOs — that's a fixture-state issue,
  not a bug. A real orient would expect substantive content.

### Task 8: JSON sanity (`cairn status --json | python3 -m json.tool`)

- Intended: Confirm `cairn status --json` produces valid JSON.
- Tool call(s) made: `cairn status --json | python3 -m json.tool`
- Result: success — JSON parsed without error. Keys observed include
  `project_name`, `cairn_root`, `branch`, `git_branch`, `last_commit_sha`,
  `last_commit_message`, `collaborator_count`, `collaborator_ids`, `goal_count`,
  `decision_count`, `open_question_count`, `incomplete_action_count`,
  `action_breakdown`.
- Notable: `branch` field contains the string `"current"` while `git_branch`
  contains `"master"`. Minor: I would expect `branch` to either be the git
  branch or to be renamed `exploration` per ADR-0008. (The backlog itself
  carries this as a known rename TODO, so this is expected.)

### Task 9: Validate

- Intended: `cairn validate` from project repo cwd, exit 0.
- Tool call(s) made: `cairn validate`
- Result: success — printed `OK`, exit code 0.

### Task 10: Error in unpaired cwd

- Intended: From `/tmp`, `cairn finding add` should error.
- Tool call(s) made: `cd /tmp && cairn finding add --author kyle --title "test" --body "test"`
- Result: error (expected), exit code 2.
- Verbatim error: `error: no cairn found at or above /tmp`
- Notable: Clear, actionable message. Mentions the offending path. Did not
  suggest `cairn registered` or `cairn link` as next steps, which would have
  been a nice touch but isn't required.

### Task 11: Collaborator add from project repo

- Intended: `cairn collaborator add` from project repo cwd should succeed
  (regression target per F-03).
- Tool call(s) made:
  `cairn collaborator add --id testperson --name "Test Person" --role helper`
- Result: success. Output: `Added 1 collaborator.`
- Entity id allocated: testperson
- Notable: Post-fix behaviour confirmed. I then removed the entry by editing
  `cairns/lit-monitor/state/collaborators.yaml` directly (the backlog said this
  was acceptable; there is no `cairn collaborator remove` subcommand). Post-
  cleanup the collaborator count is back to 2 (kyle, priya).

## 4. Identity consistency

- Did you ever feel uncertain about which user you were supposed to be? No.
  Every write was an explicit `--author kyle`.
- Did any tool response refer to you under a different identity? No. The CLI
  output never named the author back at me in a confusing way.
- `whoami()` consistency: n/a — not a CLI subcommand. (`No such command 'whoami'`.)
  This is fine for the CLI path, but if a future test wants identity
  introspection from the CLI, that command doesn't exist.

## 5. Cairn-routing observations (scenario 1)

- "To the project this repo is paired with" → I relied on cwd routing every
  time. I never passed an explicit `--cairn <name>` flag (and the help text I
  saw didn't surface such a flag prominently on `finding add`/`decision add`,
  so cwd routing is the natural path). It worked correctly for both lit-monitor
  and coral-bleach.
- Explicit `cairn=<name>` parameter: not exercised in this run — the work
  backlog never required it. The cross-cairn write to coral-bleach was done
  by `cd`ing into its project repo, not by passing `--cairn coral-bleach`
  from lit-monitor's cwd.
- Did I try to write to a cairn name the server rejected? No.
- Did any read tool return data from the wrong cairn? No. Each `cairn status`
  printed the correct cairn name in its header line, matching the cwd.

## 6. Concurrency observations

n/a — scenario 1, single agent, no parallel writes.

## 7. Errors and surprises

Errors seen:

1. `cairn whoami` → `No such command 'whoami'.` (Discovered when sanity-checking
   identity at start of section 2. Not part of the work backlog; just noted.)
2. `cd /tmp && cairn finding add ...` → `error: no cairn found at or above /tmp`,
   exit 2. (Expected; task 10.)

That's the complete list. No write failures, no validation failures, no
crashes. No stack traces or Python tracebacks anywhere.

## 8. UX friction

- **`cairn whoami` doesn't exist on the CLI.** The MCP server exposes a
  `whoami` tool (per ARCHITECTURE / phase 3 notes), but the CLI doesn't have
  a parallel command. Minor — `--author` is required on every write anyway —
  but a parallel CLI command would help agents self-orient.
- **No `cairn collaborator remove` (or `rm`/`delete`) subcommand.** The work
  backlog itself says "manually clean up by editing collaborators.yaml" — i.e.
  the backlog already knows there's no removal command. That's fine for now
  but is friction.
- **`branch` vs `exploration` in JSON output.** `cairn status --json` returns
  a `branch` key with value `"current"` and a `git_branch` key with value
  `"master"`. ADR-0008 calls for renaming user-facing "branch" → "exploration".
  This is in the backlog as a known TODO (`--branch` flag rename), but the
  JSON field naming is part of the same drift.
- **Finding filenames truncate mid-word at 60 chars.** This is documented as
  expected behaviour, but mid-word truncation (e.g. `relevant-to-base` for
  `relevant-to-baseline`) does produce filenames that read oddly. The fix
  (no trailing hyphen) is the right minimum; a tokeniser that backs off to
  the last word boundary inside the budget would be nicer. Not blocking.
- **`cairn finding add` does not return a finding id.** The output is "Logged
  finding at <path>." — useful, but if the orchestrator wants to refer to
  this finding from a later `--related` flag, it has to derive an id from
  the filename (`F-2026-05-23-<slug>`). Knowing whether the canonical
  reference is the filename, a `F-` prefix, or a sha would help.
- **`cairn decision add` printed the related list but not the file path.**
  Output: `Recorded D-002 in state/decisions.yaml; related: Q-001.` In
  contrast to `finding add`, which prints a full relative path. The
  inconsistency is mild but I noticed it.
- **No prompt confirmed default routing.** I never had to choose between
  cairns, so cwd routing was invisible-but-correct. If a project repo were
  ever paired with multiple cairns, I'd want the CLI to be explicit about
  which cairn it picked. Not an issue in this fixture.

## 9. Acceptance-criterion self-report

Scenario 1's A-criteria aren't restated in my work backlog. Based on the
backlog's task list and the implied fix-areas, here's my best read against
the F-01..F-03-style fixes the backlog hints at:

| Criterion | Your read | Evidence (task #, tool call, file path) |
|-----------|-----------|-----------------------------------------|
| A1 — registry shows both cairns | pass | Task 1, `cairn registered` output |
| A2 — `cairn status` from project repo cwd works (regression target) | pass | Task 2, output matched stated baseline |
| A3 — finding write to paired cairn via cwd | pass | Task 3, file at `cairns/lit-monitor/knowledge/findings/2026-05-23-coral-reefs-journal-rss-feed-is-unreliable.md` |
| A4 — decision write with `--related` | pass | Task 4, D-002, related Q-001 |
| A5 — cross-cairn write by cwd, slug no longer has trailing hyphen | pass | Task 5, slug ends `-base` (60 chars exactly) |
| A6 — orient / validate / collaborator add work from project repo cwd | pass | Tasks 7, 9, 11 |

I'm not graded on these; the orchestrator has the canonical list.

## 10. Additional observations

- The lit-monitor fixture had a pre-seeded finding
  (`2026-05-23-methods-comparison-paper-arxiv-2403-04567-is-worth-a-closer.md`)
  on disk despite the work backlog stating the baseline was "0 findings." Either
  the backlog is slightly stale or the fixture-prep step seeded an extra file
  after the baseline was written. Worth checking before the orchestrator counts
  deltas.
- Both pre-seeded files in lit-monitor and coral-bleach use the 60-char
  truncated slug convention (`...is-worth-a-closer`, `...througho`, etc.) — so
  the fix-for-trailing-hyphen behaviour appears consistent across already-seeded
  data too, not just new writes.
- `cairn status` showing `Active explorations: none` is reassuring, but if the
  ADR-0008 rename ever lands, the JSON `branch` field will need to be renamed
  in lockstep or downstream tooling will break.
- The `Git: master @ <sha> — "<last commit>"` line in `cairn status` is great
  for orientation — confirms which sha I'm anchored to without a separate
  `git log` call.

## 11. End-of-run state

- Last successful tool call: `cairn collaborator add --id testperson ...` on
  lit-monitor (then manually rolled back by editing collaborators.yaml).
- Did I complete every task in the backlog? Yes, tasks 1–11.
- Final write count from this sub-agent's session:
  - decisions=1 (D-002 on lit-monitor)
  - findings=2 (1 on lit-monitor, 1 on coral-bleach)
  - actions=0
  - open_questions=0
  - collaborators=+1 then −1 (testperson, added then manually removed; net 0)
- Final on-disk counts after cleanup:
  - lit-monitor: collaborators=2, decisions=2, open_questions=1, findings=2,
    actions=0
  - coral-bleach: collaborators=2, decisions=2, open_questions=1, findings=4,
    actions=0
