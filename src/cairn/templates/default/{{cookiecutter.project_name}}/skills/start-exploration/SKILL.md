---
name: start-exploration
description: Use when the user wants to track an alternative line of inquiry the group can review later — a different methodology, an alternative analysis, a divergent design. Creates a `<user-id>/<short-description>` git branch in the cairn, writes an exploration manifest, updates the active-explorations index on main, and leaves the user on the new branch.
---

# Start a cairn exploration

A *cairn exploration* is an optional augmentation for tracking an alternative line of inquiry whose rationale itself is the artifact worth preserving. Materialized as a git branch in the cairn repo plus an `explorations/<owner>/<slug>.md` manifest. Use whenever the work is genuinely speculative — an alternative loss function, a different dataset cut, a redo of an analysis with new assumptions. An exploration that doesn't pan out is still useful project history.

> **Not the same as a git branch in the user's project repo.** If the user says "let's branch this" while doing project work, that usually means a git branch in their project's code repo (the git-native answer). A cairn exploration is the explicit alternative for rationale-tracked work that benefits from a manifest, comparison, and an explicit merge moment. When ambiguous, ask which they mean before running this skill.

## Steps

1. **Identify the user's collaborator id** from `state/collaborators.yaml`. If you don't already know it (the *orient* skill establishes this at session start), ask. Don't guess from the git email — confirm.

2. **Phrase the goal as a short kebab-case description** (3–6 words). Examples: "try alt loss function", "redo experiment without outliers", "explore causal forest variant". Keep it descriptive enough that someone reading the explorations list later understands the purpose without context.

3. **Invoke the action.** Two equivalent paths (see TRACKING.md):
   - **MCP** *(preferred when available)*: call `start_exploration(description="...", as_id="<user-id>")`. The Tier-1 MCP server may not expose this tool yet; fall back to the CLI in that case.
   - **CLI**:

   ```sh
   cairn exploration start "<short description>"
   # or, if there are multiple collaborators registered:
   cairn exploration start "<short description>" --as <user-id>
   ```

   This will:
   - update `explorations/README.md` on main with a new row,
   - create the git branch `<user-id>/<kebab-slug>` in the cairn and switch to it,
   - write a manifest at `explorations/<user-id>/<slug>.md` capturing the proposed inquiry,
   - commit both, attributed to the configured git user.

4. **Edit the manifest** to fill in the TODO (initial rationale: *why* this is worth exploring now, and what would make it merge-worthy). The manifest is the artifact the group will look at when deciding whether to review or merge the exploration later.

5. **Stay on the new git branch** for the rest of the session unless the user says otherwise.

## What not to do

- Don't create an exploration silently. Always confirm the description with the user before running the command.
- Don't reuse an existing exploration name. The command refuses, but warn the user first if you suspect a collision.
- Don't write findings, decisions, or other state to `main` after switching to an exploration — explorations carry their own forward-looking layer.
- Don't auto-create an exploration when the user just wants a project-repo git branch. When the user is doing actual coding work, a project-repo branch is usually the right answer.

## Acceptance criteria (US-A-03)

- Git-branch name in the cairn repo follows `<user-id>/<short-description>` (kebab-case).
- `explorations/README.md` is updated on main.
- A manifest file exists at `explorations/<user-id>/<slug>.md`.
- The user is left on the new git branch with session context intact.
- A same-name collision prompts for resolution rather than silently overwriting.

## When the exploration is done

Every exploration eventually gets resolved — either it merges into main or it's abandoned. Both are valuable history. When the user signals the work is wrapping up ("we're done", "this didn't pan out", "I merged that"), use the **resolve-exploration** skill (`cairn exploration close`) to record the outcome in the manifest and move the row to the "Closed explorations" section of `explorations/README.md`. Don't let explorations accumulate without closure — that's how lists become noisy and the group loses track of what's actually live.
