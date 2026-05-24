# Sub-agent feedback — scenario-2 / morgan

## 1. Identity

- Sub-agent role: Morgan, analysis lead on shared-physics-paper
- Collaborator id used for writes: morgan
- Working directory: /tmp/cairn-sc2-F0KF/projects/morgan/
- Cairn(s) reachable from this session: shared-physics-paper (via cairn.toml pairing)
- Transport: http
- Endpoint (if http): http://127.0.0.1:47973/mcp

## 2. Environment sanity check

- `whoami()` (no cairn param) returned: **Not called.** There is no `cairn whoami` subcommand at the CLI surface (see top-level `cairn --help` — the closest is `cairn registered`). `whoami` is an MCP tool, not a CLI command, and this sub-agent was driven through CLI only. So B6 is not directly testable from my slice.
- `cairn registered` (run from my project repo cwd) reported "No cairns registered (registry: /tmp/cairn-sc2-F0KF/config/cairn/server.toml)". That's correct — this scenario uses cairn.toml pairing, not the user-level registry. But the message is potentially misleading: a fresh user would not realize that "registered" and "paired-by-cairn.toml" are distinct mechanisms. No hint pointing at the existing `cairn.toml` was emitted.
- `cairn status` errored with the documented known-gap message: `error: \`cairn status\` is not supported against a remote-MCP cairn yet (this project repo is paired with 'shared-physics-paper' at http://127.0.0.1:47973/mcp).` Clean, actionable, exit code 1. Good behavior for a known gap.
- Direct filesystem read of server-side `state/` showed baseline:
  - decisions.yaml: **2 entries** (D-001 and D-002, both authored by `alex`) — *not* the "1 decision (D-001)" the prompt described. Either alex already wrote D-002 concurrently before I started, or the prompt's baseline description is stale.
  - open_questions.yaml: 1 entry (Q-001, raised_by morgan)
  - action_items.yaml: 1 entry (A-001, assignee alex) — *not* "0 actions" as the prompt described. Same concurrent-writer hypothesis: alex wrote A-001 before I read.
  - findings: 1 file (`2026-05-24-fit-converges-on-toys.md`)
  - collaborators.yaml: alex, morgan, sam, repo-history — all four present as expected.
- The most useful interpretation: the "baseline" in the prompt was the *fixture's* baseline before any sub-agent wrote, but by the time I read state files alex had already landed D-002 and A-001. This is fine — it's evidence concurrent writes from another sub-agent did land — but anyone scoring B2 has to account for this.

## 3. Work backlog completion

### Task 1: Sanity check

- Intended: confirm I can reach the cairn and capture baseline counts.
- Tool call(s) made: `cairn registered`, `cairn status`, direct file reads of state/*.yaml and knowledge/findings/.
- Result: success (read-side); `cairn status` errored as expected.
- Entity id allocated: n/a.
- Author / raised_by / assignee passed: n/a.
- Notable: see §2 — baseline did not match the prompt's stated counts because at least one other sub-agent had already written.

### Task 2: Finding — fake-jet background reduction

- Intended: log a finding about the 30% fake-jet reduction under the new pT cut.
- Tool call: `cairn finding add --author morgan --title "30% reduction in fake-jet background under the new pT cut" --body "<body>"` against the morgan project cwd.
- Result: success.
- Entity id allocated: filename `2026-05-24-30-reduction-in-fake-jet-background-under-the-new-pt-cut.md` (findings don't have F-NNN IDs — they're identified by date-slug).
- Author passed: morgan. Confirmed in file frontmatter `author: morgan`.
- Cross-references passed in `related`: none (the task didn't reference Q-001 / D-002, even though intellectually it relates to the pT-cut decision; I did not add it unprompted).
- Notable: the CLI returned a clean confirmation line with the file path and the cairn endpoint. Good UX.

### Task 3: Open question — MC sample coverage (filed as action instead)

- Intended: file an open question about MC coverage of the high-pT tail.
- Tool call attempted #1: `cairn action add --assignee morgan --text "..." --due-date "2026-06-01" --context "..."`.
  - Result: **error** — `No such option '--context'. Did you mean '--text'?`
- Tool call attempted #2: `cairn action add --assignee morgan --text "<merged context into text>" --due-date "2026-06-01"`.
  - Result: success.
- Entity id allocated: **A-002**.
- Assignee passed: morgan. Confirmed in state/action_items.yaml.
- Notable: per the prompt's own caveat, I used `action add` because there is no `cairn open-question add` (and no `cairn question`, `cairn oq`, or similar). See §8. Also, action items only support `assignee/text/due-date/related` — no `--context`, even though decisions and findings both have context-ish fields (decisions have `context`, findings have a body). The shape mismatch between entity types is real friction.

### Task 4: Finding — trigger efficiency plateau

- Intended: log a finding about the 50-80 GeV plateau efficiency.
- Tool call: `cairn finding add --author morgan --title "Trigger efficiency plateaus above 50 GeV" --body "<body>"`.
- Result: success.
- Entity id allocated: `knowledge/findings/2026-05-24-trigger-efficiency-plateaus-above-50-gev.md`.
- Author passed: morgan. Confirmed.
- Notable: nothing.

### Task 5: Action — toy MC closure

- Intended: file an action to validate toy MC closure under the new cut.
- Tool call: `cairn action add --assignee morgan --text "Validate toy MC closure under the new pT cut" --due-date "2026-06-05"`.
- Result: success.
- Entity id allocated: **A-004**.
- Assignee passed: morgan. Confirmed.
- Notable: I got A-004, not A-003. A-003 was allocated to sam (`Complete first draft of paper section 4 (systematics)`) in the gap between my A-002 and this call. That's the expected interleaving and is positive evidence for B4 — IDs are dense and monotonic across users, no gaps.

### Task 6: Final verification

- Intended: confirm my four writes (2 findings + 2 actions) landed and are attributed to morgan.
- Tool call(s): direct filesystem reads of state/action_items.yaml, state/open_questions.yaml, knowledge/findings/.
- Result: all four writes present, all attributed to `morgan`. open_questions.yaml unchanged (Q-001 only) — as expected, since I never actually filed an open question.

## 4. Identity consistency

- Did you ever feel uncertain about which user you were supposed to be? **No.** I was Morgan throughout.
- Did any tool response refer to you under a different identity than the one you were given? **No.** The CLI does not echo the caller's identity in success responses (just the entity id and cairn name), so there was no opportunity for an identity bleed to surface — but also no opportunity to detect one if it happened silently. Frontmatter and YAML reads confirmed `author/assignee: morgan` for all my writes after the fact.
- If `whoami()` was called multiple times during the run, did it return consistent results each time? **N/A** — `whoami` is an MCP tool only, not a CLI command. From my slice I cannot evaluate B6 directly.

## 5. Cairn-routing observations (scenario 1 only)

N/A — this is scenario 2.

## 6. Concurrency observations (scenario 2 only)

- Did any write fail and need a retry? **No write failed for concurrency reasons.** The only retry was Task 3 due to the `--context` flag not existing.
- Did any tool call hang, time out, or return a network-level error? **No.** All HTTP calls returned promptly.
- Did any entity id come back that you didn't expect? **Yes, in the good sense:** I got A-002 then A-004, with A-003 (sam) interleaved. No gaps. Decisions never got allocated by me, but reading decisions.yaml showed D-001 and D-002 both authored by alex with consecutive timestamps and no gaps either.
- Did the server ever refuse a write with a "concurrent modification" type of error? **No.**

## 7. Errors and surprises

1. **`cairn action add --context ...` rejected.** Tool: `cairn action add`. Args: `--assignee morgan --text "..." --due-date 2026-06-01 --context "..."`. Error: `No such option '--context'. Did you mean '--text'?`. The error itself was clear and actionable. The surprise is that *the orchestrator's prompt told me to pass `--context`* — meaning either the prompt is stale or this flag exists in a different cairn version. Worth flagging to whoever maintains the prompt.

2. **`cairn status` against remote-paired cairn errored with the documented known-gap message.** Not really a surprise (the prompt warned me), but the message is good — it names the paired cairn and the endpoint, so the operator knows where to look.

3. **Baseline counts in the prompt didn't match what I found.** Prompt said "Baseline: 1 decision (D-001), 1 open question (Q-001), 1 finding, 0 actions." Actual at first read: 2 decisions (D-001, D-002), 1 OQ, 1 finding, 1 action. Interpretation: the orchestrator-stated baseline was the fixture's pre-scenario state; concurrent sub-agents had already written by the time I read. Not a bug, but it does mean any sub-agent that *assumes* a baseline can be wrong.

## 8. UX friction

- **No `cairn open-question` (or `cairn question`, `cairn oq`) subcommand.** The CLI surface has decision / finding / action / exploration but no first-class way to file an open question. The fixture's existing `Q-001` had to come from somewhere — presumably an MCP-only path or a manual YAML edit during fixture scaffolding. This is real friction for the analysis-lead role, who naturally generates "things we don't yet know" more than "decisions we have made". As the prompt invited me to flag: confirmed missing.
- **`cairn action add` does not accept `--context`** even though decisions accept context-style fields and findings have a body. Three write-emitting entity types, three different field schemas surfaced through the CLI. The shape inconsistency made me have to inline context into `--text` for the MC-coverage action, which now reads awkwardly: `"Check whether the MC samples adequately cover the high-pT tail under the new cut (statistics-limited above 400 GeV in current samples)"`. Compare with a decision where the `context` is a separate field.
- **`cairn registered` is misleading in a cairn.toml-paired project.** It correctly reports the registry is empty, but a fresh operator in this cwd has no way to know they're paired-via-cairn.toml without reading `cairn.toml` directly. A line like "this project is paired with <name> via ./cairn.toml" would close that gap.
- **No `cairn whoami` CLI subcommand.** Since the MCP tool is named `whoami`, I expected a CLI parallel. Its absence means B6 (whoami discrimination) is only testable through MCP-direct clients, not through the CLI surface that operators actually use.
- **Findings don't have an F-NNN id.** They're identified by date-slug filename. That's fine in isolation but inconsistent with decisions/actions/open-questions (which have D-NNN / A-NNN / Q-NNN). It also means a finding can't be referenced by ID in a decision's `related` field in the same way — you'd have to use the slug.
- **CLI success output is just one line.** `Logged finding at <path> in cairn '<name>' at <endpoint>.` and `Added A-002 in cairn '<name>' at <endpoint>.` are concise but they don't echo back the author/assignee they recorded, so if a server bug *had* attributed my write to "alex" I wouldn't have noticed from CLI output alone — I had to go read the YAML/MD files to confirm. For a smoke test specifically designed to catch identity bleed, this is a gap.
- **Title gets lowercased in the slug** (`30-reduction-in-fake-jet-background-under-the-new-pt-cut`), which means the leading "30%" became just "30" with the `%` dropped silently. Minor, but worth noting if anyone tries to cross-reference findings by their pre-slug title.

## 9. Acceptance-criterion self-report

| Criterion | Your read | Evidence (task #, tool call, file path) |
|-----------|-----------|-----------------------------------------|
| B1 (Attribution) | pass — for my slice | All 4 writes show `author: morgan` / `assignee: morgan` in /tmp/cairn-sc2-F0KF/cache/cairn/dev-servers/sandbox-47973/cairns/shared-physics-paper/state/action_items.yaml and knowledge/findings/2026-05-24-*morgan*.md. Cross-checked all four post-write. |
| B2 (No data loss) | partial — need orchestrator to aggregate | I attempted 2 findings + 2 actions + 0 open-questions + 0 decisions. All 4 visible server-side. Orchestrator must sum across alex/morgan/sam reports and compare to final state. |
| B3 (Concurrent-write safety) | pass (from my slice) | I successfully read action_items.yaml after concurrent writes from alex (A-001), me (A-002), sam (A-003), me (A-004) — no YAML corruption, no duplicate ids, monotonic. I did not run `cairn validate` (it would fail with the same remote-gap error as `cairn status`); orchestrator should run validate on the server-side cairn directory. |
| B4 (ID monotonicity) | pass | Actions: A-001 (alex), A-002 (morgan), A-003 (sam), A-004 (morgan) — dense, monotonic, no gaps, three writers interleaved. Decisions: D-001, D-002 (both alex) — dense. Open questions: Q-001 only. No allocator races visible. |
| B5 (Cross-user references) | n.a. for my slice | I did not pass any `--related` flag this run (the prompt didn't ask me to cross-link my finding to D-002 or Q-001, and I didn't speculate). Orchestrator should look at alex's / sam's writes for evidence. |
| B6 (`whoami` discrimination) | n.a. for my slice | `whoami` is MCP-only; no CLI affordance to call it. Cannot evaluate from my slice. |
| B7 (No agent-posture violations under concurrency) | pass | I was Morgan throughout; never felt confused about identity; all my writes attributed correctly. |
| B8 (HTTP transport stays up) | pass | All 6 CLI calls to the HTTP endpoint completed promptly with success or a clean error (the `--context` one). No 502s, timeouts, connection resets, or hangs. |

## 10. Additional observations

- The `cairn.toml` pairing model is elegant but under-advertised. A `cairn status` that's known-to-fail with a useful message is *better* than a `cairn registered` that's silent about the pairing.
- The `dev` subcommand group is set up as "not for production cairn use" but the whole scenario-2 setup depends on `cairn dev serve` running. That's fine for a smoke test, but it makes me wonder what the eventual production HTTP-server story looks like (the registry seems aimed at stdio).
- Concurrent writes from three users into a single shared YAML file with monotonic ID allocation suggests there's a server-side lock or atomic-rename strategy in play. Worth a glance at the implementation — would be a good thing to document in an ADR if not already.
- The findings frontmatter records `exploration: main`. Cairn has explorations as a first-class concept but my session never touched them; I assumed the default and the CLI did the right thing silently. Worth confirming that "main" is the correct sentinel name (vs. "no-exploration" or null).
- Total time-on-keyboard for the work backlog: ~6 CLI calls plus a handful of reads. The CLI surface is minimal and fast — once I knew the shapes, I never had to read the help text again. That's a good sign.

## 11. End-of-run state

- Last successful tool call: `cairn action add --assignee morgan --text "Validate toy MC closure under the new pT cut" --due-date "2026-06-05"` → A-004 in cairn 'shared-physics-paper' at http://127.0.0.1:47973/mcp.
- Did you complete every task in the backlog? **Partial.** Tasks 1, 2, 4, 5, 6 completed cleanly. Task 3 (open question) was *filed as an action* instead, because there is no `cairn open-question add` subcommand. So strictly: 5 of 6 backlog items completed as specified; 1 substituted with the closest available primitive and flagged in §8.
- Final write count attributed to morgan (this sub-agent only): decisions=0, findings=2, actions=2, open_questions=0.
