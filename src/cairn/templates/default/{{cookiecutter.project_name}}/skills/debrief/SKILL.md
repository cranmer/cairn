---
name: debrief
description: Use at natural session-end signals ("ok let's wrap up", "good place to stop", "I have to go", "see you tomorrow", "thanks, I'll come back to this") OR when invoked explicitly. Reviews the working conversation and produces a single batched proposal of captures — findings logged in passing, decisions made, action items implied, questions raised but not yet recorded. The user approves / edits / drops the whole list in one round, avoiding per-item interruptions.
---

# Debrief at session end

The debrief replaces two failure modes:

1. **Per-capture interruptions.** Asking *"should I record that?"* for every signal is tedious and trains the user out of saying useful things mid-flow.
2. **Lost capture.** If the user wraps up without you having captured what was discussed, the project memory thins out — the cairn becomes a fossil instead of a living record.

The debrief is one batched review at the end of a working block.

## When to trigger

- **Explicit invocation**: the user says "debrief", "wrap up the session", "what should I record from today", or similar.
- **Inferred signals**: "ok we're done", "I have to go", "let's stop here", "good place to pick up tomorrow", "thanks — I'll come back to this".
- **Don't auto-trigger more than once per session** unless the user asks again. If you've already debriefed and new substantive things happened after, mention them in your next reply rather than triggering a second debrief unprompted.

## Steps

1. **Look at the working conversation** since the start of the session (or since the previous debrief in this session). Don't re-debrief things you've already captured live via the tracking-stance posture — those are committed; this is for what slipped through.

2. **Cross-reference existing IDs.** Skim `state/decisions.yaml` and `state/open_questions.yaml` for entries this session might be answering or relating to, so proposed captures can point at them via `--related`.

3. **Draft the candidate captures**, grouped by kind:
   - Decisions made (one-line statement + optional context + related IDs)
   - Findings worth recording (title + body, related IDs)
   - Action items committed to (assignee, text, due date if mentioned)
   - Open questions raised but not yet logged
   - Branch transitions, if any (a started or closed branch not yet recorded)

4. **Present the proposal as a single block.** Example:

   ```
   Debrief — captures from this session:

   Decisions (1):
     1. "We're going with stratified resampling rather than SMOTE for the rare class"
        → D-NNN, author: <user-id>, related: Q-007

   Findings (2):
     2. "Stratified resampling lifts rare-class recall ~5x vs SMOTE on the held-out set"
        → knowledge/findings/<today>-stratified-resampling-lift.md, related: D-NNN
     3. "SMOTE oversamples cluster boundaries too aggressively on this data"
        → knowledge/findings/<today>-smote-oversampling-issue.md

   Actions (1):
     4. "Maria will rerun the ablation by Friday"
        → A-NNN, assignee: maria, due: 2026-05-22

   Open questions (0): —

   Approve all? (yes / edit N / drop N / skip)
   ```

5. **Apply on approval.** Run one `cairn` command per item, in order. After each, emit the one-line notice (per the tracking stance). Show the final list of IDs once done.

6. **Handle revisions.** If the user says "edit 2" or "drop 4", revise/remove just that item and re-confirm the affected ones — don't re-render the whole proposal.

7. **Branch awareness.** If the user is on a non-main exploration branch, all captures land on that branch (the CLI handles this automatically). Mention this once in the proposal header: *"(captures will land on branch `<owner>/<slug>`)"*.

## What NOT to do

- **Don't fabricate captures.** If something was ambiguous in conversation, leave it out and say: *"I wasn't sure about X — capture it yourself if it matters."*
- **Don't double-capture.** If you already recorded something live earlier in the session, it's already in state — don't include it in the proposal.
- **Don't propose captures that don't fit the schemas.** "We had a nice chat about gradient descent" is not a finding. Findings need a specific, citable observation.
- **Don't include captures whose author is uncertain.** If you don't know which collaborator id should own a finding/decision/action, ask before assuming.

## Acceptance criteria

- Single round of bulk user confirmation rather than per-item ones.
- All applied captures are attributed to the right human author (not "claude" / "agent").
- Captures land on the current branch when the user is on an exploration branch.
- The user can revise individual items without redoing the whole review.
- Ambiguous items are surfaced as questions, not invented as captures.
