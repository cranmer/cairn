---
name: complete-action
description: Use when the user says they have finished a task that corresponds to an action item ("I'm done with the outline", "that's shipped", "rerun is complete"). Updates `state/action_items.yaml` so status becomes `complete`, with completion timestamp and completer recorded. Keeps history — the entry is never deleted.
---

# Mark an action item complete

Action items in `state/action_items.yaml` track outstanding work. When something gets done, we record it — both for accountability and so the next agenda doesn't surface stale items.

## Steps

1. **Resolve the action id**. If the user said "I'm done with the outline":
   - Read `state/action_items.yaml` and find the matching open action by `text` similarity and `assignee` (likely the current user).
   - If the match is unambiguous, proceed with its id (e.g., `A-014`).
   - If ambiguous or no match, ask the user which `A-NNN` they mean and list the open candidates.

2. **Invoke the action.** Two equivalent paths (see TRACKING.md):
   - **MCP** *(preferred when available)*: call `complete_action(id="A-014", by="<user-id>")`. Pass `cairn="<name>"` if more than one cairn is registered.
   - **CLI**:

   ```sh
   cairn action complete A-014
   # If a different collaborator finished it on someone else's behalf:
   cairn action complete A-014 --by <other-id>
   ```

   The command refuses if the id doesn't exist, or if it's already complete. It records:
   - `status: complete`
   - `completed_at` (UTC ISO timestamp)
   - `completed_by` (collaborator id)
   …and keeps the original entry in place (we don't delete).

3. **Ask about follow-ups**. Completing an action often implies a follow-up — a finding to log, a decision to record, a related open question now answered. Prompt the user:

   - "Want to record what you learned as a finding?" (deferred — Phase 2)
   - "Did this answer Q-NNN? If so, we should update its status."
   - "Should this become a recorded decision (`cairn decision add`)?"

   Don't act on these without the user's say-so.

## Acceptance criteria (US-A-04)

- The completed action keeps its history (not deleted).
- `status`, `completed_at`, `completed_by` are recorded.
- If completion implies a follow-up, the user is prompted to capture it.
- The commit message references the action id for traceability.
