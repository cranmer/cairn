# Sub-agent feedback — scenario 2 / morgan

## 1. Identity

- Sub-agent role: Morgan Wu, analysis lead on shared-physics-paper
- Collaborator id used for writes: morgan
- Working directory: /tmp/cairn-run-20260523T192455Z/projects/morgan
- Cairn(s) reachable from this session: shared-physics-paper (via HTTP)
- Transport: http
- Endpoint (if http): http://127.0.0.1:49273/mcp

## 2. Environment sanity check

I did not call `whoami()` or `status()` explicitly — the backlog said
"Don't try to read state — remote-mode reads aren't supported." So I
went straight to the writes. The first write succeeded and the response
identified the cairn as `shared-physics-paper` at
`http://127.0.0.1:49273/mcp`, which matched the prompt's pid/port
description (port 49273), so the environment looked correctly wired.

One initial wrinkle: I ran the first `cairn finding add` from the
default cwd (`/home/user/cairn`) and got:

```
error: no cairn found at or above /home/user/cairn
```

I retried from `/tmp/cairn-run-20260523T192455Z/projects/morgan` (which
has `cairn.toml`) and it worked. So the CLI requires being inside a
linked project directory to know which remote cairn to talk to. Not a
bug — just a thing I had to figure out.

## 3. Work backlog completion

### Task 1: Finding — smoothing window over-smooths the third peak

- Intended: Log a finding about closure-test residuals at the third
  peak being biased when the smoothing window is 5 bins.
- Tool call(s) made: `cairn finding add --author morgan --title "..." --body "..."` (no explicit cairn — default routing via cairn.toml in cwd).
- Result: success
- Entity id allocated (if any): `knowledge/findings/2026-05-23-smoothing-window-of-5-bins-over-smooths-the-third-peak-in-th.md`
- Author / raised_by / assignee parameter you passed: `--author morgan`
- Cross-references passed in `related`: none
- Verbatim output:
  ```
  Logged finding at knowledge/findings/2026-05-23-smoothing-window-of-5-bins-over-smooths-the-third-peak-in-th.md in cairn 'shared-physics-paper' at http://127.0.0.1:49273/mcp.
  ```
- Anything notable: The finding filename is truncated mid-word ("in-th"
  rather than "in-the-toys"). Functional but ugly — the slug truncator
  seems to be a fixed character limit.

### Task 2: Finding — nuisance pulls on ttbar normalization

- Intended: Log a finding about non-Gaussian fit pulls on ttbar
  normalization in 30% of toys.
- Tool call(s) made: `cairn finding add --author morgan --title "..." --body "..."`
- Result: success
- Entity id allocated (if any): `knowledge/findings/2026-05-23-fit-pulls-on-ttbar-normalization-grow-to-1-2-sigma-in-30-per.md`
- Author / raised_by / assignee parameter you passed: `--author morgan`
- Cross-references passed in `related`: none
- Verbatim output:
  ```
  Logged finding at knowledge/findings/2026-05-23-fit-pulls-on-ttbar-normalization-grow-to-1-2-sigma-in-30-per.md in cairn 'shared-physics-paper' at http://127.0.0.1:49273/mcp.
  ```
- Anything notable: Same slug-truncation behavior ("in-30-per" rather
  than "in-30-percent-of-toys"). Also: title contains "1.2 sigma" but
  filename has "1-2-sigma" — periods/spaces all collapse to dashes,
  which is sensible but does make titles slightly less recognizable in
  the filename.

### Task 3: Action — rerun toys with extended nuisance set

- Intended: Action item to rerun toy MC with extended nuisances
  (lepton energy scale, jet resolution), due 2026-06-02.
- Tool call(s) made: `cairn action add --assignee morgan --text "..." --due-date "2026-06-02"`
- Result: success
- Entity id allocated (if any): `A-002`
- Author / raised_by / assignee parameter you passed: `--assignee morgan`
- Cross-references passed in `related`: none
- Verbatim output:
  ```
  Added A-002 in cairn 'shared-physics-paper' at http://127.0.0.1:49273/mcp.
  ```
- Anything notable: I got `A-002`, not `A-001` — so somebody else (Alex
  or Sam) got A-001 by the time my call landed. That's the expected
  concurrency behavior and the server allocated cleanly. Also notable:
  the success message doesn't echo the text/assignee/due-date back, so
  I'm trusting that the server stored the right fields.

### Task 4: Open question (skipped)

- Intended: Note an open question about something analysis-related.
- Tool call(s) made: none — backlog explicitly says to skip because the
  CLI has no `question add` / `open-question add` command. Only the
  MCP server's `add_open_question` tool exposes this.
- Result: skipped per instructions
- Anything notable: This is a real CLI-vs-MCP parity gap. The schema
  supports open questions, the MCP server exposes a write tool for
  them, but a human (or sub-agent) driving the CLI cannot create one.
  For a tool with the "substrate-as-specification" commitment, this is
  a noticeable asymmetry — anything writable via one interface should
  be writable via the other. Doesn't feel like "no big deal" to me; it
  feels like a parity bug.

## 4. Identity consistency

- Did you ever feel uncertain about which user you were supposed to
  be? no — the prompt and backlog both said morgan, and I passed
  `--author morgan` / `--assignee morgan` on every write.
- Did any tool response refer to you under a different identity than
  the one you were given? no — responses don't echo the identity at
  all, which is its own minor concern (see UX friction).
- If `whoami()` was called multiple times during the run, did it
  return consistent results each time? n.a. — not called.

## 5. Cairn-routing observations (scenario 1 only)

n.a. — scenario 2.

## 6. Concurrency observations (scenario 2 only)

- Did any write fail and need a retry? Only the first call, which
  failed because I was in the wrong cwd — that's a user error, not a
  concurrency or network failure. After moving into the project dir,
  every write succeeded on the first try.
- Did any tool call hang, time out, or return a network-level error?
  no.
- Did any entity id come back that you didn't expect? Yes, mildly: I
  got `A-002` for my only action add, implying A-001 was allocated to
  another sub-agent's write before mine. Expected for a shared cairn
  but worth noting that I have no way to confirm A-001's existence
  from this remote session.
- Did the server ever refuse a write with a "concurrent modification"
  type of error? no.

## 7. Errors and surprises

1. `cairn finding add` from `/home/user/cairn` (default cwd):
   ```
   error: no cairn found at or above /home/user/cairn
   ```
   Clear enough — I just needed to `cd` into the project dir. But: it
   would be nicer if a remote-mode CLI invocation could be told which
   cairn to write to by name (e.g. via env var or `--cairn` flag) so
   it doesn't have to walk up the filesystem looking for `cairn.toml`.
   The user-level registry already knows the endpoint; tying writes
   to cwd is a 100%-local-mode assumption.

2. No other errors during the run.

## 8. UX friction

- The `cairn finding add` success message includes the cairn name and
  endpoint, but doesn't echo back the author, title, or any unique
  finding id (just the filename, which carries the slug). If two
  agents log near-identical findings, the slugs would presumably
  collide on a `-N` suffix and the only way to disambiguate is to
  read the file.
- `cairn action add` success message is even sparser — just `Added
  A-002`. No echo of text, assignee, or due-date. I can't sanity-check
  that what I typed is what got stored without reading state, which
  the backlog says I shouldn't try.
- Finding filenames are truncated to a fixed length mid-word (e.g.
  "in-th" instead of "in-the-toys"). Truncating at a word boundary
  would be friendlier.
- No CLI command to add an open question even though the schema and
  MCP server both support it. Discovered by following the backlog
  note; I'd have hit this naturally trying to add Q-002.
- The CLI needs to be run from within a project directory containing
  `cairn.toml` in order to find the remote endpoint. In a multi-cairn
  HTTP world it would be nice to support `--cairn <name>` directly so
  the registry can do the routing without cwd walks.

## 9. Acceptance-criterion self-report

I don't have the scenario doc with B1-B8 spelled out in front of me;
self-reporting against what I infer from the backlog and template:

| Criterion | Your read | Evidence (task #, tool call, file path) |
|-----------|-----------|-----------------------------------------|
| B1 (writes routed to right cairn) | pass | All three writes returned `cairn 'shared-physics-paper' at http://127.0.0.1:49273/mcp` |
| B2 (write counts per agent) | pass (2 findings + 1 action from morgan) | Tasks 1-3 above |
| B3 (no concurrent-mod errors) | pass | Section 6 |
| B4 (state files reflect attempted writes) | not directly verifiable from remote | Backlog forbade reads |
| B5 (no identity bleed) | pass | Section 4 |
| B6 (open-question parity) | fail | Task 4 — CLI lacks the command |
| B7 (clear error messages) | pass | The cwd error was clear |
| B8 (entity ids contiguous across agents) | pass (got A-002, implies A-001 elsewhere) | Task 3 output |

## 10. Additional observations

- The slug truncation is deterministic but produces ugly filenames; a
  word-boundary-aware truncator would cost almost nothing.
- Remote-mode writes work fine but remote-mode reads being unavailable
  makes it impossible to do even a basic sanity check from the
  sub-agent's POV. A read-only `cairn status` over HTTP would close
  that gap.
- The cwd-rooted cairn discovery feels like a local-mode assumption
  leaking into the remote workflow. Once a project is registered with
  the user-level registry, a `--cairn <name>` flag (or env var) would
  let scripts run from anywhere.
- The open-question CLI gap is the clearest concrete parity issue I
  hit. Worth opening as a tracking item.

## 11. End-of-run state

- Last successful tool call: `cairn action add` → A-002, cairn
  shared-physics-paper.
- Did you complete every task in the backlog? Tasks 1-3 yes; task 4
  intentionally skipped per backlog instructions (no CLI command
  exists); task 5 (final check) addressed in this feedback.
- Final write count: decisions=0, findings=2, actions=1,
  open_questions=0
