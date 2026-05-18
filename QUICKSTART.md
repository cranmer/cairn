# Quickstart

A five-minute path from a clean clone to a working cairn.

> **Want your agent to do this for you?** See [`AGENT-BOOTSTRAP.md`](AGENT-BOOTSTRAP.md). Paste that file into a fresh Claude Code session and the agent will install Cairn, scaffold a new cairn, and register you as the first collaborator — pausing for your confirmation at each major step.

## 1. Install

Requires **Python ≥ 3.10** and `git` on PATH.

```sh
git clone https://github.com/cranmer/cairn.git
cd cairn
pip install -e ".[dev]"
```

Verify:

```sh
cairn --help
```

You should see the available subcommands: `init`, `collaborator`, `decision`, `validate`, `status`, `version`.

## 2. Configure your git identity (one-time)

Cairn refuses to scaffold a cairn without a configured git identity — every commit, by any actor, carries attribution.

```sh
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"
```

## 3. Create a cairn

```sh
cd /tmp                              # or anywhere outside the framework repo
cairn init my-project --no-input
cd my-project
```

This scaffolds the canonical layout (`state/`, `knowledge/`, `skills/`, `branches/`, plus `PROJECT.md` and `README.md`), seeds empty-but-valid YAML state files, and creates the initial git commit attributed to you.

```sh
git log --oneline                    # one initial commit
ls state/                            # five YAML files, all []
```

## 4. Add collaborators and a decision

```sh
cairn collaborator add --id you   --name "Your Name"    --role "project lead"
cairn collaborator add --id maria --name "Maria Santos" --role "methods" \
                       --expertise "causal inference" --expertise R

cairn decision add --author you \
                   --text   "Use stratified resampling for the imbalanced classes" \
                   --context "Discussed in meeting; alternative was SMOTE"

cairn action add --assignee maria --text "rerun model on rare-class subset" --due-date 2026-06-01
cairn finding add --author you \
                  --title "Stratified resampling beats SMOTE on rare events" \
                  --related D-001
```

Each command stages and commits its change, attributed to you. The decision is auto-assigned `D-001`, the action `A-001`, with UTC ISO 8601 timestamps. The finding lands at `knowledge/findings/<today>-stratified-resampling-beats-smote-on-rare-events.md`.

## 5. Inspect

```sh
cairn validate                       # exit 0 — schema and cross-refs are clean
cairn status                         # compact summary, <30 lines
cairn status --json | python -m json.tool   # machine-readable
```

Try breaking things to see the failure modes:

```sh
# Edit state/decisions.yaml and add a dangling reference like
#   related: [Q-999]
cairn validate                       # exit 1, names the file + entity + bad ref
```

## What's where

- `state/decisions.yaml`, `open_questions.yaml`, `action_items.yaml`, `goals.yaml`, `collaborators.yaml` — canonical state.
- `knowledge/meetings/`, `findings/`, `literature/`, `provenance/` — accumulating project knowledge.
- `skills/` — procedural skills available to agents working in this cairn.
- `branches/README.md` — index of active exploration branches.
- `PROJECT.md` — short orientation file an agent reads first.

## Bulk input via YAML

```sh
cat <<'EOF' > team.yaml
- id: kyle
  name: Kyle Cranmer
  role: project lead
- id: lit-monitor
  name: Literature Monitor
  role: literature monitor
  type: ai-collaborator
  trigger: weekly
EOF

cairn collaborator add --yaml team.yaml
# or:  cat team.yaml | cairn collaborator add --yaml -
```

## Other templates

```sh
cairn init my-other --template /path/to/local/template --no-input
# or, with the optional cookiecutter extra:
pip install -e ".[cookiecutter]"
cairn init my-other --template https://github.com/example/template
```

## Run the tests

```sh
pytest                               # full suite (~5s)
ruff check src tests                 # lint
```

## Where to go next

- `ARCHITECTURE.md` — the design document.
- `USER_STORIES.md` — testable user stories (US-NN IDs). The primary specification.
- `CLAUDE.md` — conventions for contributing.
- `docs/decisions/` — architectural decision records.
