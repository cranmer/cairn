# Sub-agent feedback template

Each sub-agent fills this in at the end of its run and writes it to the
path given to it by the orchestrator (`<feedback-path>` in the prompt
frame). The orchestrator reads every filled-in feedback file and
synthesizes the results against the scenario's acceptance criteria.

**Posture for filling this in:** be specific and honest. If something
felt confusing, say so even if the writes succeeded. If a tool error
mentioned something the prompt didn't prepare you for, quote the error.
If a behavior surprised you, name it. The point of this template is to
surface the things that *wouldn't* show up in a passing transcript.

Don't summarize for politeness. The orchestrator wants raw observations,
not a tidy report.

---

```markdown
# Sub-agent feedback — <scenario id> / <sub-agent name>

## 1. Identity

- Sub-agent role: <e.g. "Kyle on coral-bleach", "alex on shared-physics-paper">
- Collaborator id used for writes: <e.g. kyle | alex | morgan | sam>
- Working directory: <abs path to project repo tmpdir>
- Cairn(s) reachable from this session: <list of cairn names>
- Transport: <stdio | http>
- Endpoint (if http): <e.g. http://127.0.0.1:51234>

## 2. Environment sanity check

Before starting the work backlog, the sub-agent should verify it can
reach the cairn(s) it's supposed to reach. Report the results.

- `whoami()` (no cairn param) returned: <paste the relevant fields, or
  "errored: <message>">
- `status()` for each reachable cairn — report cairn name + decision/
  finding/action/question counts as a sanity baseline before any
  writes.
- Anything surprising in the baseline that suggested the environment
  wasn't set up the way the prompt described? (e.g. "the prompt said I
  had access to lit-monitor but `status(cairn='lit-monitor')` errored
  with X")

## 3. Work backlog completion

For each task in your work backlog (in order):

### Task <N>: <one-line task summary from the backlog>

- Intended: <what the task asked for, in your own words>
- Tool call(s) made: <name(s) and the cairn parameter you passed, or
  "<no cairn param — default routing">
- Result: <success | error: ...>
- Entity id allocated (if any): <e.g. D-007, F-2026-05-23-…, A-012>
- Author / raised_by / assignee parameter you passed: <id>
- Cross-references passed in `related`: <list of ids>
- Anything notable: <e.g. "the server returned a different cairn name
  than I expected", "the entity id came back but the file path was
  missing">

(repeat per task)

## 4. Identity consistency

- Did you ever feel uncertain about which user you were supposed to be?
  <yes | no — and if yes, when / what triggered it>
- Did any tool response refer to you under a different identity than the
  one you were given? <yes | no — quote it>
- If `whoami()` was called multiple times during the run, did it return
  consistent results each time? <yes | no — describe>

## 5. Cairn-routing observations (scenario 1 only)

- When the task said "to the project this repo is paired with", what did
  you do? Did you pass a `cairn` parameter, or rely on the default?
- When the task named a specific other cairn, did the explicit
  `cairn=<name>` parameter work as expected?
- Did you ever try to write to a cairn name that the server rejected?
  Paste the error message verbatim.
- Did any read tool (`status`, `whoami`, `get_open_questions`, etc.)
  return data that looked like it was from the wrong cairn?

## 6. Concurrency observations (scenario 2 only)

- Did any write fail and need a retry? <yes | no — describe>
- Did any tool call hang, time out, or return a network-level error?
- Did any entity id come back that you didn't expect (e.g. a gap from
  D-005 → D-008 with nothing in between)?
- Did the server ever refuse a write with a "concurrent modification"
  type of error? Paste it.

## 7. Errors and surprises

List every error message you saw during the run, even if you recovered.
Include the tool name, the args you passed (redact long bodies), and the
error text. If the error message was unclear or didn't help you decide
what to do next, say so.

## 8. UX friction

Anything that wasn't an outright error but felt rough:

- Tool names or parameters that didn't match what you expected from the
  prompt or docs.
- Responses that were technically successful but had confusing wording
  or missing fields you'd have liked.
- Cases where you weren't sure whether a tool call had succeeded.
- Cases where you had to guess at a parameter value.

## 9. Acceptance-criterion self-report

For each criterion the scenario doc names (A1–A6 for scenario 1, B1–B8
for scenario 2), self-report:

| Criterion | Your read | Evidence (task #, tool call, file path) |
|-----------|-----------|-----------------------------------------|
| A1 / B1   | pass / partial / fail / n.a. | ... |
| ...       | ...       | ...                                     |

Don't grade the scenario as a whole — the orchestrator does that by
aggregating across sub-agents. Just report what *your* slice saw.

## 10. Additional observations

Free-form. Anything that struck you as worth a note that doesn't fit
above — design suggestions, possible bugs, friction patterns, mental-
model breakdowns. One bullet per observation; one sentence each unless
you need more.

## 11. End-of-run state

- Last successful tool call: <name, cairn, entity id>
- Did you complete every task in the backlog? <yes | no — which were
  skipped and why>
- Final write count: decisions=<n>, findings=<n>, actions=<n>,
  open_questions=<n>
```

---

## Notes for the orchestrator

When aggregating:

- **Section 3** gives the ground-truth count of writes attempted per
  sub-agent — sum across feedback files and cross-check against the
  state files for criteria B2 / B4.
- **Section 4** signals agent-posture violations — any "yes" in 4.1 or
  4.2 is a finding worth surfacing even if the writes themselves were
  correct.
- **Section 7** is the cleanest pre-aggregated bug list; copy each
  distinct error into SYNTHESIS.md's technical-findings section with a
  pointer back to the feedback file.
- **Section 8** populates the UX-findings section of SYNTHESIS.md.
- **Section 9** is a sanity check on the orchestrator's own grading;
  large divergences between sub-agent self-report and orchestrator
  scoring deserve a look.
- **Section 10** is where the most interesting findings often hide —
  read it carefully even if everything else looks green.
