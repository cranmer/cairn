# Sub-agent feedback — scenario-1 (re-run) / Kyle on coral-bleach

## 1. Identity

- Sub-agent role: Kyle on coral-bleach (re-run against fixed Cairn build, PR #27 merged)
- Collaborator id used for writes: kyle
- Working directory: /tmp/cairn-run-20260523T191531Z/projects/coral-bleach/
- Cairn(s) reachable from this session: coral-bleach, lit-monitor (both registered in user-level registry)
- Transport: CLI only (no MCP — server not registered in parent env, per backlog scoping note)
- Endpoint (if http): n/a

## 2. Environment sanity check

- `whoami()` (no cairn param) returned: n/a (CLI-only; MCP not exercised)
- `cairn --version` returned: `0.0.1.dev109+gd104a6d4a` — works fine. Previous run had reported `cairn --version` didn't work; that's resolved.
- `cairn registered` listed both cairns:
  - `coral-bleach  /tmp/cairn-run-20260523T191531Z/cairns/coral-bleach`
  - `lit-monitor   /tmp/cairn-run-20260523T191531Z/cairns/lit-monitor`
- Baseline `cairn status` from coral-bleach project repo (before my writes):
  - Collaborators: 2 (kyle, lila); Decisions: 1; Open questions: 1; Findings: 1; Actions: 0.
  - Recent decision: D-001 (Adopt PIT-tagged colonies as the primary monitoring unit).
  - Note: the backlog mentioned baseline of "1 finding", but after my 2 writes the count went 1 → 3 → 4, suggesting there may be an additional pre-existing finding I didn't notice in baseline. Verified by `ls`: the directory had a second pre-existing finding `2026-05-23-transect-methodology-paper-arxiv-2403-04567-relevant-to-base.md` which wasn't in `status` output before my writes. Either status only showed the most recent one (it says "Findings (1 total, most recent)") or this is a baseline mismatch. Status said `1 total` but `ls` showed 2 files at start. Probably an indexing/scan question rather than my concern. Not critical.
- Baseline lit-monitor status (after my finding-add): 2 collaborators (kyle, priya), 2 decisions, 1 open question, 2 findings.
- Nothing else surprising at startup.

## 3. Work backlog completion

### Task 1: Registry visibility (`cairn registered`)

- Intended: confirm both cairns appear in the user-level registry.
- Tool call(s) made: `cairn registered` (no cairn param — global command).
- Result: success. Both cairns listed with their paths.
- Anything notable: clean output, includes the path to the registry file. Matches expectation.

### Task 2: Confirm pairing from project repo (NEW since previous run)

- Intended: `cairn status` from `/tmp/cairn-run-.../projects/coral-bleach/` should resolve via `cairn.toml` and return coral-bleach's state without a cwd workaround.
- Tool call(s) made: `cairn status` with cwd = project repo.
- Result: success. Returned coral-bleach state (1 decision, 1 finding at the time of baseline display, 1 open question, 2 collaborators). No cwd workaround needed.
- Anything notable: previous run found this errored. Now works. The output header `Cairn 'coral-bleach' [/tmp/.../cairns/coral-bleach]` makes the resolution explicit — nice for confirming you're talking to the right cairn.

### Task 3: Log a finding to the paired cairn

- Intended: add a finding to coral-bleach via the project repo.
- Tool call(s) made: `cairn finding add --author kyle --title "coral cover at transect T3 dropped to 30% in 2024" --body "..."`
- Result: success.
- Entity id allocated: `2026-05-23-coral-cover-at-transect-t3-dropped-to-30-in-2024.md`
- Author: kyle. Cross-refs: none.
- Output verbatim: `Logged finding at knowledge/findings/2026-05-23-coral-cover-at-transect-t3-dropped-to-30-in-2024.md.`
- Anything notable: filename rendering of "30%" → "30" (percent dropped). Reasonable slug behavior.

### Task 4: Record a decision with related id and explicit context

- Intended: add D-002 with `--related Q-001` and verify the fixed decision-add output (file path + accepted `--related` ids).
- Tool call(s) made: `cairn decision add --author kyle --text "Switch from line-intercept to belt transects starting with the 2025 season" --context "Belt transects integrate over more area; cited in lit-monitor watchlist (arxiv 2403.04567)." --related Q-001`
- Result: success.
- Entity id allocated: D-002.
- Author: kyle. Cross-refs: Q-001.
- **Output verbatim:** `Recorded D-002 in state/decisions.yaml; related: Q-001.`
- Anything notable: PREVIOUS RUN got `Recorded D-002.` — confirmed fixed. Now includes the state file path AND echoes the accepted `--related` ids. Good. (Minor nit: shows the relative state file path rather than the cairn-rooted absolute, but that's fine and consistent with `finding add`.)

### Task 5: Cross-cairn write (lit-monitor)

- Intended: `cd` to lit-monitor project repo and add a finding there. Confirm no trailing-hyphen slug bug.
- Tool call(s) made: `cairn finding add --author kyle --title "Methods-comparison paper (arxiv 2403.04567) is worth a closer read" --body "..."` (cwd = lit-monitor project repo).
- Result: success.
- Entity id allocated: filename `2026-05-23-methods-comparison-paper-arxiv-2403-04567-is-worth-a-closer.md`
- Anything notable: **No trailing hyphen** — ends in `-closer.md`. Previous run got `...-closer-.md`. Confirmed fixed (F-XX from prior run resolved). Pairing-resolution from the lit-monitor project repo also worked transparently — the write went to lit-monitor's cairn, not coral-bleach's, as confirmed by subsequent status output.

### Task 6: Long-title slug check

- Intended: confirm long-title truncation produces a clean filename (no trailing hyphen) and the file is readable.
- Tool call(s) made: `cairn finding add --author kyle --title "extended observations of secondary bleaching events throughout the 2024 monitoring season at all three transect sites" --body "Test that the slug-truncation behavior is sane."` (cwd = coral-bleach project repo).
- Result: success.
- Entity id allocated: filename `2026-05-23-extended-observations-of-secondary-bleaching-events-througho.md`
- Anything notable: truncation ends at `-througho` (mid-word "throughout"). Ends cleanly — no trailing hyphen, file is readable, YAML frontmatter retains the full untruncated title. Slug field stores the truncated form. Behavior is sane; the truncation point is in the middle of a word but that's a minor cosmetic thing — the important fix (no trailing dash, no empty/malformed name) holds.

### Task 7: Read status from each paired project cwd

- Intended: confirm cwd-based pairing routes to the correct cairn in each repo.
- Tool call(s) made:
  - `cairn status | head -3` in coral-bleach project → `Cairn 'coral-bleach' [...]`, 2 collaborators (kyle, lila), 2 decisions, 1 open question, 4 findings.
  - `cairn status | head -3` in lit-monitor project → `Cairn 'lit-monitor' [...]`, 2 collaborators (kyle, priya), 2 decisions, 1 open question, 2 findings.
- Result: success — they differ correctly, each reporting the cairn paired with that project repo.
- Anything notable: pairing resolution is reliable from cwd.

### Task 8: JSON read

- Intended: `cairn status --json` and extract project_name, branch, git_branch.
- Tool call(s) made: `cairn status --json | python3 -c "...print(d.get('project_name'), d.get('branch'), d.get('git_branch'))"` (cwd = coral-bleach).
- Result: `coral-bleach current master`
- Anything notable: **`branch` field still says `"current"`** — confirms F-09 is still deferred, as the backlog predicted. `git_branch` correctly reports `master`. So the JSON has both a `branch` (logical/exploration name with placeholder `"current"`) and `git_branch` (raw git branch).

### Task 9: Validate from project repo cwd

- Intended: run `cairn validate` from coral-bleach project repo; previously broken.
- Tool call(s) made: `cairn validate` (cwd = coral-bleach project repo).
- Result: `OK`, EXIT=0.
- Anything notable: works cleanly. Previous run flagged this as not working from project repos — confirmed fixed.

### Task 10: Error message check (no cairn anywhere)

- Intended: trigger missing-cairn error from `/tmp` and capture verbatim.
- Tool call(s) made: `cd /tmp && cairn finding add --author kyle --title "test" --body "test"`.
- Result: error, EXIT=2.
- **Verbatim error:** `error: no cairn found at or above /tmp`
- Anything notable: concise and accurate. Tells me the search path. Could optionally mention `cairn register` or `cairn registered` but isn't strictly necessary at /tmp where there isn't even a cairn.toml. Mild friction: no hint about the user-level registry existing — but the previous run apparently expected this kind of bare message, so probably fine.

### Task 11: Cairn.toml pointer hint (NEW since previous run)

- Intended: create a `cairn.toml` pointing at a non-existent cairn and confirm the error surfaces the pointer's presence (per F-04 fix).
- Tool call(s) made: created `/tmp/cairn-run-.../probe-dir/cairn.toml` with `name = "this-does-not-exist"`, then `cairn status`.
- Result: error, EXIT=1.
- **Verbatim error:** `error: cairn 'this-does-not-exist' is not registered. Add it with `cairn register this-does-not-exist <path>`. See `cairn registered`.`
- Anything notable: **F-04 fixed.** Error now names the cairn from the pointer (`'this-does-not-exist'`), tells me the action to fix (`cairn register ... <path>`), and points at the discovery command (`cairn registered`). Excellent error message — it implicitly confirms the cairn.toml was found and parsed, since the name extracted from it appears in the message. Could go one step further and explicitly mention the cairn.toml path that was found, but that's gold-plating; the current message is plenty informative.

## 4. Identity consistency

- Did you ever feel uncertain about which user you were supposed to be? No.
- Did any tool response refer to you under a different identity? No. All my writes carry `author: kyle` and no command silently substituted an identity.
- `whoami()` not exercised (CLI-only run).

## 5. Cairn-routing observations (scenario 1)

- For "to the project this repo is paired with" tasks, I relied entirely on the cwd-based `cairn.toml` pointer; no explicit cairn parameter was passed. This worked correctly: writes from `projects/coral-bleach/` landed in `cairns/coral-bleach/`, and writes from `projects/lit-monitor/` landed in `cairns/lit-monitor/`.
- The CLI doesn't take a `--cairn <name>` parameter on the verbs I exercised (`finding add`, `decision add`, `status`, `validate`) — routing is purely cwd-driven via `cairn.toml`. I didn't try to override it.
- Server didn't reject any writes by name; all writes went where expected.
- No read tool returned data from the wrong cairn. `cairn status` consistently identified the cairn in its header, which made wrong-cairn issues impossible to miss.

## 6. Concurrency observations (scenario 2)

n/a — this is scenario 1.

## 7. Errors and surprises

All errors I saw during the run:

1. Task 10: `error: no cairn found at or above /tmp` (intended).
2. Task 11: `error: cairn 'this-does-not-exist' is not registered. Add it with \`cairn register this-does-not-exist <path>\`. See \`cairn registered\`.` (intended; surfaces pointer per F-04 fix).

Both errors were clear, actionable, and helpful. No unexpected errors during normal write/read flow.

## 8. UX friction

- **Status `1 total` vs `ls` showing 2 files at baseline:** in the initial `cairn status` from coral-bleach, the Findings header read `Findings (1 total, most recent)` but `ls knowledge/findings/` later showed there were already 2 files pre-existing (one of them, `2026-05-23-transect-methodology-paper-arxiv-2403-04567-relevant-to-base.md`, wasn't from my writes). Possibly a stale state-file index vs disk scan question; possibly I'm miscounting between the baseline and post-write state. Worth checking whether `cairn status` re-scans the findings dir or trusts a yaml index, since a mismatch like this could mask data loss.
- **`branch: "current"` in JSON output (F-09):** confirmed still present; the backlog says deferred — fine, just noting.
- **Decision-add output (now fixed):** the new wording `Recorded D-002 in state/decisions.yaml; related: Q-001.` could optionally separate the relative path vs the absolute cairn-rooted form. Minor — current form is consistent with `finding add` which says `Logged finding at knowledge/findings/...md`. Both use cairn-relative paths.
- **Slug truncation chops mid-word:** the long-title file ends at `...througho.md` (mid-word). Cosmetic; not a blocker. Title in frontmatter is preserved in full. A word-boundary truncation would read nicer but isn't required.
- **Error at `/tmp` doesn't hint at the registry:** `error: no cairn found at or above /tmp` could plausibly add a hint like "or specify `--cairn <name>` from a registered cairn (see `cairn registered`)." Minor.

## 9. Acceptance-criterion self-report

The scenario 1 doc names criteria A1–A6, but I don't have that doc in my context — I'm self-grading against the backlog tasks instead, which are the on-the-ground acceptance test for this re-run.

| Criterion | Your read | Evidence |
|-----------|-----------|----------|
| `cairn --version` works | pass | Task pre-1: `0.0.1.dev109+gd104a6d4a` |
| Registry lists both cairns | pass | Task 1 |
| `cairn status` works from project repo without workaround | pass | Task 2 |
| `cairn finding add` writes to paired cairn from project cwd | pass | Tasks 3, 5, 6 |
| `cairn decision add` output now shows file path + related ids (prev: just `Recorded D-002.`) | pass | Task 4: `Recorded D-002 in state/decisions.yaml; related: Q-001.` |
| Cross-cairn write filename clean (no trailing hyphen) | pass | Task 5: `...-closer.md` |
| Long-title slug ends cleanly | pass | Task 6: `...-througho.md` (no trailing dash, file readable) |
| Both project repos route to their own cairn | pass | Task 7 |
| JSON status structure (`branch: "current"` still present as expected) | pass (deferred) | Task 8 |
| `cairn validate` works from project repo cwd | pass | Task 9 |
| Missing-cairn error message reasonable | pass | Task 10 |
| Stale-pointer error mentions cairn name | pass | Task 11 (F-04 fixed) |

## 10. Additional observations

- The `cairn status` header `Cairn 'coral-bleach' [/tmp/.../cairns/coral-bleach]` is a really nice affordance for confirming routing — should keep it across formats. The JSON output exposes `project_name` but not the resolved path; consider adding `cairn_path` to JSON for parity.
- The pointer-error message (Task 11) is a strong piece of UX — it includes (a) the name from the pointer, (b) the corrective command shape, (c) the discovery command. Worth using as a template for other resolver errors.
- Slug truncation at ~62 chars (`-througho`) suggests a fixed-length cap. Word-boundary trimming would be a nice polish.
- One Findings count quirk noted in section 8: `cairn status` "1 total" at baseline disagreed with the on-disk file count. Probably worth a quick check on whether `status` reads the findings dir directly or relies on an index that can drift. (Could also just be my misreading of state between commands.)
- Both `decision add` and `finding add` output relative paths under the cairn root. Consistent — good.

## 11. End-of-run state

- Last successful tool call: `cairn status` from `probe-dir` (Task 11 — errored intentionally). Last successful *write* was Task 6: finding `2026-05-23-extended-observations-of-secondary-bleaching-events-througho.md` on coral-bleach.
- Did you complete every task in the backlog? Yes — all 11 tasks.
- Final write count (from my session):
  - coral-bleach: decisions=+1 (D-002), findings=+2 (T3 dropped + extended observations), actions=0, open_questions=0
  - lit-monitor: decisions=0, findings=+1 (methods-comparison paper), actions=0, open_questions=0
- Final on-disk state (post-writes):
  - coral-bleach: 2 decisions, 4 findings, 1 open question, 2 collaborators
  - lit-monitor: 2 decisions, 2 findings, 1 open question, 2 collaborators

### Summary vs previous run's findings

| Previous finding | Status after this re-run |
|------------------|-------------------------|
| `cairn --version` didn't work | **Fixed** — returns `0.0.1.dev109+gd104a6d4a`. |
| `cairn status` errored from project repo | **Fixed** — works without workaround. |
| `cairn validate` didn't work from project repo | **Fixed** — exits 0. |
| `decision add` output was just `Recorded D-002.` | **Fixed** — now `Recorded D-002 in state/decisions.yaml; related: Q-001.` |
| Cross-cairn finding filename had trailing hyphen (`...-closer-.md`) | **Fixed** — ends in `...-closer.md`. |
| F-04: pointer error didn't mention cairn.toml/cairn name | **Fixed** — error names the pointed-at cairn and points to `cairn register` and `cairn registered`. |
| F-09: JSON `branch: "current"` (deferred) | **Still deferred** as predicted. |
