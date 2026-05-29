# Group deployment — running a shared cairn

This document is for whoever is setting up and operating a cairn that several collaborators reach over HTTP. It is an operations doc — assumptions about hosting, networking, supervision, credentials, and admin tasks — not a per-user setup guide.

If you're a *user* joining a group cairn that someone else has set up, see [`QUICKSTART-with-server.md`](../QUICKSTART-with-server.md) instead.

If you're setting up cairn for personal use only, see [`QUICKSTART-standalone.md`](../QUICKSTART-standalone.md).

## What "group deployment" means here

A long-lived `cairn mcp --transport streamable-http` process serves one or more cairns from a host that everyone in the group can reach. Each collaborator pairs their local project repo with the server's endpoint via `cairn link --endpoint <url> --name <handle>`, and from then on their CLI and Claude Code sessions write to the shared cairn over HTTP.

What this gets you:

- One cairn that several people on different machines write to in parallel.
- Attribution per write — every entity carries the writing collaborator's `author` field.
- Server-side serialization of id allocation (no duplicate `D-NNN` even under concurrent writes).
- Cross-references that resolve immediately (Sam can `--related D-004` against a decision Alex wrote a minute ago).

What it doesn't get you (yet):

- Bound authentication: today the bearer token authorizes the connection, but the `author` parameter is what claims the identity. The two aren't cryptographically tied. A user with a valid token can write under any registered collaborator's id. This is the "attribution, not authentication" posture; it's fine for trusted research groups and inappropriate for hostile environments.
- Multi-region / failover: there's one server, one disk. Back the disk up.

For the conceptual story of what a shared cairn looks like in use, see [`scenario-many-users-one-cairn.html`](scenario-many-users-one-cairn.html).

## Pre-flight choices

Before installing anything, decide:

1. **Where the server runs.** A dedicated VM, a lab workstation that's always on, a Kubernetes deployment, a container on a group machine — any of these work. The host needs to be reachable from every collaborator's laptop (over VPN, over the open internet behind a reverse proxy, etc.). The server itself binds to `127.0.0.1` by default; you reach the wider network via a reverse proxy or by deliberately binding `0.0.0.0`.

2. **Where the cairn's git repo lives on disk.** This is the substrate — everything the server reads and writes goes here. Pick a path with regular backups. The cairn is just a git repository; standard git workflows (mirror to a private remote, periodic `git push` to off-host backup, snapshot the disk) all apply.

3. **How collaborators authenticate.** Today, a shared bearer token per cairn (or per group) is the simplest setup. For tighter control, front the server with a reverse proxy that does TLS termination, OIDC, and access logging — the MCP server itself doesn't enforce auth beyond the bearer token, but a proxy can.

4. **How the process is supervised.** A bare `nohup cairn mcp ... &` is fragile — long-running servers can get reclaimed by container governance, OOM killers, log rotation, or any number of housekeeping processes. Use a real supervisor (`systemd` on a Linux host, `supervisord` for containers, a `Deployment` for k8s) so the process restarts cleanly on failure or reboot.

## Step 1 — Install cairn on the server host

Same install as everywhere else:

```sh
pipx install 'cairn[mcp] @ git+https://github.com/cranmer/cairn'
cairn --help
cairn version
```

Make sure pipx put `cairn` somewhere stable (`/usr/local/bin/cairn` or the supervisor user's `~/.local/bin/cairn`) — the supervisor unit file will reference this absolute path.

## Step 2 — Scaffold and register the cairn

```sh
# Pick a path with backups; the cairn's git repo lives here.
cd /var/lib/cairn               # or wherever
cairn register shared-physics-paper ./shared-physics-paper-cairn --init
```

This creates the cairn directory and registers it in the user-level registry (`~/.config/cairn/server.toml` for the user running the server). If you want multiple cairns served by one process, repeat `cairn register <handle> <path> --init` for each — the MCP server picks them all up.

Add a real first commit's worth of metadata before turning the server on (PROJECT.md content, the initial collaborator list — see Step 3 below).

## Step 3 — Add collaborators

Every person who'll write to the cairn needs to be registered in `state/collaborators.yaml` before their first write. Adding collaborators is a **server-side** operation; users joining can't add themselves.

```sh
cd /var/lib/cairn/shared-physics-paper-cairn
cairn collaborator add \
  --id alex \
  --name "Alex Chen" \
  --role "methods lead" \
  --email alex@example.com \
  --github alexchen
```

Repeat for each collaborator. The id is what they'll pass as `--author` on every write — coordinate with them on the choice before adding (it's typically their first name kebab-cased: `alex`, `morgan`, `maria-s`).

For ambiguous-authorship entries that no single human wrote (decisions inferred from git history during a `bootstrap_from_repo` run, for example), add a placeholder collaborator with `type: unknown`:

```sh
cairn collaborator add --id repo-history --name "Repository history" --role "implicit" --type unknown
```

## Step 4 — Generate and distribute bearer tokens

The server doesn't generate tokens for you — pick any reasonably long random string. A typical pattern:

```sh
# Generate a token (any high-entropy string works):
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Distribute the token to your collaborators via whatever secure channel you already use (signal, in-person, your team's secrets manager). They put it in `~/.config/cairn/credentials.toml` at mode 0600 on their own machines — `QUICKSTART-with-server.md` walks them through that step.

The server side of credentials today is minimal: the bearer token authorizes the connection, but the `author` claim on each write is what carries the attribution. If you need stronger guarantees, front the server with a reverse proxy that does OIDC and access logging.

## Step 5 — Run the server under supervision

The MCP server starts with:

```sh
cairn mcp --transport streamable-http --host 127.0.0.1 --port 8765
```

For production deployment, wrap this in a supervisor. A minimal `systemd` unit:

```ini
# /etc/systemd/system/cairn-mcp.service
[Unit]
Description=Cairn MCP HTTP server
After=network.target

[Service]
Type=simple
User=cairn
Group=cairn
Environment=XDG_CONFIG_HOME=/var/lib/cairn/config
ExecStart=/usr/local/bin/cairn mcp --transport streamable-http --host 127.0.0.1 --port 8765
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```sh
systemctl daemon-reload
systemctl enable --now cairn-mcp
journalctl -u cairn-mcp -f
```

The `XDG_CONFIG_HOME` env var tells the server where to find the registry — point it at a path you control rather than the supervisor user's home dir.

Default binding is `127.0.0.1` (safe for single-host development). To reach the server from other machines, either bind `0.0.0.0` directly (only if you trust the network) or front it with a reverse proxy that terminates TLS and forwards to `127.0.0.1:8765`.

## Step 6 — Front the server (recommended for any real deployment)

A reverse proxy in front of the MCP server gives you TLS, access logging, and a place to add auth that the MCP server itself doesn't enforce. An nginx site config might look like:

```nginx
server {
    listen 443 ssl http2;
    server_name cairn.lab.example.org;

    ssl_certificate     /etc/letsencrypt/live/cairn.lab.example.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/cairn.lab.example.org/privkey.pem;

    location /mcp {
        proxy_pass         http://127.0.0.1:8765/mcp;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;

        # streamable-http needs long-lived connections and bidirectional buffering:
        proxy_buffering    off;
        proxy_read_timeout 1h;
    }
}
```

Adjust to taste. The MCP server's streamable-HTTP transport requires `proxy_buffering off` and a generous read timeout — short timeouts will break in-flight tool calls.

The collaborators' endpoint URL is then `https://cairn.lab.example.org/mcp`.

## Step 7 — Onboarding a new collaborator

When a new person joins the project:

1. Pick their collaborator id (kebab-case, lowercase, stable).
2. On the server, run `cairn collaborator add --id <id> --name "..." --role "..." --email <...>` against the appropriate cairn.
3. Distribute the bearer token to them via whatever secure channel you use.
4. Send them four facts: endpoint URL, cairn handle, bearer token, their collaborator id.
5. Point them at [`QUICKSTART-with-server.md`](../QUICKSTART-with-server.md) — that walks them through the client-side setup.

If their first write returns `unknown author '<id>'`, you forgot Step 2.

## Upgrading

The server, like any other cairn install, picks up updates via:

```sh
pipx install --force 'cairn[mcp] @ git+https://github.com/cranmer/cairn'
```

After the install completes, `systemctl restart cairn-mcp` (or whatever supervisor equivalent) to get the new code running.

Bundled skills (the `SKILL.md` files in `<cairn>/skills/`) can drift between cairn versions. To pull newly-bundled skills into your existing cairns after upgrading:

```sh
cd /var/lib/cairn/<cairn-name>
cairn skills sync     # non-destructive; only copies skills you don't have
```

Run this once per cairn after each cairn upgrade. Users connecting via HTTP don't need to do anything — they read skills through the MCP server's `get_skill` tool, which reads them from the server's disk.

## Backups and recovery

The cairn is a git repository. The standard practices apply:

- **Mirror to a private remote.** A bare `git push --mirror` to a private GitHub or self-hosted repo at the end of each day is a low-effort backup.
- **Snapshot the disk.** If the cairn lives on a managed volume (cloud disk, ZFS dataset), regular snapshots are enough.
- **The state files are plain YAML.** In a real disaster, you can hand-edit them; pair with `cairn validate` to catch schema breakage before users hit it.

What lives outside git and needs separate backup:
- The MCP registry (`server.toml`) at `XDG_CONFIG_HOME/cairn/server.toml` on the server host.
- Bearer tokens (in your secrets manager, not here).
- Any TLS certificates / private keys.

## What this doc deliberately doesn't cover

- **Distributing the server across multiple machines.** The current shape is one process, one disk. Replication / failover is a future deployment story.
- **Mid-session token rotation.** You can rotate tokens by distributing the new one and updating each collaborator's `credentials.toml`; the server doesn't track per-token sessions, so the changeover is immediate but coordinated.
- **Auditing who wrote what.** Git authorship on the cairn's commits is the audit trail today. If you need finer-grained access logs, your reverse proxy is the right place.
- **Quotas / rate limits.** Not enforced at the application layer; if you need them, do it at the proxy.

## See also

- [`QUICKSTART-with-server.md`](../QUICKSTART-with-server.md) — what to hand to each collaborator joining the server.
- [`scenario-many-users-one-cairn.html`](scenario-many-users-one-cairn.html) — narrative walkthrough of the shape this deployment serves.
- [`decisions/0012-mcp-http-transport.md`](decisions/0012-mcp-http-transport.md) — the design decision that introduced HTTP transport, with the design constraints in detail.
