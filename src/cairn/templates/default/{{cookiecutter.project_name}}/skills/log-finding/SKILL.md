---
name: log-finding
description: Use when the user expresses something they want recorded as a finding ("we just learned that…", "remember this finding…", "log that…", "we discovered…"). Writes a new markdown file under knowledge/findings/ with proper YAML frontmatter (date, author, related references). The author is the human, not you. If the user is on a branch, the finding lands there.
---

# Log a finding

A *finding* is a small piece of learned knowledge worth keeping — an empirical observation, an unexpected behavior, a result that should inform future work. Findings live as markdown files under `knowledge/findings/` with YAML frontmatter.

## Steps

1. **Confirm scope with the user.** Findings should be specific and citable, not vague. If they said "we just learned that X", echo a one-sentence framing back and ask if that's right before writing anything. Don't expand a casual remark into a finding without consent.

2. **Identify the author** (the human, not you). The *orient* skill establishes the current user's collaborator id at session start; reuse that. If you don't know it, ask. The author field is set to the human — never to "claude" or "agent".

3. **Pick related entity ids** (optional but encouraged). If this finding bears on an open question, a recent decision, or an existing goal, include those IDs (`Q-NNN`, `D-NNN`, `G-NNN`, `A-NNN`). Scan `state/decisions.yaml` and `state/open_questions.yaml` briefly to find candidates; confirm with the user before adding them.

4. **Run the command**:

   ```sh
   cairn finding add \
     --author <user-id> \
     --title "<one-sentence finding>" \
     --related D-014 \
     --related Q-007 \
     --body "<body text or use --body-from FILE for longer bodies>"
   ```

   This will:
   - derive a kebab-case slug from `--title` (override with `--slug`),
   - write `knowledge/findings/YYYY-MM-DD-<slug>.md` with frontmatter (`date`, `author`, `title`, `slug`, `related`, `branch`),
   - stage and commit the file, attributed to the configured git user.

5. **Default to asking before committing.** By default the CLI commits immediately, which is the right behavior when *you* (the agent) are invoking it on the user's behalf and they've just confirmed the finding. If you sense any hesitation in the user, pass `--no-commit`: the file is still written, but the user can review and `git commit` it themselves.

6. **Branch awareness.** The CLI records the current branch in the frontmatter automatically. If the user is on an exploration branch, the finding lands there (not on main). Don't merge or switch branches; let the user decide later whether to promote the finding.

## What not to do

- Don't write a finding without an explicit cue from the user. "Interesting" observations from your own reasoning are not findings.
- Don't backdate. The date in the frontmatter is today's date (UTC); the CLI handles this.
- Don't attribute the finding to yourself. Authors are humans; AI contributions go through the review queue (Phase 5, not yet built).

## Acceptance criteria (US-A-02)

- The file is at `knowledge/findings/YYYY-MM-DD-<short-slug>.md` with proper frontmatter.
- The author is the current human user.
- If on a branch, the finding lands on that branch.
- A git commit is staged; the agent defaults to asking confirmation before committing for less-experienced users.
