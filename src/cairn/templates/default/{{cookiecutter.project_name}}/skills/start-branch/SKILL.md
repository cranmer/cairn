---
name: start-branch
description: Use when the user wants to explore an alternative approach the group can review later without disrupting main. Creates a `<user-id>/<short-description>` git branch, writes a branch manifest, updates the active-branches index on main, and leaves the user on the new branch.
---

# Create an exploration branch

Branches are first-class in a cairn. Use them whenever the work is genuinely speculative — an alternative loss function, a different dataset cut, a redo of an analysis with new assumptions. A branch that doesn't pan out is still useful project history.

## Steps

1. **Identify the user's collaborator id** from `state/collaborators.yaml`. If you don't already know it (the *orient* skill establishes this at session start), ask. Don't guess from the git email — confirm.

2. **Phrase the goal as a short kebab-case description** (3–6 words). Examples: "try alt loss function", "redo experiment without outliers", "explore causal forest variant". Keep it descriptive enough that someone reading the branch list later understands the purpose without context.

3. **Run the command**:

   ```sh
   cairn branch start "<short description>"
   # or, if there are multiple collaborators registered:
   cairn branch start "<short description>" --as <user-id>
   ```

   This will:
   - update `branches/README.md` on main with a new row,
   - create the branch `<user-id>/<kebab-slug>` and switch to it,
   - write a manifest at `branches/<user-id>/<slug>.md` capturing the proposed inquiry,
   - commit both, attributed to the configured git user.

4. **Edit the manifest** to fill in the TODO (initial rationale: *why* this is worth exploring now, and what would make it merge-worthy). The manifest is the artifact the group will look at when deciding whether to review or merge the branch later.

5. **Stay on the new branch** for the rest of the session unless the user says otherwise.

## What not to do

- Don't create a branch silently. Always confirm the description with the user before running the command.
- Don't reuse an existing branch name. The command refuses, but warn the user first if you suspect a collision.
- Don't write findings, decisions, or other state to `main` after switching to a branch — branches contain their own forward-looking layer.

## Acceptance criteria (US-A-03)

- Branch name follows `<user-id>/<short-description>` (kebab-case).
- `branches/README.md` is updated on main.
- A manifest file exists at `branches/<user-id>/<slug>.md`.
- The user is left on the new branch with session context intact.
- A same-name collision prompts for resolution rather than silently overwriting.

## When the branch is done

Every exploration branch eventually gets resolved — either it merges into main or it's abandoned. Both are valuable history. When the user signals the work is wrapping up ("we're done", "this didn't pan out", "I merged that"), use the **resolve-branch** skill (`cairn branch close`) to record the outcome in the manifest and move the row to the "Closed branches" section of `branches/README.md`. Don't let exploration branches accumulate without closure — that's how branch lists become noisy and the group loses track of what's actually live.
