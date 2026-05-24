# Sub-agent feedback — scenario-2 / sam

## 1. Identity

- Sub-agent role: Sam on shared-physics-paper (writeup lead, cross-reference role for B5)
- Collaborator id used for writes: sam
- Working directory: /tmp/cairn-sc2-F0KF/projects/sam/
- Cairn(s) reachable from this session: shared-physics-paper (over HTTP)
- Transport: http
- Endpoint (if http): http://127.0.0.1:47973/mcp

## 2. Environment sanity check

- `whoami()` (no cairn param) returned: not invoked. The prompt steered me to the CLI wrapper (`cairn registered`, `cairn status`) rather than direct MCP `whoami` calls. `cairn registered` showed: `No cairns registered (registry: /tmp/cairn-sc2-F0KF/config/cairn/server.toml).` — i.e. the *client-side* CLI registry is empty, which is correct for a remote-paired project repo; the server has its own registry.
- `status()` per cairn: `cairn status` is unsupported in remote mode and errored with the documented gap:
  ```
  error: `cairn status` is not supported against a remote-MCP cairn yet (this project repo is paired with 'shared-physics-paper' at http://127.0.0.1:47973/mcp).
  ```
  Baseline read via direct filesystem instead of the CLI. At the moment I read, baseline + alex's earlier writes were:
  - decisions: D-001 (alex), D-002 (alex, pT cut), D-003 (alex, trigger), D-004 (alex, lumi nuisances)
  - open_questions: Q-001 (raised_by morgan — the prompt's "baseline" framing implied pre-seeded, but the file shows morgan as `raised_by`)
  - action_items: A-001 (alex, trigger eff tables)
  - collaborators: alex, morgan, sam, repo-history
- Surprises: the prompt said baseline = 1 decision (D-001) / 1 open question / 1 finding / 0 actions. By the time I read, alex had already written D-002–D-004 and A-001, and Q-001 was attributed to `raised_by: morgan` rather than to an anonymous pre-seed. I also could not find a findings.yaml under `state/` — only `action_items.yaml`, `collaborators.yaml`, `decisions.yaml`, `goals.yaml`, `open_questions.yaml`. If there's a finding it lives under `knowledge/findings/`, not in a state YAML, which is consistent with how `cairn finding add` works but worth noting the prompt's "baseline: 1 finding" wasn't verifiable from `state/` alone.

## 3. Work backlog completion

### Task 1: Sanity check — `cairn registered`, `cairn status`, direct state-file reads

- Intended: confirm baseline + observe what alex/morgan had written.
- Tool call(s) made: `cairn registered`, `cairn status` (expected to fail), `Read` on server-side state files.
- Result: success (registered shows empty client registry as expected; status errored per known gap; state files readable).
- Entity id allocated: none.
- Author/raised_by/assignee: none.
- Cross-references passed in `related`: none.
- Notable: see section 2 baseline-mismatch note.

### Task 2: Decision — paper section 3 structure (related D-001)

- Intended: record decision to structure section 3 around the pT cut, referencing alex's D-001.
- Tool call(s) made: `cairn decision add --author sam --text "..." --context "..." --related D-001`. No explicit `--cairn`; default routing via `cairn.toml`.
- Result: success — server returned `Recorded D-005 in cairn 'shared-physics-paper' at http://127.0.0.1:47973/mcp.`
- Entity id allocated: D-005
- Author parameter passed: sam
- Cross-references passed in `related`: [D-001]
- Notable: none.

### Task 3: Decision — cite Q-001 in systematics (related Q-001)

- Intended: record decision to cite Q-001 in systematics section.
- Tool call(s) made: `cairn decision add --author sam --text "..." --context "..." --related Q-001`.
- Result: success — `Recorded D-006 in cairn 'shared-physics-paper' at http://127.0.0.1:47973/mcp.`
- Entity id allocated: D-006
- Author parameter passed: sam
- Cross-references passed in `related`: [Q-001]
- Notable: cross-reference to a Q-* id from a decision was accepted without complaint. This is good — it means the related-id validator resolves across entity classes, not only within decisions.

### Task 4: Action — first draft of section 4

- Intended: add A-* action assigned to sam due 2026-06-15.
- Tool call(s) made: first attempt: `cairn action add --assignee sam --text "..." --due-date "2026-06-15" --context "..."`. Errored:
  ```
  Error: No such option '--context'. Did you mean '--text'?
  ```
  Retried without `--context`: `cairn action add --assignee sam --text "..." --due-date "2026-06-15"`.
- Result: success — `Added A-003 in cairn 'shared-physics-paper' at http://127.0.0.1:47973/mcp.`
- Entity id allocated: A-003 (note: A-002 was allocated by morgan in the interim; not a gap)
- Assignee parameter passed: sam
- Cross-references passed in `related`: none
- Notable: **UX friction** — `cairn decision add` and `cairn action add` have different surface areas. `decision add` supports `--context`; `action add` does not. The backlog prompt assumed they did. The context string "Depends on Morgan's toy MC closure validation completing first." had to be dropped, so that piece of provenance now exists only in this feedback file, not in the cairn. If actions have no "context" / "rationale" slot at all, that's a schema gap. If they have one under a different name, the CLI surface didn't suggest one.

### Task 5: Read-then-write cross-reference — `--related D-002` (alex's pT cut decision)

- Intended: read decisions.yaml to find alex's pT cut decision id, then file a sam decision referencing it.
- Tool call(s) made:
  1. `Read` on server-side `state/decisions.yaml` → confirmed D-002 is alex's "Tighten the leading-jet pT cut from 30 to 40 GeV".
  2. `cairn decision add --author sam --text "Use Alex's pT cut decision as the canonical reference in the paper's analysis section" --context "Keeps the paper's analysis choice traceable to a recorded decision." --related D-002`.
- Result: **success** — server returned `Recorded D-007 in cairn 'shared-physics-paper' at http://127.0.0.1:47973/mcp.`
- Entity id allocated: D-007
- Author parameter passed: sam
- Cross-references passed in `related`: [D-002] (alex's decision)
- Notable: **the B5 cross-user reference write succeeded.** Server's exact response was a single-line confirmation; it did not echo back the `related` list, so I confirmed the cross-reference landed by reading `state/decisions.yaml` afterwards. The final entry shows:
  ```yaml
  - id: D-007
    date: '2026-05-24T19:20:41Z'
    author: sam
    decision: Use Alex's pT cut decision as the canonical reference in the paper's analysis section
    context: Keeps the paper's analysis choice traceable to a recorded decision.
    supersedes: null
    superseded_by: null
    related:
    - D-002
    source_commits: []
    source_prs: []
  ```
  So: cross-user reference resolved, attribution preserved as `sam`, related list contains alex's D-002. Mild UX nit: the success line doesn't echo the `related` field, so a sub-agent that *didn't* re-read the YAML couldn't tell whether `--related` was honored vs silently dropped.

### Task 6: Final verification

- Intended: re-read state files; confirm sam attribution; spot ID gaps.
- Tool call(s) made: `Read` on `decisions.yaml`, `action_items.yaml`.
- Result: all four of my writes (D-005, D-006, D-007, A-003) are attributed to `sam`. No gaps in the decision sequence (D-001..D-007 all present). No gaps in the action sequence at last read (A-001 alex, A-002 morgan, A-003 sam, A-004 morgan). All `related` lists are the ones I passed.

## 4. Identity consistency

- Did you ever feel uncertain about which user you were supposed to be? no.
- Did any tool response refer to you under a different identity? no — every success line was a generic "Recorded D-NNN in cairn 'shared-physics-paper' at <url>" with no identity in the response, but every read-back of `state/decisions.yaml` showed `author: sam` on all four of my writes.
- `whoami` was not invoked in this run (the wrapper steered me to the CLI write commands, which don't surface whoami).

## 5. Cairn-routing observations (scenario 1 only)

n.a. — scenario 2.

## 6. Concurrency observations (scenario 2 only)

- Did any write fail and need a retry? no. (The one retry I did — `action add` — was a CLI-surface issue, not a concurrency issue.)
- Did any tool call hang, time out, or return a network-level error? no. Every write returned within a normal-feeling latency.
- Did any entity id come back that I didn't expect? Mild: I expected to allocate A-002, but got A-003. Reading `action_items.yaml` showed A-002 was claimed by morgan in the gap between my decisions and my action add. **No gap was produced** — A-002 landed cleanly under morgan. So this is a normal interleave under concurrent allocation, not a write loss.
- Did the server ever refuse a write with a "concurrent modification" error? no.

## 7. Errors and surprises

1. **`cairn status` against remote-paired cairn:** documented in the prompt as a known gap, error message was clear and explanatory.
   ```
   error: `cairn status` is not supported against a remote-MCP cairn yet (this project repo is paired with 'shared-physics-paper' at http://127.0.0.1:47973/mcp).
   ```
   Helpful suggestion would be: "use `cairn ... --remote` or read state via MCP tools" — but the error itself is unambiguous about what failed.

2. **`cairn action add --context` rejected:**
   ```
   Error: No such option '--context'. Did you mean '--text'?
   ```
   "Did you mean '--text'?" is misleading here — I *had* `--text`; I additionally wanted to attach contextual rationale, which `cairn decision add` does support. The didyoumean hint pointed me away from the real answer (the option simply does not exist on `action add`).

3. **Baseline drift between prompt and reality:** the prompt said baseline = 1 decision (D-001), 1 open question, 1 finding, 0 actions. By the time my session started, alex had already added D-002–D-004 and A-001. This is fine — the scenario *is* concurrent — but a sub-agent treating "baseline" as a strict pre-condition would have flagged it as an inconsistency. Worth phrasing prompts as "baseline at orchestrator-start", not "baseline at your-start".

## 8. UX friction

- **Asymmetric flag surface between `decision add` and `action add`.** `--context` works on decisions, not actions. If the schema rationale is "actions have a `text` field that absorbs both", that should be in the CLI help. Otherwise, the `action_items` schema appears to drop a piece of provenance the user would naturally want to attach.
- **Success messages don't echo what was written.** A line like `Recorded D-005 (author=sam, related=[D-001]) in cairn 'shared-physics-paper'` would let a sub-agent verify attribution and cross-reference *from the tool output alone*, instead of having to re-read the YAML. Right now there's no way to tell from the success line whether `--related` was accepted or silently dropped.
- **`cairn registered` from a remote-paired project repo says "no cairns registered".** That's technically true of the client-side registry, but it's the same wording a fresh user would see if they had no server set up at all. Distinguishing "no client-side registry entries but this project is paired remotely via cairn.toml" from "you have nothing set up" would help.
- **Server-side state-file path is not surfaced anywhere by the CLI.** I only knew where to read state files because the prompt told me. A user-friendly `cairn dev where shared-physics-paper` or analogous would be nice. (Documented as ADR-0015-adjacent territory.)
- **No `cairn finding` baseline visible from `state/`.** The prompt said baseline includes 1 finding, but findings live as files under `knowledge/findings/`, not in a YAML. A confused sub-agent could conclude "no findings exist" from a state-file-only inspection.

## 9. Acceptance-criterion self-report

| Criterion | Your read | Evidence (task #, tool call, file path) |
|-----------|-----------|-----------------------------------------|
| B1 Attribution | pass | All 4 of my writes show `author: sam` / `assignee: sam` in `state/decisions.yaml` and `state/action_items.yaml`. Tasks 2, 3, 4, 5. |
| B2 No data loss | pass (my slice) | 3 decisions attempted + recorded (D-005, D-006, D-007); 1 action attempted + recorded (A-003). All visible in state files. |
| B3 Concurrent-write safety | pass (my slice) | Both `decisions.yaml` and `action_items.yaml` parsed cleanly on every re-read; no duplicate ids; no half-written entries. |
| B4 ID monotonicity | pass at end of my run | D-001..D-007 present and unique; A-001..A-004 present and unique. The A-001→A-003 "gap" from my POV is morgan's A-002 landing in between — not a real gap. |
| B5 Cross-user references | **pass** | Task 5: `cairn decision add --author sam --related D-002` (alex's decision) recorded D-007 with `related: [D-002]` preserved in `state/decisions.yaml`. Server response: `Recorded D-007 in cairn 'shared-physics-paper' at http://127.0.0.1:47973/mcp.` Also Task 3: D-006 references Q-001 (raised by morgan) and was accepted. |
| B6 `whoami` discrimination | n.a. (my slice) | I did not invoke `whoami` directly; the CLI path doesn't expose it. The orchestrator's other sub-agents may have. |
| B7 No agent-posture violations | pass | No identity confusion at any point during the run. |
| B8 HTTP transport stays up | pass (my slice) | Every write returned a normal success response; no 502 / connection-reset / timeout observed. |

## 10. Additional observations

- **The cross-entity-class reference (decision → Q-id) just worked.** D-006 lists Q-001 in `related` and the server accepted it without complaint. Good sign that the related-id validator is genuinely cairn-wide and not gated by class.
- **The `repo-history` collaborator is registered but I never wrote anything attributed to it.** The scenario doc mentions it as part of B5's prereqs but my backlog didn't exercise it. If the orchestrator wants B5's "ambiguous authorship" sub-criterion covered, one of the three sub-agents (or a dedicated fourth) should issue at least one write with `author=repo-history`.
- **Action items appear to have no context/rationale field at all.** This is a schema observation, not a CLI one. If the design intent is that decisions carry "why" but actions don't, that's defensible (actions are imperative, not deliberative) — but the omission is worth a quick callout because the natural-language workflow of "I want to attach a reason this is blocked / who it depends on" doesn't have a home.
- **No way to express "depends on" between actions.** A-003 (my section-4 draft) depends on morgan's A-004 (toy MC closure) per the backlog. There's no schema slot for that. `related` would be a plausible home; an explicit `depends_on` would be better. Currently this dependency exists only in informal notes.
- **Default routing (no `--cairn` flag) worked perfectly.** I never had to think about which cairn I was writing to; `cairn.toml` did its job.

## 11. End-of-run state

- Last successful tool call: `cairn decision add --author sam --related D-002` → recorded D-007 in shared-physics-paper.
- Did you complete every task in the backlog? yes — all 6 tasks completed. Task 4 (action add) required a retry due to the `--context` flag being unsupported; substantively still completed.
- Final write count for **this sub-agent**: decisions=3 (D-005, D-006, D-007), findings=0, actions=1 (A-003), open_questions=0.
