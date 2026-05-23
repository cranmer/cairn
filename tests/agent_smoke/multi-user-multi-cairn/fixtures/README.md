# Fixtures — fictional project skeletons

The scenarios use three fictional research projects as stand-ins for
real cairn-paired repos. Each is small enough to scaffold in a tmpdir
from a spec (a list of files + content) rather than being a checked-in
directory. The fixtures live here as specs; the orchestrator builds
them fresh on every run.

**Why fictional rather than cloned-real-world:** the scenarios test
concurrent / multi-user / routing behavior. The project content is
atmosphere — the substantive material is in the work backlogs and the
cairn state. Fictional projects keep tests deterministic and remove any
risk of accidental network operations against third-party repos.

## Three projects

| Project name | Domain | Used in | Cairn name |
|---|---|---|---|
| `coral-bleach` | Marine-biology data analysis | Scenario 1 | `coral-bleach` |
| `lit-monitor` | Literature monitoring tool | Scenario 1 | `lit-monitor` |
| `shared-physics-paper` | Multi-author paper writeup | Scenario 2 | `shared-physics-paper` |

Each project ships with:

- A minimal `README.md` (one paragraph describing the fictional
  project's purpose).
- A synthesized git history (3–5 commits, with `git config user.email`
  set to the relevant collaborator's address before each commit so
  authorship is plausible).
- A `cairn.toml` pairing the project repo with its corresponding cairn
  (the form of `cairn.toml` depends on the scenario — `name = "..."`
  for scenario 1, `endpoint + name` for scenario 2).
- A `work-backlog.md` for whichever sub-agent will work in this repo.
  The backlog spells out the tasks the sub-agent walks through; it is
  *not* a full simulation of organic research work.

## Project specs

### `coral-bleach`

**Fictional pitch:** a marine biology group monitoring coral cover at
three transect sites in the Coral Triangle. Annual transect data, some
historical photo archives, and an unfinished paper on bleaching events
since 2018.

**Files:**

- `README.md` — one paragraph + a TODO list with two items.
- `analysis/transect_summary.py` — ~20 lines of Python that "computes
  cover percentages". Doesn't need to run; presence matters.
- `data/transects-2024.csv` — five rows of synthetic transect data
  (site, date, cover_pct).
- `cairn.toml` — paired with cairn `coral-bleach` via `name = ...`.

**Pre-seeded cairn state (scenario 1):**

- Collaborators: `kyle` (PI), `lila` (postdoc). (Both registered so
  cross-cairn whoami comparisons have substance.)
- Decisions: `D-001` ("Adopt PIT-tagged colonies as the primary
  monitoring unit") authored by `kyle`, dated 6 months ago.
- Open questions: `Q-001` ("Should 2018 baseline use pre-bleach or
  post-bleach surveys?") raised by `lila`.
- One finding: `F-…-bleach-2024-extent` summarising the 2024 event,
  authored by `kyle`.

**Sub-agent work backlog (scenario 1, sub-agent A):**

1. Log a finding "coral cover at transect T3 dropped to 30% in 2024"
   to the project this repo is paired with (no explicit cairn param).
2. Record a decision about switching the sampling protocol from
   line-intercept to belt transects, attributed to `kyle`, citing
   `Q-001` in `related`.
3. Quick cross-write: log a finding to `lit-monitor` ("the new Hughes
   et al. paper on bleaching cycles is worth tracking"), passing the
   `cairn` parameter explicitly.
4. Sanity reads: call `whoami(cairn='coral-bleach')` and
   `whoami(cairn='lit-monitor')`; report whether the returned
   collaborator lists differ.
5. Call `status(cairn='lit-monitor')` to confirm cross-cairn read
   works and returns lit-monitor's counts, not coral-bleach's.

### `lit-monitor`

**Fictional pitch:** a literature-tracking project that watches arXiv
and journal RSS for coral / bleaching / climate-stress papers. Light
Python tooling. The team is a single researcher (Kyle wearing the
same hat as on coral-bleach, plus a collaborator), and they're
beginning to systematically tag what they read.

**Files:**

- `README.md` — one paragraph; "what we're tracking" list.
- `watchlist.yaml` — a YAML list of 4 fictional paper titles + arxiv
  ids.
- `scripts/fetch.py` — ~10 lines that "would fetch new entries"; stub.
- `cairn.toml` — paired with cairn `lit-monitor` via `name = ...`.

**Pre-seeded cairn state (scenario 1):**

- Collaborators: `kyle` (lead), `priya` (collaborator, lit-search).
  (Note: `kyle` appears in both cairns to test that the same
  collaborator id can exist independently per-cairn; `lila` and `priya`
  do NOT overlap, so whoami discrimination has visible signal.)
- Decisions: `D-001` ("Use arXiv API + journal RSS, not Google
  Scholar") by `priya`.
- One open question: `Q-001` ("Should we track preprints separately
  from published versions?") by `kyle`.

**Sub-agent work backlog (scenario 1, sub-agent B):**

1. Log a finding "RSS feed for Coral Reefs journal is unreliable; need
   a fallback" to the project this repo is paired with (no cairn
   param).
2. Record a decision to add a polling fallback for unreliable RSS
   feeds, attributed to `kyle`, citing `Q-001` in `related`.
3. Quick cross-write: log a finding to `coral-bleach` ("new transect
   methodology paper out — relevant to the Q-001 baseline debate"),
   passing the `cairn` parameter explicitly.
4. Same sanity reads as sub-agent A but in reverse: `whoami` and
   `status` for both cairns; confirm discrimination.

### `shared-physics-paper`

**Fictional pitch:** a three-author paper on a measurement of an
ungapped (fictional) Higgs-sector observable, with three collaborators
splitting methods, analysis, and writeup. The cairn is the paper's
shared project memory — decisions about cuts, findings from
intermediate fits, open questions on systematics. Three humans
collaborate in parallel over weeks.

**Files:**

- `README.md` — one paragraph + author list (Alex, Morgan, Sam).
- `paper/draft.tex` — ~30-line skeleton with `\section` placeholders.
- `analysis/run_fit.py` — ~15-line stub.
- `cairn.toml` — paired with cairn `shared-physics-paper` via
  `endpoint = "http://127.0.0.1:<port>"` + `name = "shared-physics-paper"`.
  (The orchestrator substitutes the actual port when it starts the
  HTTP server.)

**Pre-seeded cairn state (scenario 2):**

- Collaborators:
  - `alex` (methods lead, `alex@example.com`)
  - `morgan` (analysis lead, `morgan@example.com`)
  - `sam` (writeup lead, `sam@example.com`)
  - `repo-history` (`type="unknown"`) — for ambiguous-authorship
    cross-check (criterion B5 setup).
- Decisions: `D-001` ("Use the V+jets control region for background
  estimation") authored by `alex`, dated 2 weeks ago.
- Open questions: `Q-001` ("Are the JER systematics double-counted in
  the smoothing prescription?") raised by `morgan`.
- One finding: `F-…-fit-converges-on-toys` authored by `alex`.

The pre-seeded data is intentionally light so most state churn during
the scenario comes from the sub-agents' writes — that's what we're
testing.

**Sub-agent work backlogs (scenario 2):**

*Alex (methods lead):*

1. Record a decision: tighten the leading-jet pT cut from 30 GeV to
   40 GeV. Author = `alex`. Reference `Q-001` in `related`.
2. Add an action item: "produce updated efficiency tables under the
   new cut" assigned to `alex`, due in 1 week.
3. Record a second decision: keep the existing trigger threshold
   despite the cut change. Author = `alex`.
4. Sanity: call `whoami()` and confirm `suggested_id` resolves to
   `alex`.

*Morgan (analysis lead):*

1. Log a finding: "the smoothing window of 5 bins over-smooths the
   third peak in the toys". Author = `morgan`.
2. Raise a new open question: "Should we re-derive JER systematics
   with the updated pT cut?" Raised by `morgan`.
3. Log a second finding: "fit pulls on the nuisance for ttbar
   normalization grow to 1.2σ in 30% of toys". Author = `morgan`.
4. Add an action item: "rerun toys with extended nuisance set"
   assigned to `morgan`.
5. Sanity: `whoami()` should resolve to `morgan`.

*Sam (writeup lead):*

1. Record a decision: cite Hughes et al. 2026 as the canonical
   reference for the smoothing prescription. Author = `sam`.
   Reference whichever D-NNN Alex's tightening decision got (Sam's
   backlog tells the agent to look it up via
   `get_decisions(cairn='shared-physics-paper')` first — this
   exercises the read-then-cross-reference flow).
2. Record a second decision that explicitly cites Morgan's new open
   question (Sam looks it up too and passes its id in `related`).
3. Log a finding summarising the methods-section draft progress.
   Author = `sam`.
4. Add an action item assigned to `sam`: "circulate methods draft for
   internal review by Friday".
5. Sanity: `whoami()` should resolve to `sam`. Additionally, call
   `whoami()` twice during the run and confirm the result is
   consistent (criterion B7).

The lookups Sam does in tasks 1 and 2 are the cross-user-reference
exercise (criterion B5): the decision Sam writes references an id
that another sub-agent allocated earlier in the same run.

## How the orchestrator builds these

For each scenario the orchestrator:

1. Creates the run tmpdir: `tests/agent_smoke/multi-user-multi-cairn/runs/<timestamp>/`.
2. For each project in the scenario, creates `<tmpdir>/projects/<name>/`
   and writes the files listed above.
3. Initializes a git repo in each project dir, configures `user.email`
   appropriately, and produces the synthesized commits.
4. Scaffolds the cairn(s) (`cairn init`) in `<tmpdir>/cairns/<name>/`,
   pre-registers collaborators (`cairn collaborator add ...`), and
   seeds the initial decisions / questions / findings listed under
   "pre-seeded cairn state" above. Seeding uses the CLI rather than
   raw file writes so the resulting state is guaranteed schema-valid.
5. Registers each cairn against the user-level registry
   (`cairn register --name <name> <cairn-path>`) under a per-run
   `XDG_CONFIG_HOME` so the test is isolated from the dev machine's
   real registry.
6. For scenario 2 only: starts `cairn mcp --transport streamable-http
   --host 127.0.0.1 --port <free-port>` in the background, captures
   the chosen port, and stamps it into each project's `cairn.toml`.
7. Writes each sub-agent's `work-backlog.md` into its project repo and
   reserves a `feedback-<sub-agent>.md` path the sub-agent will fill
   in.
8. Launches sub-agents in parallel via the Agent tool with
   `run_in_background=true`.

## Regenerating fixtures

The fictional projects don't have committed file contents because the
specs above are the source of truth — they're built fresh in tmpdir on
every run. If a scenario doc gains new tasks that require a richer
fixture, update this README + the relevant scenario's work-backlog
section together; don't drift them apart.
