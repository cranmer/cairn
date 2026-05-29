# Sub-agent feedback — scenario-1 / Kyle on coral-bleach

## 1. Identity

- Sub-agent role: Kyle on coral-bleach (scenario 1, one user / many cairns)
- Collaborator id used for writes: `kyle`
- Working directory: `/tmp/cairn-sc1-rUOm/projects/coral-bleach/` (primary), with cwd-changes to `/tmp/cairn-sc1-rUOm/projects/lit-monitor/` for the cross-cairn write and `/tmp` for the no-cairn-found test
- Cairn(s) reachable from this session: `coral-bleach`, `lit-monitor` (both via cwd-walk on `cairn.toml`)
- Transport: stdio (CLI direct; no MCP HTTP server in this scenario)
- Endpoint (if http): n/a

## 2. Environment sanity check

I had no `whoami()` tool to call — this scenario goes through the `cairn` CLI, not the MCP server. The CLI doesn't expose a top-level identity-print command; identity is supplied per-call via `--author <id>` and the project repos have git-config `user.email` already set to `kyle@example.com` / `Kyle` per the prompt frame.

`cairn registered` (from `/tmp/cairn-sc1-rUOm/projects/coral-bleach/`):

```
# Registered cairns (/tmp/cairn-sc1-rUOm/config/cairn/server.toml)
  coral-bleach  /tmp/cairn-sc1-rUOm/cairns/coral-bleach
  lit-monitor   /tmp/cairn-sc1-rUOm/cairns/lit-monitor
```

Baseline `cairn status` from each cairn root, **before any of my writes**:

- `coral-bleach`: collaborators=2 (kyle, lila), decisions=1, open_questions=1, findings=1, actions=0, git head = "Log finding: 2024 bleaching event extent across transects" @ 67c55ac.
- `lit-monitor`: collaborators=2 (kyle, priya), decisions=1, open_questions=1, findings=0, actions=0, git head = "D-001: Use arXiv API + journal RSS, not Google Scholar." @ 420df6e.

Nothing surprising in the baseline. The wrapper script at `/tmp/cairn-sc1-rUOm/bin/cairn` pins the venv + `XDG_CONFIG_HOME` cleanly; registry resolution worked out of the box.

## 3. Work backlog completion

### Task 1: Sanity check — confirm registration + capture baseline

- Intended: list registered cairns from the coral-bleach project repo, then `cairn status` inside each cairn root for baseline counts.
- Tool call(s) made: `cairn registered` from coral-bleach project repo; `cairn status` from `/tmp/cairn-sc1-rUOm/cairns/coral-bleach/` and `/tmp/cairn-sc1-rUOm/cairns/lit-monitor/`.
- Result: success.
- Entity id allocated: n/a (read-only).
- Author/raised_by/assignee parameter: n/a.
- Cross-references passed in `related`: n/a.
- Anything notable: `cairn registered` echoes the registry path (`/tmp/cairn-sc1-rUOm/config/cairn/server.toml`) and a 2-row table — clean output. Nothing here points back to the local `cairn.toml`, which is fine for "list registry contents" but means a confused user can't immediately tell "which of these will my cwd resolve to?" from `registered` alone. (See section 8.)

### Task 2: Default-routed finding from coral-bleach project repo

- Intended: log a finding titled "Coral cover dropped to ~30% in 2024 transects" with cwd at `/tmp/cairn-sc1-rUOm/projects/coral-bleach/`; no cairn-naming flag, rely on cwd resolution via `cairn.toml`.
- Tool call(s) made: `cairn finding add --author kyle --title "Coral cover dropped to ~30% in 2024 transects" --body "..."` — *no cairn-naming parameter*; the CLI doesn't expose one (see section 5).
- Result: success — `Logged finding at knowledge/findings/2026-05-24-coral-cover-dropped-to-30-in-2024-transects.md.` exit=0.
- Entity id allocated: `F-2026-05-24-coral-cover-dropped-to-30-in-2024-transects` (the filename slug acts as the id; there's no separate `F-NNN` printed).
- Author parameter passed: `kyle`.
- Cross-references passed in `related`: none (CLI flag exists, I didn't pass any).
- Anything notable: Landed at `/tmp/cairn-sc1-rUOm/cairns/coral-bleach/knowledge/findings/2026-05-24-coral-cover-dropped-to-30-in-2024-transects.md`, **not** in lit-monitor's findings dir. Frontmatter verbatim:

  ```yaml
  date: '2026-05-24T19:15:55Z'
  author: kyle
  title: Coral cover dropped to ~30% in 2024 transects
  slug: coral-cover-dropped-to-30-in-2024-transects
  related: []
  exploration: main
  source_commits: []
  source_prs: []
  ```

  The success message returns a path relative to the cairn root (`knowledge/findings/...`), not the absolute path. A user with two cairns side-by-side has to mentally resolve "which cairn root is this relative to?" — there's no name echoed back. (Section 8 / section 10.)

### Task 3: Default-routed decision from coral-bleach project repo

- Intended: record a decision about monthly transect sampling, from the same cwd.
- Tool call(s) made: `cairn decision add --author kyle --text "Switch to monthly transect sampling during bleaching season" --context "Quarterly sampling is missing the acute decline window in 2024."`.
- Result: success — `Recorded D-002 in state/decisions.yaml.` exit=0.
- Entity id allocated: `D-002`.
- Author parameter passed: `kyle`.
- Cross-references passed in `related`: none.
- Anything notable: The id `D-002` is sane — the baseline already had `D-001` (Adopt PIT-tagged colonies...). `state/decisions.yaml` in coral-bleach now has both; lit-monitor's `state/decisions.yaml` is untouched by my call. As above, the success message references `state/decisions.yaml` without naming the cairn — fine here only because there's no ambiguity about cwd, but again no name echo.

### Task 4: Cross-cairn write — finding to lit-monitor

- Intended: from inside the lit-monitor project repo, log a finding about a Hoegh-Guldberg paper. Acts as the A2 proxy since the CLI has no `--cairn` flag.
- Tool call(s) made: `cd /tmp/cairn-sc1-rUOm/projects/lit-monitor && cairn finding add --author kyle --title "The new Hoegh-Guldberg paper on bleaching is worth tracking" --body "..."`.
- Result: success — `Logged finding at knowledge/findings/2026-05-24-the-new-hoegh-guldberg-paper-on-bleaching-is-worth-tracking.md.` exit=0.
- Entity id allocated: filename slug `2026-05-24-the-new-hoegh-guldberg-paper-on-bleaching-is-worth-tracking`.
- Author parameter passed: `kyle`.
- Cross-references passed in `related`: none. Would have been natural to link it to my coral-bleach finding (F-...-coral-cover-dropped-to-30...), but cross-cairn `related` references aren't supported (and shouldn't be — that would break the substrate-as-specification invariant).
- Anything notable: Landed at `/tmp/cairn-sc1-rUOm/cairns/lit-monitor/knowledge/findings/2026-05-24-the-new-hoegh-guldberg-paper-on-bleaching-is-worth-tracking.md`. Frontmatter looks right (`author: kyle`, `exploration: main`). Importantly, **coral-bleach's findings dir was untouched by this call** — confirmed by listing before/after. The cwd-walk routing did its job.

### Task 5: No-cairn-found error from /tmp

- Intended: attempt a write from a directory with no `cairn.toml` anywhere upward; expect a clear error and non-zero exit.
- Tool call(s) made: `cd /tmp && cairn finding add --author kyle --title "ghost test" --body "should be rejected"`.
- Result: error — exit=2.
- Error text verbatim: `error: no cairn found at or above /tmp`
- Anything notable: Clear, actionable, includes the cwd that was searched. Exit code 2 (not 1) is standard-ish for "usage/lookup failure" in Typer/Click; fine. The message could be slightly better by hinting at the fix ("run `cairn link <cairn-name>` or `cd` into a paired project repo"), but as-is it's not confusing. No false positive — `/tmp` genuinely has no cairn.toml ancestor, and the CLI correctly refused.

### Task 6: Per-cairn read discrimination

- Intended: `cairn status` from each cairn root; counts and collaborator names must differ.
- Tool call(s) made: `cairn status` from `/tmp/cairn-sc1-rUOm/cairns/coral-bleach/` and `/tmp/cairn-sc1-rUOm/cairns/lit-monitor/`.
- Result: success — both differ as expected.
- Collaborator counts/names:
  - coral-bleach: `Collaborators: 2 (kyle, lila)`
  - lit-monitor:  `Collaborators: 2 (kyle, priya)`
- Anything notable: At this read (Task 6, after my Tasks 2–4), counts had **grown beyond what I wrote**. coral-bleach now showed `Decisions: 2, Findings: 3` and lit-monitor showed `Decisions: 2, Findings: 2`. That's not consistent with "my edits only" — a third finding appeared in coral-bleach ("The 2024 transect dataset is ready for cross-referencing with literature watch...") and a second decision (`D-002: Cache arXiv fetches for 6 hours...`) appeared in lit-monitor that I never wrote. That has to be the concurrent sub-agent B doing its home-cairn writes from the lit-monitor side and also writing a cross-cairn finding into coral-bleach. **This is not a routing bug** — the new files are correctly attributed to `kyle` and landed in the right cairns — but it's a confound for any test that wants to assert "Kyle's coral-bleach writes are the only changes to coral-bleach in this run". A reviewer reading just my sub-agent feedback would miscount if they assumed the only writes were mine.

### Task 7: Validate

- Intended: `cairn validate` from each cairn root; both must exit 0.
- Tool call(s) made: `cairn validate` in `/tmp/cairn-sc1-rUOm/cairns/coral-bleach/` and `/tmp/cairn-sc1-rUOm/cairns/lit-monitor/`.
- Result: both `OK`, both exit=0.
- Entity id allocated: n/a.
- Anything notable: Validate is terse — just `OK`. That's appropriate for the success path; would matter more on the failure path (not exercised here).

## 4. Identity consistency

- Did you ever feel uncertain about which user you were supposed to be? **No.** Identity was anchored by the per-call `--author kyle` flag and the cwd-paired project repo. There's no session-level identity in the CLI — each command takes `--author` explicitly — so the question doesn't really arise the way it would over MCP.
- Did any tool response refer to you under a different identity than the one you were given? **No.** Every written file's frontmatter shows `author: kyle`; the success messages don't echo identity at all.
- If `whoami()` was called multiple times during the run, did it return consistent results each time? **n/a** — `whoami()` is an MCP tool, not a CLI command. The CLI has no analogue; identity is per-call.

## 5. Cairn-routing observations (scenario 1 only)

- When the task said "to the project this repo is paired with", what did I do? Default routing via cwd — I ran the command from inside the project repo, and the CLI walked up to find the `cairn.toml`. No cairn-naming flag was passed (none exists on the CLI).
- When the task named a specific other cairn, did the explicit `cairn=<name>` parameter work as expected? **There is no `cairn=<name>` parameter on the CLI.** I worked around it the way the prompt directed: `cd` into the other project repo and let the cairn.toml walk resolve. That worked correctly — the cross-cairn finding landed in lit-monitor and not coral-bleach. **But: this is asymmetric with the MCP server's surface**, where `cairn=<name>` *is* the routing parameter. If the methodology's intent is "exercise A2 = explicit cairn-naming", the CLI cannot do that today — `cd`-then-call is a different mechanism (cwd-walk on a per-repo pointer file), not "explicit cairn name in the call". A user who wants to log a quick finding into a cairn they don't have cd'd to has no one-liner. The honest reporting per the prompt: A2's intent is *partially* covered — routing-by-cwd-pointer demonstrably works, but the "name a cairn from the outside" path isn't exercised.
- Did you ever try to write to a cairn name that the server rejected? **n/a** — no server, and no `--cairn` flag to mis-aim.
- Did any read tool (`status`, `whoami`, `get_open_questions`, etc.) return data that looked like it was from the wrong cairn? **No.** `cairn status` always reflected the cwd-resolved cairn; running it from the cairn root rather than the project root gave the expected per-cairn snapshot. No cross-contamination.

## 6. Concurrency observations (scenario 2 only)

n/a — this is scenario 1. (But see Task 6 above and section 10 — I did observe concurrent writes from sub-agent B during my session, just not as the scenario's focus.)

## 7. Errors and surprises

Errors actually encountered during the run:

1. `cairn finding add` from `/tmp` (no cairn.toml):

   - Tool: `cairn finding add`
   - Args: `--author kyle --title "ghost test" --body "should be rejected"` (cwd=/tmp)
   - Error text: `error: no cairn found at or above /tmp`
   - Exit: 2
   - Assessment: clear, helpful, expected. Not unclear.

No other errors. No retries. No hangs.

Surprises (non-error):

- Lit-monitor's `knowledge/findings/` was **not** empty at the time of Task 4 — it already had `2026-05-24-rss-poller-throughput-is-fine-for-biology-preprints-but-drop.md` even though my baseline read in Task 1 reported `Findings: 0`. So between Task 1 and Task 4, sub-agent B (working concurrently on lit-monitor) added at least one finding. Not a bug — just confirms the concurrent activity. Worth flagging because a careful reader of just my run might mis-attribute it.
- During Task 6's status read, an unexpected coral-bleach finding had appeared: `2026-05-24-the-2024-transect-dataset-is-ready-for-cross-referencing-wit.md`. This is sub-agent B's cross-cairn write into coral-bleach (the mirror of my Task 4 going the other direction). Correct behavior, but it confirms the two sub-agents are interleaved.

## 8. UX friction

- **No `--cairn` flag on the CLI.** The prompt explicitly flagged this as a known gap and asked me to note it honestly. It's a real friction point: when MCP exposes `cairn=<name>` as the routing primitive and the CLI exposes only "cd into the right place", users straddling both surfaces will trip. From a one-user / many-cairns workflow, this means: "log a finding into the cairn I'm not cd'd into" has no CLI one-liner. A `--cairn <name>` flag (resolved against `cairn registered`) would close this gap.
- **Success messages don't echo the cairn name.** `Logged finding at knowledge/findings/...` and `Recorded D-002 in state/decisions.yaml.` are both fine when cwd is unambiguous, but in a many-cairn world, echoing the resolved cairn (e.g. `Logged finding at coral-bleach:knowledge/findings/...` or `Recorded D-002 in coral-bleach/state/decisions.yaml.`) would defuse the "wait, which cairn did that just go into?" moment after a `cd`.
- **`cairn registered` doesn't show which is "current".** It lists all cairns in the registry but doesn't mark which one the current cwd resolves to. A `*` marker (or a separate `cairn current`) would help.
- **No CLI `whoami`.** Per-call `--author` works, but it means in a session where someone forgets to pass it the command fails with `Missing option '--author'.` rather than defaulting to the git-configured identity. The MCP server does identity inference; the CLI doesn't. Not blocking, but inconsistent.
- **Frontmatter `exploration: main` for findings on main.** Tiny nit — calling main "an exploration" reads a bit oddly. The semantics are clear from ADR-0008 (user-facing "exploration" vs underlying git "branch"), so this is fine, just worth noticing as a phrase that lands oddly when you're literally on the main branch and the field reads `exploration: main`.
- **Decision command takes `--text` for the decision body**, not `--decision`. Easy to type-guess wrong on first try (I had to check `--help`). Naming it `--decision` would match the YAML field name (`decision:`) and the entity name.

## 9. Acceptance-criterion self-report

| Criterion | My read | Evidence (task #, tool call, file path) |
|-----------|---------|-----------------------------------------|
| A1 | pass | Task 2: `cairn finding add` from `/tmp/cairn-sc1-rUOm/projects/coral-bleach/` with no cairn-name flag → landed at `/tmp/cairn-sc1-rUOm/cairns/coral-bleach/knowledge/findings/2026-05-24-coral-cover-dropped-to-30-in-2024-transects.md`, not in lit-monitor. Frontmatter `author: kyle`. Decision write in Task 3 (`D-002`) also routed correctly to coral-bleach. |
| A2 | partial | Task 4: cross-cairn write succeeded via `cd /tmp/cairn-sc1-rUOm/projects/lit-monitor && cairn finding add ...`, landed at `lit-monitor/knowledge/findings/2026-05-24-the-new-hoegh-guldberg-paper-on-bleaching-is-worth-tracking.md`. **But** the prompt's A2 names "a write addressed to the OTHER cairn", and the CLI has no `--cairn` flag — what I exercised is cwd-walk routing under a different pointer file, not naming-from-outside. Per the prompt frame this is the honest reading. The MCP-side equivalent (passing `cairn="lit-monitor"`) was not exercisable from the CLI surface. |
| A3 | pass | Task 5: `cd /tmp && cairn finding add ...` → `error: no cairn found at or above /tmp`, exit=2. Clear, non-zero, doesn't leave a partial write. |
| A4 | pass | Task 6: `cairn status` in coral-bleach reports collaborators `(kyle, lila)`; in lit-monitor reports `(kyle, priya)`. Different decision/finding counts and recent-decision contents. No cross-leakage. |
| A5 | pass | Same evidence as A4 — different "recent decisions" sections, different git heads, no shared state. (A4 and A5 in the prompt are both about per-cairn read discrimination — I read them as the same criterion split by entity type.) |
| A6 | pass | Section 4 — never confused about which cairn I was writing into. The cwd → cairn.toml → registry chain is intuitive once you have one cairn.toml per project repo. The only mental-model wobble was post-hoc, in Task 6, when status counts didn't match "what I wrote" — and that wobble was caused by concurrent activity from sub-agent B, not by routing confusion. |

## 10. Additional observations

- **The "scenario 1 is one user, many cairns" framing implicitly assumes interleaving with sub-agent B doesn't matter for my acceptance criteria, and that mostly holds — but only because I verified by reading the files I wrote, not by trusting the totals.** A future iteration of the methodology might want to snapshot the cairns' state files at sub-agent-spawn time and diff at sub-agent-end, so each sub-agent reports a clean per-agent write delta rather than a confounded total.
- **Sub-agent B wrote a finding into coral-bleach as `kyle`** (the "2024 transect dataset is ready for cross-referencing..." one). That means *attribution* alone doesn't distinguish "Kyle on coral-bleach (me)" from "Kyle on lit-monitor doing a cross-cairn write into coral-bleach". The git history (commit timestamps, commit messages) would, and so would the frontmatter `date` field at second-precision. If the methodology relies on attribution to slice writes per sub-agent, it should additionally key on commit hash or filename.
- **Frontmatter `date` is to second precision and ISO-8601-Z**, which is good. My two writes were at `19:15:55Z` (finding in coral-bleach) and `19:16:19Z` (finding in lit-monitor). My decision was at `19:16:07Z`. The cross-cairn finding from sub-agent B into coral-bleach was at a different second (visible by checking that file's frontmatter), so timeline reconstruction is feasible.
- **The CLI is fast.** Each `cairn finding add` / `decision add` returned in well under a second, including the git commit. Validate is also snappy. Nothing here suggests the CLI is the bottleneck for these workflows.
- **`cairn validate` exit semantics are clean.** Both `OK` exits were exit=0. Worth keeping that contract stable.
- **One ergonomic suggestion for `cairn status`**: include the resolved registry name + path at the top in a format that's grep-friendly. Today the first line is `Cairn 'coral-bleach' [/tmp/cairn-sc1-rUOm/cairns/coral-bleach]` — that's already good. The bigger gap is in the *write* commands echoing the cairn name (section 8).
- **Possible bug or expected?** Status's "Findings" count (3 total in coral-bleach at the end) includes findings written by sub-agent B that I didn't author. That's correct behavior (the substrate is the truth) but worth flagging as a thing to remember when interpreting per-sub-agent counts.

## 11. End-of-run state

- Last successful tool call: `cairn validate` in `/tmp/cairn-sc1-rUOm/cairns/lit-monitor` → `OK`, exit=0.
- Did you complete every task in the backlog? **Yes — all 7 tasks completed in order.**
- Final write count (mine, not totals — totals include sub-agent B's writes):
  - decisions written by me: 1 (`D-002` in coral-bleach: "Switch to monthly transect sampling during bleaching season")
  - findings written by me: 2
    - `coral-bleach/knowledge/findings/2026-05-24-coral-cover-dropped-to-30-in-2024-transects.md`
    - `lit-monitor/knowledge/findings/2026-05-24-the-new-hoegh-guldberg-paper-on-bleaching-is-worth-tracking.md`
  - actions written by me: 0
  - open_questions written by me: 0
- Final state-file totals (including concurrent sub-agent B activity) at end of Task 6:
  - coral-bleach: decisions=2, findings=3, open_questions=1, actions=0
  - lit-monitor:  decisions=2, findings=2, open_questions=1, actions=0
