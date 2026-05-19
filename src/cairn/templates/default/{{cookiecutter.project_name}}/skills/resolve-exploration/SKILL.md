---
name: resolve-exploration
description: Use when the user wraps up a cairn exploration — either because the work has been merged into main, or because they're abandoning the direction. Records the closure in the exploration's manifest and moves its row from the "Active explorations" table to a "Closed explorations" section in explorations/README.md. Pairs with the start-exploration skill.
---

# Close a cairn exploration

Explorations in a cairn carry meaning whether they merge or not. A finished exploration deserves closure: a manifest entry recording what happened and why, so the group can learn from the work later. Abandoned explorations are part of the project's history — what was tried and why it was set aside.

## When to invoke this skill

The user signals closure with phrases like:

- "I merged that exploration" / "we're done with kyle/try-alt-loss"
- "abandon that exploration" / "this didn't pan out"
- "close out the exploration — we've taken what we needed"

If you're not sure whether the user means *close* or just *switch away*, ask. And if they say "close that branch" while doing project-repo work, confirm they mean a cairn exploration and not a project-repo git branch.

## Steps

1. **Identify the exploration** (`<owner>/<slug>`). If the user named it ambiguously ("the loss-function one"), inspect `explorations/README.md` and `git branch --list '*/*'` in the cairn and confirm with them before continuing.

2. **Identify the outcome**:
   - **merged** — the work made it onto main (via PR, fast-forward, manual merge, doesn't matter how). Required: the exploration's git branch must actually be an ancestor of `main`. If not, ask the user to merge first.
   - **abandoned** — the exploration is over without merging. Either the result didn't pan out, or it's been superseded.

3. **Ask the user for a one-sentence reason.** This is the most important field: future readers will skim closure reasons to understand why a direction was set aside or what a merged exploration contributed. Bad: "done". Good: "stratified resampling yielded 5x lift on rare class; promoted to main with finding 2026-05-18-stratified-beats-smote".

4. **Switch to main** (or master, whichever exists) in the cairn. The closure commit lands on main:

   ```sh
   git checkout main
   ```

5. **Invoke the action.** Two equivalent paths (see TRACKING.md):
   - **MCP** *(preferred when available)*: call `close_exploration(name="<owner>/<slug>", status="merged"|"abandoned", reason="...", closed_by="<id>")`. The Tier-1 MCP server may not expose this tool yet; fall back to the CLI in that case.
   - **CLI**:

   ```sh
   cairn exploration close <owner>/<slug> \
     --status merged \
     --reason "<one-sentence outcome>"
   # or:
   cairn exploration close <owner>/<slug> \
     --status abandoned \
     --reason "<one-sentence outcome>"
   ```

   For repos with multiple collaborators registered, add `--closed-by <id>`. The command:
   - Verifies the exploration's git branch exists and (for `--status merged`) is an ancestor of main.
   - Refuses if the working tree has uncommitted changes (pass `--force` only if the user has explicitly weighed the trade-off).
   - Appends a closure block to `explorations/<owner>/<slug>.md` with `status`, `closed_at`, `closed_by`, `reason`, and (for merged) a short merge commit SHA.
   - Moves the exploration's row from the active table in `explorations/README.md` to a "Closed explorations" section.
   - Commits both files on main, attributed to the configured git user.

6. **Optionally clean up the git branch ref.** Cairn only records the outcome — it does NOT delete the git branch. If the user wants the local branch gone:

   ```sh
   git branch -d <owner>/<slug>     # safe delete (refuses if unmerged)
   git branch -D <owner>/<slug>     # force delete; warn first
   ```

   The manifest stays. The git ref disappearing doesn't erase the project's record.

## What to do if the merge requires review

If the user wants the exploration reviewed before it's recorded as closed, the answer is **not** this skill — open a pull request and let the group discuss there. Use this skill only after the merge (or the decision to abandon) is final.

## What not to do

- Don't fabricate a `--reason`. If the user says "just close it", ask them why before running the command. The reason is the durable artifact, not the close itself.
- Don't pass `--force` without explicit user consent. Uncommitted work on the current branch is a real signal that the user has something in flight.
- Don't delete the git branch ref as part of the closure flow unless the user asked. The ref and the manifest are independent.
- Don't close an exploration whose git branch is currently checked out. Switch to main first.

## Acceptance criteria (US-A-09)

- The manifest at `explorations/<owner>/<slug>.md` gains a `## Closure` block recording status, date, closer, reason, and (for merged) merge SHA.
- The row moves from the active table in `explorations/README.md` to a closed section.
- For `--status merged`, the command refuses if the exploration's git branch is not an ancestor of main.
- The closure commit is attributed to the invoking user and references the exploration name.
- The manifest itself is never deleted — abandoned explorations still belong in the project's history.
