# {{cookiecutter.project_name}}

A research project organized as a *cairn* — a git-native substrate for the group's shared memory: decisions, open questions, action items, meetings, findings, and the people (human and AI) contributing to it.

## Getting started

- `PROJECT.md` is the orientation file. Read it first.
- `state/` holds the canonical YAML state files; edit them via `cairn` commands or by hand.
- `knowledge/` accumulates meeting notes, findings, literature, and provenance artifacts.
- `branches/README.md` indexes active exploration branches.

## Quick reference

```sh
cairn status                                    # summary of where things stand
cairn collaborator add --id <id> --name "..." --role <role>
cairn decision add --author <id> --text "..."
cairn validate                                  # check schema + cross-references
```

See the Cairn project documentation for the full set of conventions.
