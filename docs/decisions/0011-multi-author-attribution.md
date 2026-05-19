# 0011 — Multi-author attribution on cairn entities

## Context

Today every writable cairn entity carries a **single** authorship field:

- `Decision.author: CollaboratorId`
- `FindingFrontmatter.author: CollaboratorId`
- `OpenQuestion.raised_by: CollaboratorId`
- `ActionItem.assignee: CollaboratorId`

This was fine for the original framing — cairn captures live conversation, and a typical capture has one person at the keyboard. But real research collaboration produces multi-author content that the schema can't represent honestly:

- **Pair coding / pair writing.** Two people working together produce one decision; the schema forces a choice of one as "the" author.
- **Group consensus.** A decision reached collectively at a meeting (or a Slack thread) has no single primary; today it's attributed to whoever happened to log it.
- **Retroactive bootstrap.** Observations extracted from a project's docs / TODO markers / git history don't have a single human author; the `bootstrap_from_repo` skill defaulted them to the project lead until OQ-5's `type="unknown"` stopgap shipped, which avoids over-crediting but doesn't represent shared authorship either.

The `type="group"` / `type="unknown"` collaborators shipped as the OQ-5 stopgap let users *name* shared and unattributable authorship, but they're still cosmetic at the schema level — the underlying field still says "this entity has one author." We end up with a `consensus` collaborator that hides who actually contributed, when the real information is the *list* of contributors.

UX testing of the StellaForge bootstrap surfaced this concretely: five findings derived from docs/potential_issues.md were attributed to the project lead by the agent's default ("speaks for the project"); when the user asked why, the agent acknowledged the over-crediting and proposed three structural answers. ADR-0011 picks the most direct of those.

## Decision

**Adopt plural authorship on the four writable entity types.** The fields are renamed:

| Entity | Today | After ADR-0011 |
|---|---|---|
| Decision | `author: CollaboratorId` | `authors: list[CollaboratorId]` (min_length=1) |
| FindingFrontmatter | `author: CollaboratorId` | `authors: list[CollaboratorId]` (min_length=1) |
| OpenQuestion | `raised_by: CollaboratorId` | `raised_by: list[CollaboratorId]` (min_length=1) |
| ActionItem | `assignee: CollaboratorId` | `assignees: list[CollaboratorId]` (min_length=1) |

The single-author case stays cheap: pass a one-element list. The multi-author case becomes representable: pass a list of ids in the order the user named them. No `co_authors` shadow field; no `author: str | list[str]` Pydantic union; no "primary author" concept at the schema level — list position is the only ordering signal, and consumers that need a "first" author can take index 0.

### Why plural-everywhere rather than `author + co_authors`

A two-field shape (`author: CollaboratorId` + `co_authors: list[CollaboratorId]`) was the obvious alternative — it preserves a primary author while making co-authorship optional. Rejected for three reasons:

1. **The "primary" notion is mostly fictional.** In pair coding, neither author is primary. In consensus, no one is. The two-field shape forces every consumer to either pick a primary (often arbitrarily) or carry both fields through every display. The cost of *requiring* a primary outweighs the convenience.

2. **Two-field shape has permanent dual surface.** Every read tool, every git commit message, every display rendering has to decide whether to show "author" or "author + co_authors". Plural-everywhere is one field, one source of truth.

3. **List position carries the lead-author signal naturally.** If a consumer really wants "the" author, take `authors[0]`. The convention is the user/agent's choice when listing, not the schema's constraint.

### Why plural-everywhere rather than `author: str | list[str]` Pydantic union

A union supports both legacy (single string) and new (list) shapes simultaneously. Rejected because:

1. Every consumer needs to type-check (`if isinstance(authors, list)`) every read — real plumbing cost, forever.
2. Pre-1.0, no users, so backward-compatibility isn't a real concern.
3. The union shape muddies what should be a clear "authorship is a list" semantic.

### Behavior at the surface

**MCP tools** (renames + plural parameters):

| Today | After |
|---|---|
| `add_decision(author: str, ...)` | `add_decision(authors: list[str], ...)` |
| `add_finding(author: str, ...)` | `add_finding(authors: list[str], ...)` |
| `add_open_question(raised_by: str, ...)` | `add_open_question(raised_by: list[str], ...)` |
| `add_action(assignee: str, ...)` | `add_action(assignees: list[str], ...)` |
| `list_decisions(author: str, ...)` filter | `list_decisions(any_author: str, ...)` filter — matches if any author in the list equals the value |
| `get_action_items(assignee: str, ...)` filter | `get_action_items(any_assignee: str, ...)` filter |

**CLI** (mirrors MCP):

| Today | After |
|---|---|
| `cairn decision add --author kyle ...` | `cairn decision add --author kyle [--author maria]` (repeatable; collected into a list) |
| `cairn action add --assignee kyle ...` | `cairn action add --assignee kyle [--assignee maria]` (repeatable) |

The repeatable-flag form is the idiomatic Typer pattern (already used by `--related` and `--expertise`), so users get the same muscle memory.

**Git commit messages** that mention authorship name them comma-separated when there are multiple — *"D-014: <text> (kyle, maria)"*. The single-author case looks identical to today's output. The git commit's *actual* author (in the git sense) is the person making the write — that field is separate and remains singular by git's own constraint.

**`status` and other displays** show `D-014 by kyle, maria` for multi-author entities and `D-014 by kyle` for single-author. JSON outputs carry `authors: ["kyle", "maria"]` consistently — the singular form is gone.

**Validation** runs per-element. Every id in the list must resolve to a registered collaborator (existing rule, just applied to a list). A list of length 1 is valid and is the default expectation; a list of length 0 raises a clear "authors cannot be empty" error.

### OQ-5 status after this ADR

The `type="group"` / `type="unknown"` collaborators stay useful — they're the answer for when authorship is *genuinely* aggregate or unknown, not just multi-person. The composition is:

- *"Pair coding by kyle and maria"* → `authors=["kyle", "maria"]`. Two humans, both credited.
- *"Group consensus among the methods team"* → `authors=["consensus"]` (the `type="group"` collaborator). The list-of-one form names the aggregate. Adding the actual humans alongside (`authors=["consensus", "kyle", "maria"]`) is also valid and useful when the group is small enough to enumerate.
- *"Observation extracted from project docs, no clear author"* → `authors=["repo-history"]` (the `type="unknown"` collaborator).

OQ-5 is **resolved by this ADR** for the multi-author dimension; the meeting / event-linkage dimension (OQ-5 option 3) remains open and is properly its own ADR when meetings become first-class.

## Consequences

- **Schema migration.** Decision, FindingFrontmatter, OpenQuestion, ActionItem all change their authorship-field name and type. Pre-1.0, no users, so this is a clean break with no migration tooling. Existing in-repo fixtures and tests update mechanically.

- **MCP tool surface shifts** at the parameter names: `author` → `authors`, `assignee` → `assignees`. Filter parameters rename to `any_author` / `any_assignee` because list-membership semantics are different from equality. The wider tool descriptions (entity-type "use when" framing, related-id constraints, date / source_prs / source_commits docs) are unchanged.

- **CLI commands shift** to repeatable `--author` / `--assignee` flags. Typer collects repeated flags into a list, matching the existing `--related` and `--expertise` patterns. The single-author case looks identical to today.

- **Display / rendering changes** are visible: status output, list_decisions JSON, git commit messages. The text form ("by kyle" / "by kyle, maria") is unobtrusive; the JSON form is the breaking-shape change.

- **OQ-5 multi-author dimension resolves.** OQ-5's option 2 IS this ADR; option 3 (meeting linkage) remains open. The `type="group"` and `type="unknown"` collaborators stay relevant for true-aggregate authorship — they compose with the plural field rather than replacing it.

- **Tests.** Every test that constructs or asserts on Decision / Finding / Question / Action authorship updates. Mechanical sweep.

- **AGENT-BOOTSTRAP.md, bundled SKILL.md files, TRACKING.md, and PROJECT.md template** need a pass for the new field names. The bootstrap_from_repo skill specifically gains guidance on when to use `authors=["repo-history"]` (the unknown placeholder) vs `authors=["kyle", "maria"]` (real co-authors) vs `authors=["consensus", "kyle", "maria"]` (group + enumerated members).

- **Out of scope, intentionally:** meeting / event linkage (`from_meeting: "2026-05-10"`) is OQ-5 option 3 and stays open. Adding `derived_from: <event-id>` becomes possible alongside plural authors once meetings are first-class; it doesn't conflict with this ADR.

- **Trigger for revisiting:** if list-of-authors turns out to be too thin (e.g., users want per-author roles like "wrote the rationale" vs "reviewed and approved"), a follow-up ADR can replace `authors: list[CollaboratorId]` with `authors: list[{id, role}]`. The plural-string shape is the simplest representation that's strictly more expressive than today's single-string; any future expansion is additive.

## Implementation order

Implementation should land as **one PR** since the schema change is unified — half-applying it leaves the cairn in an inconsistent state. Suggested order within the PR:

1. Schema changes (the four Pydantic models).
2. State-file I/O (load/write helpers — minimal changes since YAML is just deserializing lists already).
3. MCP tool signatures and CLI flag renames.
4. Display logic in `status` / `list_*` / git commit messages.
5. Tests: sweep existing tests for the field rename; add multi-author cases (pair coding, group + enumerated members, unknown-attribution).
6. Docs: AGENT-BOOTSTRAP, bundled skills, TRACKING.md, PROJECT.md template.
7. OQ-5 in `docs/open-questions.md` updates with the resolved-by-ADR-0011 status.

Estimated diff: ~500–700 LOC across schemas / tools / tests / docs.
