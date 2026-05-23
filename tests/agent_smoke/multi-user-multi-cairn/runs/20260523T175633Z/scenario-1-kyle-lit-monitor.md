# Sub-agent feedback — scenario-1 / Kyle on lit-monitor

## 1. Identity

- Sub-agent role: Kyle on lit-monitor
- Collaborator id used for writes: kyle
- Working directory: `/tmp/cairn-run-20260523T175633Z/projects/lit-monitor/` (the paired project repo; the cairn itself lives at `/tmp/cairn-run-20260523T175633Z/cairns/lit-monitor/`)
- Cairn(s) reachable from this session: `lit-monitor`, `coral-bleach` (both via the user-level registry at `/tmp/cairn-run-20260523T175633Z/config/cairn/server.toml`)
- Transport: CLI only (no MCP server stood up in this slice — the task explicitly notes "you're exercising the CLI routing surface, not the MCP-tool layer")
- Endpoint (if http): n.a.

## 2. Environment sanity check

- `whoami()` (no cairn param) returned: n.a. — this run used the local `cairn` CLI, not the MCP server. There is no `cairn whoami` command in the CLI surface (`cairn --help` lists no such command). The closest analogue would be reading `state/collaborators.yaml`, which I did not need to do.
- `status()` for each reachable cairn, run from the cairn directory directly:
  - `lit-monitor` (pre-write baseline): collaborators=2 (kyle, priya), goals=0, decisions=1, open_questions=1, findings=0. Matches the backlog's claim ("1 decision, 0 findings, 1 open question, 2 collaborators").
  - `coral-bleach` (pre-write baseline, not run before writes — checked only after my write; counts post-write listed under task 6).
- Surprises in baseline:
  - **The CLI does not honour `cairn.toml` for read-only commands like `cairn status`.** Running `cairn status` from `/tmp/cairn-run-20260523T175633Z/projects/lit-monitor/` (which has a `cairn.toml` with `[cairn] name = "lit-monitor"`) errors with `error: no cairn found at or above /tmp/cairn-run-20260523T175633Z/projects/lit-monitor`. I had to `cd` into `/tmp/cairn-run-20260523T175633Z/cairns/lit-monitor/` to get a status readout.
  - **By contrast, write commands (`cairn finding add`, `cairn decision add`) DO honour `cairn.toml`.** Same cwd, same shell, opposite behavior. Major routing inconsistency — see section 7.
  - There is no `cairn --version` flag (got `No such option '--version'`). The help screen lists `cairn version` as a subcommand; I should have used that. Minor papercut but the backlog instructed me to use `--version`.

## 3. Work backlog completion

### Task 1: Confirm registry visibility

- Intended: list cairns in the user-level registry; both `lit-monitor` and `coral-bleach` should appear.
- Tool call(s) made: `cairn registered`
- Result: success. Output shows both cairns with absolute paths to their cairn dirs (`/tmp/cairn-run-20260523T175633Z/cairns/{lit-monitor,coral-bleach}`).
- Entity id allocated: n.a.
- Author / raised_by / assignee parameter: n.a.
- Cross-references in `related`: n.a.
- Notable: clean output, points to the registry TOML path explicitly, which I found helpful.

### Task 2: Confirm pairing from lit-monitor project repo

- Intended: `cairn status` from the project repo should report the pre-seeded counts.
- Tool call(s) made: `cd /tmp/cairn-run-20260523T175633Z/projects/lit-monitor/ && cairn status`
- Result: **error** — `error: no cairn found at or above /tmp/cairn-run-20260523T175633Z/projects/lit-monitor` (exit 2).
- Workaround: ran the same command after `cd`-ing into the cairn dir (`/tmp/cairn-run-20260523T175633Z/cairns/lit-monitor/`). Got the expected 2/0/1/1 baseline.
- Notable: this is the headline routing finding. `cairn.toml` advertises the pairing but `cairn status` doesn't follow it.

### Task 3: Log a finding to the paired cairn

- Intended: write a finding to `lit-monitor` from the paired project repo cwd.
- Tool call(s) made (from `/tmp/cairn-run-20260523T175633Z/projects/lit-monitor/`):
  `cairn finding add --author kyle --title "Coral Reefs journal RSS feed is unreliable" --body "Items arrive 2 to 3 weeks late; we should add a polling fallback."`
- Result: success. Output: `Logged finding at knowledge/findings/2026-05-23-coral-reefs-journal-rss-feed-is-unreliable.md.`
- File path captured: `/tmp/cairn-run-20260523T175633Z/cairns/lit-monitor/knowledge/findings/2026-05-23-coral-reefs-journal-rss-feed-is-unreliable.md`
- Author parameter passed: `kyle`
- Cross-references in `related`: none for this finding.
- Notable: surprising that this *did* work from the project repo even though `cairn status` in the same cwd doesn't. The output also reports the path *relative to the cairn root*, not absolute and not relative to my cwd — slight ambiguity ("knowledge/findings/..." with no leading path means I had to `find` to confirm where it landed).

### Task 4: Record a decision

- Intended: log a decision with the RSS finding as context and a cross-ref to Q-001.
- Tool call(s) made (same cwd as task 3):
  `cairn decision add --author kyle --text "Add a polling fallback for RSS feeds older than 7 days" --context "RSS unreliability finding logged above." --related Q-001`
- Result: success. Output: `Recorded D-002.`
- Entity id allocated: **D-002**
- Author parameter passed: `kyle`
- Cross-references in `related`: `Q-001`
- Notable: the success message gives me the id (D-002) but not the file path, while `cairn finding add` gives me the path but not an id. Asymmetric.

### Task 5: Cross-cairn write to coral-bleach

- Intended: write a finding to `coral-bleach` from coral-bleach's project repo cwd.
- Tool call(s) made:
  `cd /tmp/cairn-run-20260523T175633Z/projects/coral-bleach/ && cairn finding add --author kyle --title "Transect-methodology paper (arxiv 2403.04567) relevant to baseline debate" --body "Connects to coral-bleach Q-001 on baseline-year choice."`
- Result: success. Output: `Logged finding at knowledge/findings/2026-05-23-transect-methodology-paper-arxiv-2403-04567-relevant-to-base.md.`
- File path captured: `/tmp/cairn-run-20260523T175633Z/cairns/coral-bleach/knowledge/findings/2026-05-23-transect-methodology-paper-arxiv-2403-04567-relevant-to-base.md`
- Author parameter passed: `kyle`
- Cross-references in `related`: none (the body text mentions Q-001 but I did not pass `--related Q-001` because the backlog didn't say to).
- Notable: the slug got truncated mid-word ("relevant-to-base" instead of "relevant-to-baseline-debate") — looks like a slug-length cap. Not an error, just a slightly ugly filename.

### Task 6: Confirm cross-cairn read

- Intended: run `cairn status` from each repo and compare counts.
- Tool call(s) made: `cairn status` from each project repo, then `cairn status` from each cairn dir (workaround).
- Result from the project repos: both errored with `no cairn found at or above ...` (same routing bug as task 2).
- Result from the cairn dirs:
  - `coral-bleach`: collaborators=2 (kyle, lila), goals=0, decisions=2, open_questions=1, findings=3. Last commit message references my Transect-methodology finding.
  - `lit-monitor`: collaborators=2 (kyle, priya), goals=0, decisions=2, open_questions=1, findings=2. Last commit message is `D-002: Add a polling fallback for RSS feeds older than 7 days`.
- Counts differ (3 findings vs 2 findings, different collaborator sets, different recent-decision lists). Yes, they differ in the expected ways.
- Notable: lit-monitor lists a finding I did not write — "Methods-comparison paper (arxiv 2403.04567) is worth a closer read". Either it was pre-seeded under a different label or written by the other sub-agent. Worth the orchestrator checking attribution (the file frontmatter will show author).

### Task 7: Sanity check JSON output

- Intended: confirm `--json` returns a structured payload of the same shape (with proper counts).
- Tool call(s) made: `cairn status --json` from `/tmp/cairn-run-20260523T175633Z/cairns/lit-monitor/`
- Result: success. JSON includes `decision_count=2`, `finding_count=2`, `open_question_count=1`, `collaborator_count=2`, `recent_decisions` with D-001/D-002, `recent_findings` with both finding paths. Branch field is `"branch": "current"` (interesting — see section 5 / section 10).
- Notable: shape looks clean; consistent with the text rendering.

### Task 8: Error message check outside any paired cwd

- Intended: capture verbatim error wording when no cairn is reachable from cwd.
- Tool call(s) made: `cd /tmp && cairn finding add --author kyle --title "test" --body "test"`
- Result: **error**, exit code 2. Verbatim error: `error: no cairn found at or above /tmp`
- Notable: error is terse and does not mention `cairn.toml`, `cairn link`, or the registry. A new user would not learn from this message that they could pair the directory with `cairn link` or `cd` into a registered cairn. Same wording I saw in task 2 — so the message doesn't distinguish "you're in a project repo with a pointer that I'm ignoring" from "you're in a totally unrelated directory". That's a UX miss.

## 4. Identity consistency

- Did you ever feel uncertain about which user you were supposed to be? **no** — the prompt and every task said `kyle`, and `--author kyle` is just a literal arg.
- Did any tool response refer to you under a different identity? **no**.
- `whoami()` multiple calls consistent? n.a. — no MCP layer in this slice; CLI has no `whoami`.

## 5. Cairn-routing observations (scenario 1)

- "To the project this repo is paired with": I did *not* pass a `--cairn` parameter — the CLI surface doesn't accept one. I relied on cwd-based default routing. For writes, this worked (`cairn.toml` was honoured). For `cairn status`, it failed (`cairn.toml` was ignored). That asymmetry is the central routing finding.
- "When the task named a specific other cairn": I switched cwd into the other project repo (`coral-bleach`) and the write worked. I did not get a chance to test an explicit `--cairn=...` flag because no CLI command exposes one.
- Did I ever try to write to a cairn name the server rejected? **no** — there is no server in this slice and no way to address a cairn by name from the CLI.
- Did any read return data that looked like it was from the wrong cairn? **no**. lit-monitor's status referenced one finding I didn't write ("Methods-comparison paper..."), but that's in the lit-monitor cairn so it's correct routing — just a write I can't attribute to my session.

## 6. Concurrency observations (scenario 2 only)

n.a. — this is scenario 1.

## 7. Errors and surprises

1. `cairn status` (from `/tmp/cairn-run-20260523T175633Z/projects/lit-monitor/`):
   `error: no cairn found at or above /tmp/cairn-run-20260523T175633Z/projects/lit-monitor`
   **Unhelpful**: same cwd successfully writes via `cairn finding add` and `cairn decision add`, which means a `cairn.toml` pointer IS being detected by some commands. The error message doesn't acknowledge the pointer at all. A user would reasonably think the pairing is broken when in fact only the read commands ignore it.

2. `cairn status` (from `/tmp/cairn-run-20260523T175633Z/projects/coral-bleach/`):
   `error: no cairn found at or above /tmp/cairn-run-20260523T175633Z/projects/coral-bleach`
   Same bug as #1, mirrored on the other repo.

3. `cairn finding add` (from `/tmp`):
   `error: no cairn found at or above /tmp`
   Expected behavior, but the message could suggest `cairn registered` or `cairn link` as remediation. As written it's a dead end.

4. `cairn --version`:
   `No such option '--version'.`
   Backlog explicitly told me to verify with `cairn --version`. The CLI uses the subcommand form `cairn version`. Minor, but the backlog's verification step doesn't work as written.

## 8. UX friction

- Asymmetric command output: `cairn finding add` reports the file path but no entity id (findings don't have F-NNN ids, fine); `cairn decision add` reports the id (`D-002`) but no file path. To verify either write I had to either `find` the file or `cairn status` the cairn. A single line like `Recorded D-002 at state/decisions.yaml` would close the loop.
- No `--cairn <name>` flag on any write command. The CLI assumes cwd-based routing, which is fine until cwd routing is inconsistent (see #7). A workaround for users in a non-paired shell would be either `cd` into the cairn or the project repo — but currently only `cd` into the cairn works for `cairn status`.
- `cairn status` and `cairn finding add` disagreeing on what counts as "inside a cairn" is the biggest mental-model break of the run. I had to discover by trial that writes work where reads don't.
- The slug for the cross-cairn finding got truncated to `...relevant-to-base.md`, losing meaningful trailing tokens. Looks like a fixed character cap rather than a word-boundary cap. Cosmetic, but the filename is the user-facing handle for the finding.
- `cairn status --branch` flag name conflicts with the ADR-0008 rename ("branch" → "exploration"). The CLAUDE.md backlog notes this is already known.

## 9. Acceptance-criterion self-report

The scenario acceptance criteria (A1–A6) weren't included in my prompt, but inferring from the backlog tasks:

| Criterion (inferred) | My read | Evidence |
|---|---|---|
| A1: both cairns visible in registry from one config | pass | Task 1 — `cairn registered` lists both. |
| A2: paired-cwd write routes to the right cairn | pass | Task 3 — finding landed at `cairns/lit-monitor/knowledge/findings/...`. |
| A3: cross-cairn writes are isolated (no leak) | pass | Task 5 — coral-bleach finding landed under `cairns/coral-bleach/...`, lit-monitor counts unaffected by it. |
| A4: paired-cwd read works | **fail** | Task 2 + Task 6 — `cairn status` errors despite a valid `cairn.toml`. |
| A5: JSON output is structurally sane | pass | Task 7 — all expected fields present. |
| A6: clear errors when no cairn is reachable | partial | Task 8 — error is terse; doesn't suggest `cairn link` / `cairn registered`. Identical wording to the false-negative case in A4, which makes it impossible to distinguish a real-misconfig from a routing-bug locally. |

## 10. Additional observations

- The `cairn.toml` pointer's actual contract is unclear from the user-facing tooling. `cairn link --help` says "Pair a project repo with a cairn by writing a cairn.toml pointer" and `cairn finding add` honors it — but `cairn status` doesn't. Either the pointer is for the MCP layer only (in which case `cairn finding add` should not honor it either, or should print which cairn it resolved to) or it's for all cwd-aware commands (in which case `cairn status` should honor it). Pick one.
- A potentially-helpful enhancement: when a CLI command resolves a cairn via `cairn.toml`, print a one-line "→ resolved cairn 'lit-monitor' at /tmp/.../cairns/lit-monitor" header (perhaps gated on a verbosity flag). Right now writes succeed silently and there's no way to know which cairn ate the write without inspecting state files.
- The `cairn status` JSON includes `"branch": "current"` — a literal string "current", not the actual branch. Probably the human-facing label leaking into the JSON; from the JSON I'd have expected either the git branch (`"master"`, which is also there as `git_branch`) or the exploration name. Not blocking, just odd.
- lit-monitor's recent_findings includes a finding ("Methods-comparison paper (arxiv 2403.04567) is worth a closer read") that I didn't write — its author per the frontmatter will tell the orchestrator whether the other sub-agent wrote to the wrong cairn or whether it was pre-seeded.
- The error wording `error: no cairn found at or above <path>` is identical for "I really searched and there's no cairn" and "I deliberately did not check cairn.toml". That's the bug that hurts most when debugging.

## 11. End-of-run state

- Last successful tool call: `cairn status --json` (from `/tmp/cairn-run-20260523T175633Z/cairns/lit-monitor/`)
- Did you complete every task in the backlog? **yes**, all 8 tasks. Tasks 2 and 6 only succeeded after a cwd workaround (running from the cairn dir rather than the paired project repo).
- Final write count (by me, this session):
  - lit-monitor: decisions=+1 (D-002), findings=+1 (`coral-reefs-journal-rss-feed-is-unreliable.md`), actions=0, open_questions=0
  - coral-bleach: decisions=0, findings=+1 (`transect-methodology-paper-arxiv-2403-04567-relevant-to-base.md`), actions=0, open_questions=0
- Final absolute counts per `cairn status` at end of run:
  - lit-monitor: decisions=2, findings=2, open_questions=1, collaborators=2, actions=0
  - coral-bleach: decisions=2, findings=3, open_questions=1, collaborators=2, actions=0
