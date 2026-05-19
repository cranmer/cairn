---
name: log-decision
description: Use when the user expresses a commitment with rationale that the team is making — "we'll go with…", "let's use X", "we decided to…", "I'm going to switch to…". Records the decision via the `add_decision` MCP tool (or `cairn decision add` CLI), attributed to the appropriate collaborator. Distinct from a *finding* (an observed fact), an *open question* (uncertainty awaiting resolution), and an *action item* (assigned pending work).
---

# Log a decision

A *decision* is a commitment with rationale — the team has chosen X over Y, even tentatively, and the rationale is worth preserving alongside the choice. Decisions live in `state/decisions.yaml`, attributed and timestamped, and are referenceable by ID (`D-NNN`) from later findings, actions, and open questions.

## When to trigger

The user says (or strongly implies) any of:

- "Let's go with X" / "we'll use X"
- "We decided to…" / "we're going to…" / "we settled on…"
- "I'm switching to X" (when it's a project-wide shift, not personal preference)
- "Stick with X" / "reject Y" (a *non*-adoption can still be a decision)

If a decision is being made but you're not sure of the wording, ask once: *"I'd record this as D-NNN: '<one-line summary>'. Sound right?"* Don't pause the conversation for every minor commitment — read TRACKING.md for the posture.

## Steps

1. **Identify the author** — the collaborator id whose commitment this is. The *orient* skill establishes the current user's id at session start; reuse that. If the decision is the group's rather than one person's, attribute it to the user who voiced it (in `state/collaborators.yaml`); a future feature may support multi-author attribution.

2. **Phrase the decision as one or two sentences.** The `text` field is the decision *itself* — what's been chosen. Keep it short and self-contained ("Use stratified resampling for the rare-class case"). The longer rationale goes in `context`.

3. **Identify related entities (optional)** — if this decision resolves an open question, supersedes a prior decision, or addresses an existing goal, include the relevant IDs (`Q-NNN`, `D-NNN`, `G-NNN`, `A-NNN`). Scan `state/open_questions.yaml` briefly to find matches; confirm with the user before adding.

4. **Invoke the action.** Two equivalent paths (see TRACKING.md):
   - **MCP** *(preferred when available)*: call `add_decision(author="<user-id>", text="...", context="...", related=[...])`. Pass `cairn="<name>"` if more than one cairn is registered.
   - **CLI**:

     ```sh
     cairn decision add \
       --author <user-id> \
       --text "<the decision>" \
       --context "<rationale or background>" \
       --related Q-007 \
       --related D-003
     ```

   The CLI / MCP returns the assigned ID (`D-NNN`) — surface it briefly: *"[recorded D-014: 'Use stratified resampling…']"*.

5. **For retroactive entries** (rare in live capture, common in bootstrap), pass `date` (ISO 8601) to backdate the decision to when it was actually made, and `source_commits` / `source_prs` to record git provenance as structured fields rather than burying it in `context`.

## What not to do

- **Don't log every preference as a decision.** "I like dark mode" is not a project decision. "We're standardizing on dark themes for screenshots" is.
- **Don't fabricate rationale.** If the `context` field would be guessed, ask the user once or leave it short.
- **Don't attribute to yourself.** Decisions belong to the humans who made them.
- **Don't ask the user to run the CLI command.** Use the MCP tool (or run the CLI yourself); the user shouldn't have to know cairn's surface.

## Acceptance criteria

- A new `D-NNN` exists in `state/decisions.yaml` with the right author, text, and (when relevant) context, related refs, and source provenance.
- The commit is attributed to the configured git user.
- The recorded notice in your reply is brief — one line, doesn't interrupt the conversation.
