# Sub-agent feedback — scenario-1 / Kyle on lit-monitor (one user / many cairns)

## 1. Identity

- Sub-agent role: Kyle, anchored on lit-monitor, with a cross-cairn write into coral-bleach
- Collaborator id used for writes: kyle
- Working directory: `/tmp/cairn-sc1-rUOm/projects/lit-monitor/` (project repo paired with the `lit-monitor` cairn)
- Cairn(s) reachable from this session: `lit-monitor`, `coral-bleach`
- Transport: stdio (CLI-only; no MCP server involved this run)
- Endpoint (if http): n/a

## 2. Environment sanity check

I did not use any MCP `whoami()` tool — the scenario is exercised entirely through the `cairn` CLI per the prompt. Sanity checks via the CLI:

- `cairn registered` (run from the lit-monitor project repo) listed both cairns at their expected paths:
  ```
  coral-bleach  /tmp/cairn-sc1-rUOm/cairns/coral-bleach
  lit-monitor   /tmp/cairn-sc1-rUOm/cairns/lit-monitor
  ```
- Baseline `cairn status` from inside `/tmp/cairn-sc1-rUOm/cairns/lit-monitor/`:
  - Collaborators: 2 (kyle, priya)
  - Goals 0, Decisions 1 (D-001), Open questions 1, Findings 0, Actions 0
  - Git: `main @ 420df6e` — "D-001: Use arXiv API + journal RSS, not Google Scholar."
- Baseline `cairn status` from inside `/tmp/cairn-sc1-rUOm/cairns/coral-bleach/`:
  - Collaborators: 2 (kyle, lila)
  - Goals 0, Decisions 1 (D-001), Open questions 1, Findings 2, Actions 0
  - Git: `main @ 87183e7` — "Log finding: Coral cover dropped to ~30% in 2024 transects"
- Nothing surprising. The lit-monitor baseline already had a D-001 (priya) and one open question; coral-bleach already had two findings and a D-001 (kyle). That matched the prompt's setup framing.

## 3. Work backlog completion

### Task 1: Sanity check — list registered cairns and snapshot baseline status

- Intended: Confirm both cairns visible, capture pre-write counts for each.
- Tool call(s): `cairn registered` (from lit-monitor project repo); `cairn status` (from each cairn root).
- Result: success.
- Entity id allocated: none (read-only).
- Author / raised_by / assignee: n/a.
- Cross-references passed: n/a.
- Anything notable: `cairn registered` resolves the registry from the wrapper's pinned `XDG_CONFIG_HOME` (`/tmp/cairn-sc1-rUOm/config/cairn/server.toml`), printed as a header line — that header was a nice touch for disambiguating environments.

### Task 2: Default-routed finding — written from `projects/lit-monitor/`

- Intended: Log a finding about RSS poller throughput, relying purely on `cairn.toml`-walk for routing (no `--cairn` flag passed; the CLI does not expose one).
- Tool call(s): `cairn finding add --author kyle --title "RSS poller throughput is fine for biology preprints but drops on physics arXiv mirrors" --body "..."` from `/tmp/cairn-sc1-rUOm/projects/lit-monitor/`. No cairn parameter.
- Result: success.
- Entity id allocated: filename slug `2026-05-24-rss-poller-throughput-is-fine-for-biology-preprints-but-drop.md` (slug truncated mid-word — see UX friction §8).
- Author / raised_by / assignee parameter: `--author kyle`.
- Cross-references: none.
- Anything notable: File landed at `/tmp/cairn-sc1-rUOm/cairns/lit-monitor/knowledge/findings/2026-05-24-rss-poller-throughput-is-fine-for-biology-preprints-but-drop.md`, not coral-bleach. Frontmatter quoted verbatim:
  ```
  ---
  date: '2026-05-24T19:16:12Z'
  author: kyle
  title: RSS poller throughput is fine for biology preprints but drops on physics arXiv
    mirrors
  slug: rss-poller-throughput-is-fine-for-biology-preprints-but-drop
  related: []
  exploration: main
  source_commits: []
  source_prs: []
  ---
  ```

### Task 3: Default-routed decision — same cwd

- Intended: Record a decision; verify it lands in lit-monitor's `state/decisions.yaml`.
- Tool call(s): `cairn decision add --author kyle --text "Cache arXiv fetches for 6 hours to absorb mirror latency" --context "..."` from `/tmp/cairn-sc1-rUOm/projects/lit-monitor/`. No cairn parameter.
- Result: success.
- Entity id allocated: `D-002`. Server echoed: `Recorded D-002 in state/decisions.yaml.`
- Author / raised_by / assignee: `--author kyle`.
- Cross-references: none.
- Anything notable: Verified in `cairns/lit-monitor/state/decisions.yaml`; coral-bleach's `state/decisions.yaml` untouched by this call (it has its own D-002 written by sub-agent A; cross-checked timestamps to confirm independence).

### Task 4: Cross-cairn finding — written from `projects/coral-bleach/`

- Intended: Use cwd-walk as the proxy for an explicit cross-cairn parameter; finding should land in coral-bleach.
- Tool call(s): `cd /tmp/cairn-sc1-rUOm/projects/coral-bleach && cairn finding add --author kyle --title "The 2024 transect dataset is ready for cross-referencing with literature" --body "..."`. No cairn parameter.
- Result: success.
- Entity id allocated: filename slug `2026-05-24-the-2024-transect-dataset-is-ready-for-cross-referencing-wit.md` (slug truncated again).
- Author / raised_by / assignee: `--author kyle`.
- Cross-references: none. (Note: this finding semantically refers to lit-monitor content, but I didn't populate `related: []` because the CLI doesn't expose a flag for it and the related entity in lit-monitor is just a peer finding — there's no obvious natural id to point to. See §8.)
- Anything notable: File landed in coral-bleach, lit-monitor's findings dir was unaffected by this command. Honest gap: the CLI surface only routes by `cwd`; there is no `--cairn lit-monitor` style flag, so A2 in the strict sense (explicit cairn parameter on a write tool) cannot be exercised here. The cwd-walk is functioning as the substitute.

### Task 5: No-cairn-found error

- Intended: Confirm that a write outside any cairn errors out clearly with a non-zero exit.
- Tool call(s): `cd /tmp && cairn finding add --author kyle --title "ghost test" --body "should be rejected"`.
- Result: error.
- Entity id allocated: none.
- Author / raised_by / assignee: `--author kyle` (rejected before resolution).
- Cross-references: n/a.
- Anything notable: Verbatim stderr was a single line:
  ```
  error: no cairn found at or above /tmp
  ```
  Exit code: `2`. The message is clear and points at the failed walk root.

### Task 6: Per-cairn read discrimination

- Intended: Confirm `cairn status` from each cairn root returns cairn-specific data.
- Tool call(s): `cairn status` from `cairns/lit-monitor/` and `cairns/coral-bleach/`.
- Result: success; outputs differ as expected.
- Entity id allocated: n/a.
- Author / raised_by / assignee: n/a.
- Anything notable: After all writes by both sub-agents,
  - lit-monitor: `Collaborators: 2 (kyle, priya)`, Decisions 2, Open questions 1, Findings 2.
  - coral-bleach: `Collaborators: 2 (kyle, lila)`, Decisions 2, Open questions 1, Findings 3.
  Collaborator names are disjoint apart from `kyle`, exactly as the prompt described. The finding listed first in lit-monitor ("The new Hoegh-Guldberg paper on bleaching is worth tracking") wasn't written by me — sub-agent A must have logged it during the same run. That's expected from the methodology description but worth noting since I didn't observe its creation.

### Task 7: Validate

- Intended: Both cairns should `cairn validate` exit 0.
- Tool call(s): `cairn validate` from each cairn root.
- Result: both printed `OK`, exit 0.
- Entity id allocated: n/a.
- Anything notable: nothing.

## 4. Identity consistency

- Did you ever feel uncertain about which user you were supposed to be? **No.** The prompt was explicit ("kyle"), and every write took `--author kyle`. The git identity is also kyle/kyle@example.com so commits would attribute consistently.
- Did any tool response refer to you under a different identity? **No.**
- `whoami()` not invoked (CLI-only scenario).

## 5. Cairn-routing observations (scenario 1 only)

- When the task said "to the project this repo is paired with", I relied entirely on cwd-walk: ran the command from inside `/tmp/cairn-sc1-rUOm/projects/lit-monitor/`, which has a `cairn.toml` naming `lit-monitor`. No explicit cairn parameter was passed (and none is available on the CLI surface I used).
- When the task named the other cairn (coral-bleach), the CLI offers no `--cairn` flag, so I `cd`-ed into `/tmp/cairn-sc1-rUOm/projects/coral-bleach/` to get cwd-walk routing to do the work. **This deserves explicit honest noting**: A2's strict spirit — "explicit cairn parameter on a write tool" — is not actually exercised by the CLI in this scenario. Only the cwd-resolution path is. If the MCP server's `add_finding(cairn=...)` style parameter is supposed to be the canonical surface for cross-cairn writes, then the CLI is not equivalent and this run leaves the explicit-parameter routing untested.
- I did not try to write to a cairn name that the server would reject; the only failure mode I induced was "no cairn at cwd".
- No read tool returned data from the wrong cairn. Collaborator lists, decision IDs, and finding lists all matched the cwd-resolved cairn.

## 6. Concurrency observations (scenario 2 only)

n/a — this is scenario 1.

## 7. Errors and surprises

- `cairn finding add` from `/tmp` produced:
  ```
  error: no cairn found at or above /tmp
  ```
  Exit 2. Helpful and unambiguous; I did not need any other context to interpret it. One small nit: the error doesn't mention `cairn.toml` or suggest how to fix it ("create a cairn.toml with `name = ...` or run from a project repo that has one"). For a brand-new collaborator this would be slightly less self-explanatory than it is for me.
- No other errors during the run.

## 8. UX friction

- **Slug truncation looks unintentional.** Both findings I wrote ended up with slugs cut mid-word: `...biology-preprints-but-drop` (lost "drops") and `...cross-referencing-wit` (lost "with literature"). It's deterministic — almost certainly a fixed character cap — but the truncation point falls inside a word so the filename reads like a typo. Trimming on word boundaries would help.
- **No `--cairn` flag on the CLI writes.** I expected one based on the MCP-server framing in CLAUDE.md (tools like `add_finding(cairn=...)`). The CLI relies wholly on cwd-walk. That's a reasonable design choice, but the prompt's A2 ("a 'cross-cairn' write — addressed to the OTHER cairn") implicitly assumes the explicit-parameter form. I exercised the cwd substitute; the prompt itself flagged this gap, but in practice during the run I had to think about whether `cd`-ing counts as "addressing the other cairn" or whether I should look for a flag I'd missed. `cairn finding add --help` would have helped here; I didn't run it (could be useful to add to the work backlog).
- **No `--related` flag visible on the CLI** for findings. The cross-cairn finding is semantically related to the lit-monitor watchlist material; in a richer surface I'd want to point at it. The frontmatter ships with `related: []` filled in by default, which is fine, but means cross-cairn cross-references either need a manual frontmatter edit after the fact or aren't supported through this path at all.
- **`Recorded D-002 in state/decisions.yaml.`** is succinct but doesn't echo the cairn name. If I'd been confused about routing this wouldn't have surfaced it. The finding message has the same property (`Logged finding at knowledge/findings/...`); the relative path makes it slightly less ambiguous since the cwd is the project repo, not the cairn root, so a relative path implicitly identifies the cairn — but only if you already know cairn paths. Echoing the resolved cairn name in the success line ("Logged finding in `lit-monitor` at ...") would be more reassuring.
- **`cairn status` doesn't print the cairn name as the first thing on a confused day.** Actually it does — `Cairn 'lit-monitor' [...]` is the first line. That part is well-handled.

## 9. Acceptance-criterion self-report

| Criterion | Your read | Evidence |
|-----------|-----------|----------|
| A1 (default route from paired repo writes to lit-monitor) | pass | Task 2 (finding) + Task 3 (decision D-002) both landed in `cairns/lit-monitor/`; coral-bleach untouched by those calls. |
| A2 (cross-cairn write addressed to the OTHER cairn) | partial | Task 4 lands the finding in coral-bleach, but only via cwd-walk after `cd`-ing. The CLI exposes no `--cairn` flag, so the explicit-parameter form of A2 is not exercised. Prompt called this gap out; I confirm it. |
| A3 (no cairn at cwd → clear error) | pass | Task 5: `error: no cairn found at or above /tmp`, exit 2. |
| A4 (reads return cairn-specific state — lit-monitor) | pass | Task 6: `cairn status` from `cairns/lit-monitor/` shows kyle+priya, 2 decisions, 1 OQ, 2 findings — matches my actual writes. |
| A5 (reads return cairn-specific state — coral-bleach) | pass | Task 6: `cairn status` from `cairns/coral-bleach/` shows kyle+lila, 2 decisions, 1 OQ, 3 findings — disjoint collaborator from lit-monitor. |
| A6 (no "I'm confused which cairn this is for") | pass | Never lost track. The wrapper + cwd-walk + `Cairn '<name>' [...]` first-line in `status` were sufficient. |

## 10. Additional observations

- The wrapper at `/tmp/cairn-sc1-rUOm/bin/cairn` was invisible in use — it just worked. Pinning `XDG_CONFIG_HOME` per-run is a good isolation pattern and I'd recommend it for any future smoke harness.
- `cairn registered` printing the registry path on its first line is genuinely useful for debugging "wait, which environment am I in" situations. Don't lose that.
- The git log on lit-monitor after my writes shows `D-002: Cache arXiv fetches...` as a commit message — i.e., decisions auto-commit with sensible messages. I didn't dig into how findings commit (they presumably do too, given the coral-bleach git tip moved to "Log finding: The 2024 transect dataset..."), but the auto-commit messages were good enough to read at a glance.
- I noticed an extra finding appearing in lit-monitor between my Task 4 and Task 6 ("The new Hoegh-Guldberg paper on bleaching is worth tracking"). That must be sub-agent A's cross-cairn write into lit-monitor. Confirms the scenario is genuinely interleaving sub-agents without coordination — no locking surprises observed from my side, but I didn't run reads tightly enough to detect a race.
- Default `exploration: main` in finding frontmatter is sensible but worth confirming behaves correctly once explorations actually get used. Not in scope here.

## 11. End-of-run state

- Last successful tool call: `cairn validate` from `cairns/coral-bleach/`, exit 0.
- Did you complete every task in the backlog? **Yes**, all seven tasks completed.
- Final write count (mine only): decisions=1 (D-002 in lit-monitor), findings=2 (one in lit-monitor, one in coral-bleach), actions=0, open_questions=0.
