---
name: resolve-branch
description: Use when the user wraps up an exploration branch — either because the work has been merged into main, or because they're abandoning the direction. Records the closure in the branch manifest and moves the branch's row from the "Active branches" table to a "Closed branches" section in branches/README.md. Pairs with the start-branch skill.
---

# Close an exploration branch

Branches in a cairn carry meaning whether they merge or not. A finished exploration deserves closure: a manifest entry recording what happened and why, so the group can learn from the work later. Abandoned branches are part of the project's history — what was tried and why it was set aside.

## When to invoke this skill

The user signals closure with phrases like:

- "I merged that branch" / "we're done with kyle/try-alt-loss"
- "abandon that exploration" / "this didn't pan out"
- "close out the branch — we've taken what we needed"

If you're not sure whether the user means *close* or just *switch away*, ask.

## Steps

1. **Identify the branch** (`<owner>/<slug>`). If the user named it ambiguously ("the loss-function one"), inspect `branches/README.md` and `git branch --list '*/*'` and confirm with them before continuing.

2. **Identify the outcome**:
   - **merged** — the work made it onto main (via PR, fast-forward, manual merge, doesn't matter how). Required: the branch must actually be an ancestor of `main`. If not, ask the user to merge first.
   - **abandoned** — the exploration is over without merging. Either the result didn't pan out, or it's been superseded.

3. **Ask the user for a one-sentence reason.** This is the most important field: future readers will skim closure reasons to understand why a direction was set aside or what a merged branch contributed. Bad: "done". Good: "stratified resampling yielded 5x lift on rare class; promoted to main with finding 2026-05-18-stratified-beats-smote".

4. **Switch to main** (or master, whichever exists). The closure commit lands on main:

   ```sh
   git checkout main
   ```

5. **Run the command**:

   ```sh
   cairn branch close <owner>/<slug> \
     --status merged \
     --reason "<one-sentence outcome>"
   # or:
   cairn branch close <owner>/<slug> \
     --status abandoned \
     --reason "<one-sentence outcome>"
   ```

   For repos with multiple collaborators registered, add `--closed-by <id>`. The command:
   - Verifies the branch exists and (for `--status merged`) is an ancestor of main.
   - Refuses if the working tree has uncommitted changes (pass `--force` only if the user has explicitly weighed the trade-off).
   - Appends a closure block to `branches/<owner>/<slug>.md` with `status`, `closed_at`, `closed_by`, `reason`, and (for merged) a short merge commit SHA.
   - Moves the branch's row from the active table in `branches/README.md` to a "Closed branches" section.
   - Commits both files on main, attributed to the configured git user.

6. **Optionally clean up the branch ref.** Cairn only records the outcome — it does NOT delete the git branch. If the user wants the local branch gone:

   ```sh
   git branch -d <owner>/<slug>     # safe delete (refuses if unmerged)
   git branch -D <owner>/<slug>     # force delete; warn first
   ```

   The manifest stays. The branch ref disappearing doesn't erase the project's record.

## What to do if the merge requires review

If the user wants the branch reviewed before it's recorded as closed, the answer is **not** this skill — open a pull request and let the group discuss there. Use this skill only after the merge (or the decision to abandon) is final.

## What not to do

- Don't fabricate a `--reason`. If the user says "just close it", ask them why before running the command. The reason is the durable artifact, not the close itself.
- Don't pass `--force` without explicit user consent. Uncommitted work on the current branch is a real signal that the user has something in flight.
- Don't delete the branch ref as part of the closure flow unless the user asked. The ref and the manifest are independent.
- Don't close a branch that's currently checked out. Switch to main first.

## Acceptance criteria (US-A-09)

- The manifest at `branches/<owner>/<slug>.md` gains a `## Closure` block recording status, date, closer, reason, and (for merged) merge SHA.
- The row moves from the active table in `branches/README.md` to a closed section.
- For `--status merged`, the command refuses if the branch is not an ancestor of main.
- The closure commit is attributed to the invoking user and references the branch name.
- The manifest itself is never deleted — abandoned branches still belong in the project's history.
