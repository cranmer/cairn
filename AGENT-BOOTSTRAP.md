# Bootstrap a new cairn — instructions for a Claude Code session

**You** (Claude Code, the agent reading this) are being asked to set up a new *cairn* — a git-native shared memory for a research project — on the user's machine. The user has pasted this file to you. Follow these instructions; pause for confirmation at the **★** marks before taking the listed action. Do not skip ahead.

If the user has already created a cairn and just wants you to orient inside it, this file is the wrong one — point them at `QUICKSTART.md` and stop.

## What you're going to do

1. Verify the user has Python ≥ 3.10 and `git` on PATH.
2. Install the `cairn` package (from GitHub, since Cairn is not yet on PyPI).
3. Confirm or set the user's git identity.
4. Scaffold a new cairn at a location the user agrees to.
5. Register the user as the first collaborator.
6. Show the user what they have and how to use the bundled skills.

## Step 1 — Verify prerequisites

Run both, in parallel:

```sh
python --version    # need >= 3.10
git --version       # any recent version
```

If either is missing or below the required version, **stop** and tell the user what to install before continuing. Do not try to install Python or git for them.

## Step 2 — Choose an install environment ★

Ask the user which Python environment they want to install into. Offer (in this order):

1. **A fresh virtual environment** at `~/.venvs/cairn` (recommended if they don't have a preference).
2. **A user-supplied venv / pixi / uv / conda environment** they already have active.
3. **The system Python** (last resort — warn that `pip install --user` is preferred over global).

Wait for their choice. Then run the install:

```sh
# Option 1 — fresh venv:
python -m venv ~/.venvs/cairn && source ~/.venvs/cairn/bin/activate

# Then, in whichever environment they chose:
pip install git+https://github.com/cranmer/cairn
```

Verify the install worked:

```sh
cairn --help     # should list init, collaborator, decision, action, branch, finding, validate, status, version
cairn version
```

If `cairn --help` doesn't work, troubleshoot the PATH before continuing.

## Step 3 — Confirm git identity ★

Run:

```sh
git config --global user.name
git config --global user.email
```

If both return values: echo them back to the user and ask if they should be used as the cairn's identity. (`cairn init` will refuse to commit without them.)

If either is missing: ask the user for the value, then set it:

```sh
git config --global user.name  "Their Name"
git config --global user.email "they@example.com"
```

Do not invent values. Cairn's substrate-as-truth principle dislikes synthesized identities — the commit author must be the real human.

## Step 4 — Choose where the cairn will live ★

Ask the user:

- **Project name** (short, kebab-case if possible — this becomes the directory name and a few labels inside `PROJECT.md`).
- **Parent directory** (defaults to `~/projects/` or wherever they keep their work).
- **PI name** (the principal investigator; can be the user themselves).

Echo all three values back, then ask "shall I proceed?" before running:

```sh
cd <parent-directory>
cairn init <project-name> --pi-name "<PI Name>" --no-input
cd <project-name>
```

Verify:

```sh
ls                  # README.md, PROJECT.md, state/, knowledge/, skills/, branches/
git log --oneline   # one commit "Initial commit: scaffold cairn '<name>'"
cat state/collaborators.yaml   # should be "[]"
```

## Step 5 — Register the user as the first collaborator ★

Ask the user:

- **Collaborator id** — short, kebab-case, lowercase (e.g., `kyle`, `maria-s`). This is the canonical handle used in attributions and cross-references throughout the cairn.
- **Role** (e.g., "PI", "postdoc", "PhD student", "RA").
- Optional: GitHub handle, expertise tags, current focus.

Then run:

```sh
cairn collaborator add \
  --id <chosen-id> \
  --name "<Their Full Name>" \
  --role "<role>" \
  [--github <handle>] \
  [--expertise <topic> --expertise <topic>] \
  [--current-focus "<short description>"]
```

Verify:

```sh
cat state/collaborators.yaml
git log --oneline   # the new commit "Add collaborator '<id>'"
```

## Step 6 — Show the user what they have

Tell the user that the cairn now includes five bundled `SKILL.md` files under `skills/`:

- **orient** — what you (the agent) should read at session start to be useful without burning context.
- **search-history** — local-file scan for "was X considered?" questions.
- **start-branch** — wraps `cairn branch start "<desc>"` for exploratory work.
- **complete-action** — wraps `cairn action complete <id>` when something gets done.
- **log-finding** — wraps `cairn finding add` when the user discovers something worth recording.

Suggest two concrete next steps they might take in this session:

1. Edit `PROJECT.md` to fill in the project overview and current focus (the file ships with TODO markers).
2. Add a goal or two with `cairn decision add` / `cairn action add` so the cairn has real state to be useful against.

End with:

```sh
cairn status        # compact summary, <30 lines
cairn validate      # confirms schema + cross-references are clean
```

## What to do if anything fails

- **`cairn` command not found after install**: the install env's `bin/` isn't on PATH. Tell the user; offer to use the absolute path (`~/.venvs/cairn/bin/cairn …`) for the rest of the session.
- **`cairn init` errors with "no git user identity configured"**: go back to Step 3 and set it; do not invent.
- **`cairn init` errors with "refusing to overwrite"**: a directory with that name already exists. Ask the user whether to pick a new name or pass `--force` (which deletes the existing directory; warn first).
- **Any schema or YAML error**: stop, show the user the exact error, and ask how to proceed. Do not edit state files by hand to "fix" them without confirmation.

## What you should *not* do

- Do not commit on the user's behalf without showing them the proposed commit message first (after this bootstrap is complete; during bootstrap, the `cairn` CLI handles attribution).
- Do not install global pip packages without confirming the environment in Step 2.
- Do not run `git config --global` to change values the user already has set.
- Do not create more than one cairn in this session. One project = one cairn.

## When you're done

Tell the user:

> Your cairn `<name>` is live at `<absolute-path>`. The skills in `skills/<…>/SKILL.md` are now available to me for this session. Ask me to *orient* whenever you want a status summary, or just describe what you want to do next — I'll pick the right skill.

Then stop. The user will direct the next step.
