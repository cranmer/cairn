---
name: search-history
description: Use when the user asks about prior context in this cairn ("was X considered?", "what did we decide about Y?", "has anyone looked at Z?"). Searches local files — meetings, findings, decisions, open questions — without relying on a vector index or external service. Returns excerpts with source path, date, and author so answers can be cited.
---

# Search prior discussions

The cairn's history lives in plain files on disk. For most queries, that's all you need.

## Where to search

- `state/decisions.yaml` — keyword scan; each entry has `id`, `date`, `author`, `decision`, `context`.
- `state/open_questions.yaml` — keyword scan; each entry has `id`, `raised_by`, `date`, `question`.
- `knowledge/meetings/*.md` — one file per meeting, named `YYYY-MM-DD.md`. Speaker-attributed.
- `knowledge/findings/*.md` — logged findings with frontmatter (`date`, `author`).
- `knowledge/literature/` — paper notes.

## How to search

1. **Identify keywords** from the user's question. Include obvious synonyms but don't expand too aggressively — exact-string matches are usually what the user wants.

2. **Use `grep -rinE` (or the editor's equivalent)** across `state/`, `knowledge/`, and `branches/`. Read excerpts in context (a few lines before and after the match), not just the matched line.

3. **For YAML state files**, prefer reading the whole entry that contains the match — a decision is small, and the `context` field often carries the actual reasoning.

4. **Filter by branch.** If the user is on a non-main branch, scope to the branch's view of state files (`git show <branch>:state/decisions.yaml`). Don't accidentally cite something that was decided on a branch the user has never seen.

## How to answer

Cite each excerpt with **source path + date + author**. Examples:

- "On 2026-04-22, kyle recorded D-014: *Use stratified resampling…* (context: SMOTE was the alternative)."
- "Maria raised Q-012 on 2026-05-08 about whether the bias correction introduces identifiability problems — still open."
- "In the 2026-05-15 meeting (`knowledge/meetings/2026-05-15.md`), the group discussed…"

Empty results: say so plainly. Don't fabricate.

## When to escalate beyond local files

This skill is intentionally low-tech. If the cairn has an MCP server attached and the user's question is genuinely semantic (no obvious keywords), prefer the MCP tool `find_related_prior_discussion`. Otherwise, file scans are faster and avoid invented relevance.

## Acceptance criteria (US-A-05)

- No embeddings or external services required.
- Each result is attributable (source path, date, author).
- Results are scoped to the current branch's view of the cairn.
