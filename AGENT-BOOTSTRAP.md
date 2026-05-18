# Bootstrap a new cairn — instructions for a Claude Code session

**You** (Claude Code, the agent reading this) are being asked to set up a new *cairn* — a git-native shared memory for a research project — on the user's machine. The user has pasted this file to you. Follow these instructions; pause for confirmation at the **★** marks before taking the listed action. Do not skip ahead.

If the user has already created a cairn and just wants you to orient inside it, this file is the wrong one — point them at `QUICKSTART.md` and stop.

## Two access modes — know which one you're setting up

A cairn is a *separate* git repo from the project's working code/data/paper repos (see README.md's "A cairn is not a project's code repo" section). That means a user can have an agent session open in one of two places, and **the mode is set the moment the user launched Claude Code — it is not changed by you `cd`ing during bootstrap**:

- **Mode A** — session opened inside the cairn directory. The cairn's SessionStart hook fires once and runs `cairn status`, so you get a project-state context dump for free. The bundled SKILL.md files are *procedural prose* the agent reads on demand — they are not registered Claude Code skills and won't appear in the user's `/skills` list until ADR-0006 Stage 3 (`cairn skills install`) ships. Same applies to `TRACKING.md`: it's a file the agent reads, not a posture the harness loads.
- **Mode B** — session opened anywhere else, typically inside a project's code repo. The SessionStart hook does not fire; no `cairn status` runs automatically. You can still drive the cairn by `cd`ing into it or using absolute paths, and you can still read the SKILL.md procedures from `<cairn>/skills/<name>/SKILL.md` on demand. Cross-repo discovery so a session inside a project repo finds its paired cairn without ceremony is on the roadmap (ADR-0006 Stage 2 — `cairn link` + a project-repo `cairn.toml` pointer file) but **not yet in v0**.

This bootstrap doc creates a cairn. **It does not change the current session's mode** — Mode A vs Mode B is set by where the user launched Claude Code, not by where you `cd`. At the end, report mode honestly; don't claim Mode A just because your *current* cwd is the cairn directory. The "When you're done" section spells this out.

If the user mentions they already have a project repo with code in it, the cairn you scaffold lives **alongside** that repo (e.g., `~/projects/foo-cairn/` next to `~/projects/foo/`), never inside it. You do not modify the existing project repo during bootstrap.

**Capture initial cwd at session start** (e.g., the first `pwd` you run, before any `cd`) — you will need it at the end to determine which mode this session was opened in.

## Session affordances you should use

Two things about your Claude Code session that matter for this bootstrap:

- **Working directory persists** across your Bash tool calls. One `cd <project-path>` after the cairn is created is enough — every subsequent command runs in that directory unless you `cd` away. The user shouldn't have to see repeated `cd` lines.
- **Shell state does NOT persist** between Bash calls. Anything you `source`, `export`, or `conda activate` is gone by the next tool call. This is why we strongly prefer pipx in Step 2: it puts `cairn` on the user's normal PATH so you don't have to fight activation. For the env-based fallback path, see the `.claude/settings.local.json` trick in Step 6.5 — it makes PATH changes durable across your Bash calls.

## What you're going to do

1. Verify the user has Python ≥ 3.10 and `git` on PATH.
2. Install the `cairn` package (from GitHub, since Cairn is not yet on PyPI).
3. Confirm or set the user's git identity.
4. Scaffold a new cairn at a location the user agrees to.
5. Register the user as the first collaborator.
6. Show the user what they have and how to use the bundled skills.
7. (If env-based install) write `.claude/settings.local.json` so this session lives *inside* the cairn instead of fighting activation.

## Step 1 — Verify prerequisites

Run both, in parallel:

```sh
python --version    # need >= 3.10
git --version       # any recent version
```

If either is missing or below the required version, **stop** and tell the user what to install before continuing. Do not try to install Python or git for them.

## Step 2 — Install Cairn ★

> **Important UX note for you (the agent).** Your shell tool starts a fresh process for each command — `conda activate` or `source venv/bin/activate` in one tool call does NOT persist to the next. If you install into a conda env or venv, every subsequent `cairn` invocation will need either re-activation or an absolute path (`~/.venvs/cairn/bin/cairn …`), which is clunky for the user. **Prefer `pipx` unless the user has a strong reason otherwise** — it installs Cairn into its own isolated env and exposes the `cairn` entry point on the user's normal PATH, so subsequent commands Just Work without activation.

Offer the user these options, in this order:

1. **pipx** *(recommended).* One install, `cairn` on PATH everywhere afterward, no activation needed for any subsequent step.
2. **A user-supplied venv / conda / pixi / uv environment** they already have active. Works, but every subsequent `cairn` command in this session will need the env's full binary path (e.g., `~/.venvs/cairn/bin/cairn …`) because your shell tool resets between calls.
3. **`pip install --user`** as a fallback. Installs to `~/.local/bin/cairn` (assuming that's on PATH).

Install commands:

```sh
# Option 1 — pipx (recommended)
pipx install git+https://github.com/cranmer/cairn

# Option 2 — existing env (caller activates it themselves first)
pip install git+https://github.com/cranmer/cairn

# Option 3 — user-site
pip install --user git+https://github.com/cranmer/cairn
```

If `pipx` itself isn't installed, offer to install it for the user:

```sh
python -m pip install --user pipx && python -m pipx ensurepath
# user may need to restart their shell after ensurepath, or `source ~/.bashrc` / `~/.zshrc`
```

Verify the install worked:

```sh
which cairn      # capture this path — if `cairn` ever stops resolving later, use this absolute path
cairn --help     # should list init, collaborator, decision, action, branch, finding, validate, status, version
cairn version
```

If `cairn --help` doesn't work and the user picked option 2 (env-based install), use the full path (`<env>/bin/cairn`) for every subsequent step in this doc and tell the user explicitly: *"Your shell will need `conda activate cairn` (or equivalent) before `cairn` works in a new terminal."* If they want to avoid that, suggest reinstalling via pipx.

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

Echo both values back, then ask "shall I proceed?" before running:

```sh
cd <parent-directory>
cairn init <project-name> --no-input
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
- **Role** — what they actually *do* on this project. Bias toward activity-based descriptions ("designing generative models", "running ablation experiments", "maintaining the data pipeline", "writing the introduction"), not titles ("PI", "postdoc", "professor"). Cairn intentionally avoids prescribing a hierarchy; whatever description fits the user's actual contribution is right. If they offer a title, that's also fine — accept it.
- Optional: GitHub handle, expertise tags, current focus.

You can pre-fill the user's **email** from their git config (`git config --get user.email`) without asking — the email is what the `orient` skill uses to match the current git user against the collaborator list. Without it, every future session has to ask "which collaborator id is yours?" Confirm the email with the user before passing it, but defaulting from `git config` is fine.

When offering suggestions in any interactive prompt, suggest activity-based phrasings, not titles. Do not present role as a choice between fixed academic titles.

Then run:

```sh
cairn collaborator add \
  --id <chosen-id> \
  --name "<Their Full Name>" \
  --role "<role>" \
  --email <they@example.com> \
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

Tell the user that the cairn now includes seven bundled `SKILL.md` files under `skills/`, plus a top-level `TRACKING.md` guide.

> **What "ships seven skills" means today.** The SKILL.md files are *procedural prose* — what each skill is, when to trigger it, which `cairn` CLI command to run. They are **not** registered Claude Code skills: they won't appear in the user's `/skills` list and the Skill tool can't invoke them by name. You (the agent) read the relevant `SKILL.md` when its trigger fires and execute the steps manually. Cross-repo installation that makes them real `/orient`, `/log-finding`, etc. slash commands everywhere is on the roadmap (ADR-0006 Stage 3, `cairn skills install`) but not yet in v0. Until then, the procedures still work — you just invoke them yourself.

The procedures:

- **TRACKING.md** (at the cairn root) — the *posture* guide. Cairn's whole point is that the user shouldn't have to invoke CLI commands by hand; you (the agent) listen for capture-worthy signals in conversation and record them transparently. Read this once at session start.
- **orient** — what you should read at session start to be useful without burning context.
- **search-history** — local-file scan for "was X considered?" questions.
- **start-branch** — wraps `cairn branch start "<desc>"` for exploratory work.
- **resolve-branch** — wraps `cairn branch close <name>` when an exploration branch is merged or abandoned. Counterpart to `start-branch`.
- **complete-action** — wraps `cairn action complete <id>` when something gets done.
- **log-finding** — wraps `cairn finding add` when the user discovers something worth recording.
- **debrief** — at session-end signals ("let's wrap up", "good place to stop"), reviews the conversation and produces a single batched proposal of any captures that didn't happen live. One round of bulk confirmation rather than per-item interruptions.

Suggest two concrete next steps they might take in this session:

1. Edit `PROJECT.md` to fill in the project overview and current focus (the file ships with TODO markers).
2. Add a goal or two with `cairn decision add` / `cairn action add` so the cairn has real state to be useful against.

End with:

```sh
cairn status        # compact summary, <30 lines
cairn validate      # confirms schema + cross-references are clean
```

## Step 6.5 — Make this session live *inside* the cairn (env-based installs only) ★

Note on what already ships: every cairn scaffolded by `cairn init` comes with a `.claude/settings.json` that has a SessionStart hook running `cairn status`. That gives any Claude Code session opened in the cairn an immediate project-state context dump. The `.gitignore` already excludes `.claude/settings.local.json` (the per-user, per-machine file below). You do NOT need to create either of those files in the pipx case.

Skip the rest of this step if the user installed via **pipx** in Step 2 — `cairn` is on PATH everywhere, the bundled hook runs, and you're done; just `cd <project-path>` once.

For users who picked Option 2 (an existing venv / conda / pixi / uv env), `cairn` only resolves when that env is activated, and your Bash tool resets shell state between calls. The fix is to write a `.claude/settings.local.json` file at the cairn root that prepends the env's `bin/` to `PATH`. Claude Code reads this file alongside `.claude/settings.json` and merges them.

1. `cd <project-path>` (one time — the working directory will persist).
2. Capture the env's `bin/` directory. If you remember the path from Step 2, use it directly. Otherwise: `which cairn` (after activating the env once, e.g., `conda activate cairn`) returns `<env>/bin/cairn`; the relevant directory is the parent.
3. Write `.claude/settings.local.json` inside the cairn:

   ```json
   {
     "env": {
       "PATH": "/absolute/path/to/env/bin:$PATH"
     }
   }
   ```

4. No `.gitignore` edit needed — the bundled template already excludes `.claude/settings.local.json`. Confirm with `git status` that the new file does not appear.

5. Verify in a fresh Bash call (no env activation) that `cairn --help` now resolves.

Tell the user: *"Future Claude Code sessions opened in this cairn will auto-orient via the bundled SessionStart hook, and `cairn` will resolve without activation. You're set."*

## What to do if anything fails

- **`cairn` command not found after install**: the install env's `bin/` isn't on PATH. Tell the user; offer to use the absolute path (`~/.venvs/cairn/bin/cairn …`) for the rest of the session, OR write `.claude/settings.local.json` as in Step 6.5.
- **`cairn init` errors with "no git user identity configured"**: go back to Step 3 and set it; do not invent.
- **`cairn init` errors with "refusing to overwrite"**: a directory with that name already exists. Ask the user whether to pick a new name or pass `--force` (which deletes the existing directory; warn first).
- **Any schema or YAML error**: stop, show the user the exact error, and ask how to proceed. Do not edit state files by hand to "fix" them without confirmation.
- **`pipx upgrade cairn` did nothing on an old install**: expected if the installed version is the pre–hatch-vcs static `0.1.0`. Run `pipx install --force git+https://github.com/cranmer/cairn` once to land on the dynamic-versioning era; after that, `pipx upgrade` works normally. See the "Upgrading Cairn later" section below.

## What you should *not* do

- Do not commit on the user's behalf without showing them the proposed commit message first (after this bootstrap is complete; during bootstrap, the `cairn` CLI handles attribution).
- Do not install global pip packages without confirming the environment in Step 2.
- Do not run `git config --global` to change values the user already has set.
- Do not create more than one cairn in this session. One project = one cairn.

## When you're done

Report **honestly** about what just happened. Two facts to convey:

1. **Where the cairn lives** — its absolute path; it's a sibling of any existing project repos, not nested inside them.
2. **What mode this session is in** — and the key word is *honestly*. Mode is determined by where the user *opened Claude Code*, not where you are now after `cd`ing during bootstrap:
   - If the user's *initial* cwd was inside the cairn directory, this is **Mode A**: the cairn's SessionStart hook fired and `cairn status` ran automatically.
   - If the user's *initial* cwd was anywhere else (typically their project's code repo), this is **Mode B**: the hook did not fire. You can still run cairn commands by `cd`-ing or by using full paths, and you can read the SKILL.md procedures on demand — but don't claim this is Mode A. It isn't.

   In either case, the SKILL.md files are *procedural prose* (see Step 6's note), not registered Claude Code skills. Don't tell the user the skills are "loaded" or "available" as if they were slash commands.

A reasonable closing message:

> Your cairn `<name>` is live at `<absolute-path>`. This session was opened in `<initial-cwd>`, so it's **<Mode A or Mode B>**. <If Mode B: I can still capture findings, decisions, and actions to the cairn during our conversation — I'll run the CLI commands from there for you. The SessionStart auto-orient only fires when you open Claude Code from inside the cairn directory.> The cairn's SKILL.md procedures (orient, log-finding, debrief, etc.) are prose I'll read on demand when their triggers fire; once a future `cairn skills install` ships (ADR-0006 Stage 3) they'll be registered as real `/orient`, `/log-finding`, etc. slash commands. For ongoing project work today: continue here, or open a fresh session wherever feels natural — just describe what you want to do next, and I'll pick the right procedure.

Then stop. The user will direct the next step.

## Upgrading Cairn later

Cairn is pre-1.0 and changes land directly on `main`. The package version is now derived from git via `hatch-vcs` — every commit produces a unique version like `0.1.0.dev28+g0b9c97f`, so `pipx upgrade cairn` (and `pip install --upgrade`) correctly detect new commits rather than short-circuiting on matching static metadata.

To pick up the latest:

```sh
# pipx (recommended install path)
pipx upgrade cairn                                              # if Cairn was installed via pipx
pipx install --force git+https://github.com/cranmer/cairn       # equivalent; works even when upgrade can't

# pip in a venv / conda env
pip install --upgrade git+https://github.com/cranmer/cairn
```

If you (or the user) hit a Cairn install from before this commit where the version was the static `0.1.0`, `pipx upgrade` will no-op — fall back to `pipx install --force ...` once, and `pipx upgrade` will work from then on.

After upgrading, **existing cairns are not automatically updated.** They already shipped with whatever template / skills / `.claude/settings.json` were current at `cairn init` time, and Cairn doesn't yet have a `cairn upgrade <project>` migration command. If a meaningful template change shipped, surface that to the user and either (a) re-init into a new directory and have the user copy state over, or (b) cherry-pick specific files from the new template's location (see `python -c "import importlib.resources; print(importlib.resources.files('cairn').joinpath('templates','default'))"`). Don't auto-overwrite without asking — the user may have hand-edited PROJECT.md, etc.
