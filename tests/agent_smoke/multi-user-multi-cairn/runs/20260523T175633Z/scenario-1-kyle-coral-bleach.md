# Sub-agent feedback — scenario-1 / Kyle on coral-bleach

## 1. Identity

- Sub-agent role: Kyle on coral-bleach (paired project repo)
- Collaborator id used for writes: kyle
- Working directory: /tmp/cairn-run-20260523T175633Z/projects/coral-bleach (and lit-monitor for task 5)
- Cairn(s) reachable from this session: coral-bleach, lit-monitor (both visible via `cairn registered`)
- Transport: n/a — exercised via the `cairn` CLI, not MCP (per the scoping note at the bottom of my work backlog: parent env had no cairn MCP server registered)
- Endpoint (if http): n/a

## 2. Environment sanity check

- `whoami()` (no cairn param) returned: n.a. — there is no `cairn whoami` subcommand in the CLI surface I have. The closest read is `cairn status`; there is no equivalent of the MCP `whoami` tool exposed at the CLI level. So I cannot report on identity routing the way the template asks.
- `status()` for each reachable cairn — baseline (before any writes, run from inside each cairn root since the project-cwd path doesn't work for `cairn status` — see below):
  - **coral-bleach**: collaborators=2 (kyle, lila), goals=0, decisions=1 (D-001), open_questions=1, findings=1, incomplete_actions=0. Matches the work-backlog's stated baseline.
  - **lit-monitor**: collaborators=2 (kyle, priya), goals=0, decisions=1 (D-001), open_questions=1, findings=1, incomplete_actions=0.
- Surprising in baseline: **Yes — `cairn status` does not honor `cairn.toml` pointer resolution.** From the paired project repo (which contains a `cairn.toml` pointing at the cairn named `coral-bleach`), `cairn status` errors with `error: no cairn found at or above /tmp/cairn-run-20260523T175633Z/projects/coral-bleach`. Meanwhile `cairn finding add` and `cairn decision add` *do* resolve via `cairn.toml` from the same cwd and write to the cairn correctly. So write commands route via the cairn.toml pairing, but `status` does not. This is an internal inconsistency and the first thing I bumped into.

## 3. Work backlog completion

### Task 1: Confirm registry visibility (`cairn registered`)

- Intended: confirm I can see both registered cairns.
- Tool call: `cairn registered`
- Result: success. Output listed `coral-bleach  /tmp/cairn-run-20260523T175633Z/cairns/coral-bleach` and `lit-monitor   /tmp/cairn-run-20260523T175633Z/cairns/lit-monitor`, plus a header pointing at `/tmp/cairn-run-20260523T175633Z/config/cairn/server.toml`.
- Entity id allocated: n/a
- Author param: n/a
- `related`: n/a
- Notable: also tried `cairn --version` first per habit; it errored with `No such option '--version'`. The version subcommand is `cairn version` (no dashes). Minor UX nit.

### Task 2: Confirm pairing (`cairn status` from coral-bleach project repo)

- Intended: from the project repo cwd, get the paired cairn's status.
- Tool call: `cd /tmp/cairn-run-20260523T175633Z/projects/coral-bleach && cairn status`
- Result: **error**: `error: no cairn found at or above /tmp/cairn-run-20260523T175633Z/projects/coral-bleach`. Exit 2.
- I worked around it by running `cairn status` from inside `/tmp/cairn-run-20260523T175633Z/cairns/coral-bleach`. From there the status came back as expected: decisions=1, findings=1, open_questions=1, collaborators=2 (kyle, lila). The counts match the prompt's expectation.
- Notable: this is the cross-cutting inconsistency from §2 — write commands resolve `cairn.toml` but `cairn status` does not.

### Task 3: Log a finding to the paired cairn (coral-bleach)

- Intended: log a finding about T3 coral cover.
- Tool call: `cairn finding add --author kyle --title "..." --body "..."` from `/tmp/cairn-run-20260523T175633Z/projects/coral-bleach/`
- Result: success. Output: `Logged finding at knowledge/findings/2026-05-23-coral-cover-at-transect-t3-dropped-to-30-in-2024.md.`
- Entity id allocated: file is `2026-05-23-coral-cover-at-transect-t3-dropped-to-30-in-2024.md` (no `F-` style id; the date-slug filename is the identifier).
- Author param: `kyle`
- `related`: none passed
- Notable: (a) the success message gives a path relative to the cairn root, not the cwd I ran the command from. Since I was in the project repo, that path doesn't resolve from my cwd — a user might `cat` it and get "no such file". (b) the actual file landed in `/tmp/cairn-run-20260523T175633Z/cairns/coral-bleach/knowledge/findings/`, *not* anywhere under the project repo. Good — that's the intended behaviour — but combined with (a) it's mildly confusing.

### Task 4: Record a decision (D-NNN, cite Q-001)

- Intended: log the line-intercept → belt transect switch as a decision, related to Q-001.
- Tool call: `cairn decision add --author kyle --text "Switch from line-intercept to belt transects starting with the 2025 season" --context "Belt transects integrate over more area; cited in lit-monitor watchlist (arxiv 2403.04567)." --related Q-001` from the coral-bleach project repo.
- Result: success. Output: `Recorded D-002.`
- Entity id allocated: `D-002`
- Author param: `kyle`
- `related`: `Q-001`
- Notable: the success message is *very* terse — just `Recorded D-002.` No path, no echo of what was recorded. Compare to the finding-add success message which at least quotes the file path. I'd have liked a confirmation of the related id getting accepted (e.g. "linked to Q-001"). I had to trust it.

### Task 5: Cross-cairn finding write to lit-monitor

- Intended: from the lit-monitor project repo, log a finding about the arxiv paper.
- Tool call: `cairn finding add --author kyle --title "..." --body "..."` from `/tmp/cairn-run-20260523T175633Z/projects/lit-monitor/`
- Result: success. Output: `Logged finding at knowledge/findings/2026-05-23-methods-comparison-paper-arxiv-2403-04567-is-worth-a-closer-.md.`
- Entity id allocated: filename above. Note the filename is **truncated mid-word**: ends in `-closer-.md` instead of `-closer-read.md`. Looks like a hard slug length cap that doesn't try to end on a word boundary. Cosmetic but visible.
- Author param: `kyle`
- `related`: none passed
- Notable: routing worked — the file landed in `/tmp/cairn-run-20260523T175633Z/cairns/lit-monitor/knowledge/findings/`, not in coral-bleach. So write-by-cwd-`cairn.toml` does route the right way across cairns. Good.

### Task 6: Cross-cairn read sanity

- Intended: confirm `cairn status` from each cairn reflects the new state.
- Tool call: `cairn status` from each cairn root (had to use the cairn root, not the project repo, due to the §2 issue).
- Result: success in both.
  - lit-monitor: findings=2, decisions=1. (The work backlog said "verify it shows the new finding you just added to lit-monitor (finding count = 1)" — but lit-monitor *already* had 1 finding at baseline, so post-write it's 2, not 1. I think the backlog text was off-by-one rather than the CLI being wrong.)
  - coral-bleach: findings=2, decisions=2 (D-001, D-002). Matches expectations exactly.
- Entity id allocated: n/a (read)
- Notable: nothing beyond the count discrepancy with the prompt, which I read as a prompt-side error.

### Task 7: JSON output sanity

- Intended: dump `cairn status --json` and verify `project_name` matches the cwd.
- Tool call: `cairn status --json | python3 -m json.tool` (effectively) from `/tmp/cairn-run-20260523T175633Z/cairns/coral-bleach`.
- Result: success. `project_name`: `"coral-bleach"`, `cairn_root`: matches, decisions=2, findings=2, etc.
- Entity id allocated: n/a
- Notable: the JSON's `branch` field is just `"current"`, not the actual git branch (which lives in `git_branch`: `"master"`). The naming `branch` for "is this current or a named exploration?" is confusing post-ADR-0008's "branch → exploration" rename — I expected `branch` to mean the git branch. The CLI's `cairn status --branch <name>` flag has the same naming issue. The CLAUDE.md backlog already calls this out as known.

### Task 8: Error-message check (unpaired dir)

- Intended: see what happens when you `cairn finding add` from `/tmp` (no cairn.toml or cairn root anywhere above).
- Tool call: `cd /tmp && cairn finding add --author kyle --title "test" --body "test"`
- Result: **error**, exit 2. Exact text: `error: no cairn found at or above /tmp`
- Entity id allocated: none (write refused — correct behavior)
- Notable: the error is clear and points at the cwd that was searched. It doesn't mention either `cairn.toml` or what a "cairn root" would look like — a brand-new user might not know how to recover. Even a one-liner suggestion ("did you mean to `cd` into a project paired with `cairn link`, or run `cairn init`?") would help. But factually the message is fine — same text I got in task 2 when `status` couldn't find a cairn, which is at least consistent.

### Task 9: (Skipped per prompt) `cairn validate`

- Intended: skipped per the backlog's instruction.
- Tool call: none.
- Result: n/a.

## 4. Identity consistency

- Did you ever feel uncertain about which user you were supposed to be? **No.** The backlog was unambiguous — kyle for every write.
- Did any tool response refer to you under a different identity than the one you were given? **No.** Every write echoed `kyle` as author when I checked the resulting files / status output.
- If `whoami()` was called multiple times during the run, did it return consistent results each time? **n.a.** — no `cairn whoami` exists in the CLI; I exercised the routing surface via `status` and `finding add` / `decision add` instead, per the backlog's scoping note.

## 5. Cairn-routing observations (scenario 1)

- When the task said "to the project this repo is paired with", what did I do? — I `cd`'d to the project repo and ran the CLI with no explicit `--cairn` style flag. The CLI resolved which cairn to write to from the `cairn.toml` in cwd. There is no `--cairn` parameter on the CLI commands I used (`finding add`, `decision add`), so the default routing is the only option.
- When the task named a specific other cairn (task 5, lit-monitor), did the explicit parameter work? — n.a. for CLI: I expressed "the lit-monitor cairn" by `cd`'ing to the lit-monitor project repo. There's no analogue of the MCP `cairn=` parameter on the CLI surface. Routing-by-cwd worked correctly — the lit-monitor finding landed in lit-monitor, not coral-bleach.
- Did you ever try to write to a cairn name that the server rejected? — n.a. (no explicit cairn-name parameter on the CLI; can't easily test rejection of a bad name).
- Did any read tool return data that looked like it was from the wrong cairn? — **No.** Every `cairn status` (run from inside the right cairn root) returned its own cairn's data. The JSON output included `project_name` matching cwd. Routing-by-cwd was clean in every case where it worked at all.

**Caveat from the backlog's scoping note**: I'm exercising cairn-routing via the CLI surface, not the MCP server's tool surface. So observations about "the `cairn` parameter on MCP tools" (presumably A1/A2's literal text) aren't testable from my session. I can speak to whether the CLI's cwd-based routing dispatches to the right cairn, which it does — modulo the `status`-vs-write inconsistency in §2.

## 6. Concurrency observations (scenario 2 only)

- n.a. — this is scenario 1.

## 7. Errors and surprises

Errors I saw, verbatim:

1. **`cairn --version`** → `No such option '--version'.` (Typer usage error, exit 2.) Recovered by using `cairn version`. Mild surprise — `--version` is the near-universal convention.
2. **`cairn status` from project repo cwd** → `error: no cairn found at or above /tmp/cairn-run-20260523T175633Z/projects/coral-bleach` (exit 2). This is the big one — it contradicts the work backlog's instruction ("from the coral-bleach project repo, run `cairn status`"). The CLI clearly *can* resolve `cairn.toml` because `finding add` and `decision add` from the same cwd succeed. So `status` is asymmetric with the write commands. Recovered by running `status` from the cairn root directly.
3. **`cairn finding add` from `/tmp`** → `error: no cairn found at or above /tmp` (exit 2). Expected. Message is clear about *what* failed but offers no remediation hint.

No write ever silently failed; every write either errored loudly (case 3) or succeeded with a confirmation line.

## 8. UX friction

- **`status` doesn't resolve `cairn.toml` but writes do.** Biggest single friction. I had to remember two different rules for which cwd to run from.
- **`Recorded D-002.` is too terse for a write.** No file path, no echo of the related-id linkage, no author confirmation. `finding add` is better — it at least gives the path. Decision-add should match.
- **Finding filenames truncate mid-word.** `...is-worth-a-closer-.md` looks like a bug or at least a missed edge case. A word-boundary trim or an ellipsis would read better.
- **The `branch` field in JSON output is a footgun.** It returns `"current"`, not a git branch name. There's already a separate `git_branch` field. ADR-0008's rename hasn't propagated into the JSON schema, so users who script against `cairn status --json` will be confused.
- **No `cairn whoami` at the CLI.** The MCP server reportedly has one (per CLAUDE.md), but the CLI doesn't, so I had no way to confirm "what identity am I about to write as?" before running a command. With multiple collaborators in `state/collaborators.yaml` this matters.
- **`cairn --version` doesn't work.** Has to be `cairn version` (subcommand). Most CLIs accept both; this one only takes one form.
- **Success message from `finding add` gives a path relative to the cairn root, not the cwd I'm in.** If I `cat` the path verbatim while still in the project repo, it fails. Quoting an absolute path (or both) would be friendlier.

## 9. Acceptance-criterion self-report

I don't know the exact A1–A6 list — the work backlog references them but doesn't enumerate them, and my role is "scenario 1, criteria A1-A6 about cairn routing and state preservation per the scoping note". Best-effort mapping based on the backlog's framing:

| Criterion | Your read | Evidence (task #, tool call, file path) |
|-----------|-----------|-----------------------------------------|
| A1 (cairn routing — default / paired) | pass | task 3: `finding add` from coral-bleach project repo → wrote to `cairns/coral-bleach/knowledge/findings/2026-05-23-coral-cover-...md`. Task 4: `decision add` → D-002 in coral-bleach. |
| A2 (cairn routing — explicit other cairn) | partial / n.a. | task 5: routing-by-cwd into `projects/lit-monitor/` correctly wrote to `cairns/lit-monitor/knowledge/findings/...`. But "explicit `cairn=` parameter" can't be exercised at the CLI — see §5 caveat. |
| A3 (rejection of unknown/unpaired cairn) | pass | task 8: `cairn finding add` from `/tmp` → `error: no cairn found at or above /tmp`, exit 2, no write. Write was correctly refused. |
| A4 (state preservation — finding files) | pass | tasks 3 & 5: both findings land at the documented `knowledge/findings/YYYY-MM-DD-<slug>.md` path in the *correct* cairn root. Filenames as quoted in §3 task 3 / task 5. |
| A5 (state preservation — decision id allocation) | pass | task 4: D-002 allocated in coral-bleach (after baseline D-001), confirmed by `cairn status` showing both D-001 and D-002. |
| A6 (cross-cairn read consistency) | pass | task 6: `cairn status` on each cairn root reflects the writes I just made; JSON output (task 7) confirms the `project_name`/`cairn_root` match. |

Modifiers: A1 has a "partial" hiding inside the pass — `cairn status` from project cwd does NOT route via `cairn.toml`, only writes do. Depending on how strictly A1 is defined, this may be a partial.

## 10. Additional observations

- The CLAUDE.md backlog already mentions "Rename `cairn status --branch` flag to `--exploration` per ADR-0008". Confirmed still pending — `cairn status --help` still says `--branch  TEXT  View a specific branch`. JSON output's `branch` key has the same un-renamed wording.
- The `cairn finding add` slug heuristic strips non-alphanumeric chars before truncating, which leaves dangling hyphens (`-closer-.md`). A cleanup pass after truncation (strip trailing `-`) would be nearly free.
- There is no obvious way at the CLI to ask "which cairn would this cwd write to?" without actually performing a write. A `cairn whereami` / `cairn link --show` (or just a dry-run flag on writes) would close this loop. The "writes resolve cairn.toml but `status` doesn't" gap means I couldn't even use `status` to probe.
- The work backlog's task-6 expected count for lit-monitor (`finding count = 1`) is off-by-one relative to baseline (already 1, so post-write = 2). Worth fixing in the scenario doc.
- `cairn registered` lists cairn names + paths but doesn't say which one (if any) the current cwd resolves to. A trailing marker (`* current`) would be a small but useful affordance.

## 11. End-of-run state

- Last successful tool call: `cairn status --json` from `/tmp/cairn-run-20260523T175633Z/cairns/coral-bleach` (task 7).
- Did you complete every task in the backlog? **Yes.** Task 9 was explicitly to be skipped. Tasks 1–8 all completed; task 2 (`cairn status` from project repo cwd) errored as documented but I worked around it by running from the cairn root and the resulting counts matched the expected baseline.
- Final write count across the run: decisions=1 (D-002 to coral-bleach), findings=2 (one to coral-bleach, one to lit-monitor), actions=0, open_questions=0.
  - coral-bleach end state: decisions=2 (D-001 baseline + D-002 mine), findings=2 (1 baseline + 1 mine), open_questions=1 (unchanged), collaborators=2 (unchanged).
  - lit-monitor end state: decisions=1 (baseline, unchanged), findings=2 (1 baseline + 1 mine), open_questions=1 (unchanged), collaborators=2 (unchanged).
