---
name: log-action
description: Use when the user assigns pending work to someone (themselves or another collaborator) — "I'll handle X", "can you take care of Y by Friday?", "P will do Z". Records the action item via the `add_action` MCP tool (or `cairn action add` CLI). Distinct from a *decision* (commitment with rationale), *finding* (observed fact), and *open question* (uncertainty awaiting resolution).
---

# Log an action item

An *action item* is assigned pending work — someone owes someone else something, optionally by a date. Actions live in `state/action_items.yaml` and are marked complete (rather than deleted) when finished, preserving history.

## When to trigger

The user says (or strongly implies) any of:

- "I'll handle X" / "I'll take care of Y" / "I'm on it"
- "Can you (P) do X?" / "P will handle Y"
- "X by Friday" / "due next week" / "before the meeting"
- "Remind me to…" / "we need to do X" (when followed by an assignee)

The triggers are usually voice + tense + assignee. *"Someone should look at X"* is an open question, not an action; *"Maria will look at X by Friday"* is an action.

## Steps

1. **Identify the assignee** — the collaborator id whose task this is. Match against `state/collaborators.yaml`. If the user says "I'll do it", the assignee is the current user (resolved via the *orient* skill or git config). If the user says "P will do it", confirm the id matches.

2. **Phrase the action as a short imperative.** "Rerun model on rare-class subset", "Send draft to Maria for review", "Update the related-repos section of PROJECT.md". One sentence, action-shaped.

3. **Capture the due date (if mentioned).** Optional but encouraged when given. ISO calendar form (`YYYY-MM-DD`). Don't invent a due date — if the user said "soon" without specifics, leave it null.

4. **Identify related entities (optional)** — if the action follows from a decision, addresses an open question, or contributes to a goal, include the relevant IDs.

5. **Invoke the action.** Two equivalent paths (see TRACKING.md):
   - **MCP** *(preferred when available)*: call `add_action(text="...", assignee="<user-id>", due_date="2026-06-01", related=[...])`. Pass `cairn="<name>"` if more than one cairn is registered.
   - **CLI**:

     ```sh
     cairn action add \
       --assignee <user-id> \
       --text "<the action>" \
       --due-date 2026-06-01 \
       --related D-014
     ```

   Surface the assigned `A-NNN` briefly: *"[recorded A-022: assigned to maria, due 2026-06-01]"*.

6. **For retroactive entries**, pass `date` (ISO 8601) to backdate the action's creation timestamp — useful when reconstructing forgotten assignments from past conversations. Note `due_date` and `date` are different fields: `date` is creation time, `due_date` is the deadline.

## When the work is done

When the user signals completion ("done", "shipped", "wrapped up X"), use the **complete-action** skill (`complete_action` MCP tool / `cairn action complete <id>` CLI) — it preserves the action's history and records who completed it and when, rather than deleting the entry.

## What not to do

- **Don't log every "let me think about that" as an action.** That's an open question if anything.
- **Don't invent due dates.** If unspecified, leave `due_date` null.
- **Don't assign to yourself (the agent).** Actions belong to humans (or registered AI collaborators with the right type).
- **Don't ask the user to run the CLI.** Use the MCP tool (or run the CLI yourself).
- **Don't write retroactive actions for *completed* work** — use a finding for "we did X" and skip dated actions. Actions are for pending work.

## Acceptance criteria

- A new `A-NNN` exists in `state/action_items.yaml` with the right assignee, text, optional due_date, and (when relevant) related refs.
- The commit is attributed to the configured git user.
- The recorded notice in your reply is brief — one line, includes the id, assignee, and due date if any.
