# Quickstart — with a group cairn server

A five-minute path from a clean machine to a working setup that connects to a cairn already running on a shared HTTP server. The cairn exists, has state, and the team is already writing to it. You're hooking your local machine to it — not creating anything new.

This guide assumes the **group-server** setup: a teammate has already set up the cairn MCP server somewhere reachable over HTTP and given you an endpoint URL plus a bearer token. If no group server exists yet — you're getting started with cairn for the first time on your own machine — you want [`QUICKSTART-standalone.md`](QUICKSTART-standalone.md) instead. If you're the one *running* the group server, see [`docs/group-deployment.md`](docs/group-deployment.md).

**Want your agent to do this for you?** See [`AGENT-BOOTSTRAP.md`](AGENT-BOOTSTRAP.md). Paste that file into a fresh Claude Code session and the agent will install Cairn, set up your credentials, and pair your project repo with the remote cairn — pausing for your confirmation at each major step. The agent doc handles both the standalone path and the group-server path (here); it asks at the start which one applies.

## What you need from your team

Before you start, get four facts from whoever runs the cairn:

- **Endpoint URL** — e.g., `https://cairn.lab.example.org/mcp`
- **Cairn handle** — short name (e.g., `coral-bleach`) identifying which cairn on the server you're joining
- **Bearer token** — credentials for connecting to the HTTP server
- **Your collaborator id** — the id under which the team has registered you in the cairn. The same id goes on every write you make. *Ask them to confirm you've been added before starting* — adding collaborators is a server-side operation, not something you can do from here.

## Step 1 — Install cairn ★

Requires **Python ≥ 3.10** and `git` on PATH. **pipx** keeps `cairn` on PATH everywhere with no env-activation friction.

```sh
# If pipx isn't already installed:
python -m pip install --user pipx && python -m pipx ensurepath

# Install:
pipx install 'cairn[mcp] @ git+https://github.com/cranmer/cairn'

# Verify:
cairn --help
cairn version
```

(Cairn is not on PyPI; `pip install cairn` would pull an unrelated package. Always install from the git URL.)

## Step 2 — Configure git identity ★

```sh
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"
```

Use the email associated with your collaborator id in the cairn — the `orient` skill matches the two so future sessions can auto-detect you.

## Step 3 — Store your bearer token ★

Persist it in your credentials file rather than passing it on the command line (where it would appear in shell history):

```sh
mkdir -p ~/.config/cairn
cat > ~/.config/cairn/credentials.toml <<'EOF'
[endpoints."https://cairn.lab.example.org/mcp"]
token = "<token-from-your-team>"
EOF
chmod 600 ~/.config/cairn/credentials.toml
```

The CLI checks `CAIRN_BEARER_TOKEN` first if it's set, then this file (keyed by endpoint URL).

## Step 4 — Pair your project repo with the cairn

In your local working copy of the project repo:

```sh
cd ~/projects/myproject
cairn link --endpoint https://cairn.lab.example.org/mcp --name coral-bleach
```

This writes a `cairn.toml` at the project repo root recording the endpoint and the cairn handle. A connectivity probe runs first; if the server's unreachable or your token is wrong, the command tells you before writing the pointer.

The `cairn.toml` file is safe to commit — credentials live separately in `~/.config/cairn/credentials.toml` and never appear in git.

## Step 5 — Smoke test with a real write

From the paired project repo:

```sh
cairn finding add --author <your-id> \
  --title "Joining the cairn" \
  --body "Smoke test from a new client to confirm the wire works."
```

The CLI prints the resulting file path and the cairn name the server resolved your write to — confirming it landed in the right place. The write is real: it shows up for everyone else on the team. (Server admins can clean it up later if you want; from here you can't delete it.)

If you get `error: HTTP 401 ...`, your token is wrong or expired. If you get `error: unknown author '<your-id>' in this cairn`, the team hasn't added you as a collaborator yet — ask them to.

## Step 6 — Register the remote cairn with Claude Code (one-time, ever) ★

So your Claude Code sessions can reach the cairn's MCP tools directly:

```sh
claude mcp add --scope user --transport http cairn-remote https://cairn.lab.example.org/mcp
```

(Exact flag for HTTP transport depends on your Claude Code version; check `claude mcp add --help` if the above isn't recognized.)

Confirm:

```sh
claude mcp list           # should show `cairn-remote`
```

**Restart any open Claude Code sessions** to pick up the new MCP server.

## Step 7 — Verify

Open Claude Code in your project repo and ask:

> *"What cairn tools do you have?"*

The agent should list them. Then:

> *"What's the project status?"*

The agent calls the cairn's `status` MCP tool against the remote server. You'll see counts of decisions, findings, open questions, recent activity — everything the team has been logging.

## What you have now

- A pairing file at `~/projects/myproject/cairn.toml` pointing at the group's cairn over HTTP.
- Your bearer token at `~/.config/cairn/credentials.toml` (mode 0600, not committed).
- The remote cairn registered with your Claude Code — every session opened in any cairn-paired project repo can read and write the shared cairn through MCP tools.

Anything you log is visible immediately to the other collaborators in their own sessions, attributed to you. No restart, no sync, no merge.

## What you should not do

- Do not run `cairn init` or `cairn register --init` — the cairn exists already; creating a new local one would only confuse things.
- Do not run `cairn collaborator add` — adding collaborators is a server-side operation. Ask whoever runs the cairn.
- Do not commit your bearer token into git.
- Do not start your own `cairn mcp` HTTP server unless you're hosting the group cairn yourself; in that case see `docs/group-deployment.md`.

## Upgrading later

To pick up the latest cairn CLI:

```sh
pipx install --force 'cairn[mcp] @ git+https://github.com/cranmer/cairn'
```

Bundled skills live in the cairn on the server, not on your machine — they get updated by whoever runs the server, not from here.

## Where to go next

- `docs/scenario-many-users-one-cairn.html` — narrative walkthrough of what a shared cairn looks like across a working week with three collaborators.
- `docs/group-deployment.md` — for the person who runs the server.
- `QUICKSTART.md` — single-user standalone setup, for a personal cairn on your own machine.
