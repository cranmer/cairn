# Remote MCP server

How to run `cairn mcp` over HTTP — instead of the default per-session stdio
transport — and how to pair clients with it.

The HTTP transport is what makes one MCP server reachable from multiple
machines: a group box that every collaborator's Claude Code talks to, a
long-running per-machine server independent of any interactive client, or a
Phase-5 background agent calling a stable endpoint.

If you're running cairn for yourself on one laptop, **stay on stdio** — that's
what [`QUICKSTART.md`](../QUICKSTART.md) wires up, and the trust surface is
just the process boundary. Switch to HTTP only when you actually need
remote access.

The design rationale lives in [ADR-0012](decisions/0012-mcp-http-transport.md);
this document is the operator + client guide.

---

## At a glance

| You want to … | Use |
|---|---|
| Local single-user MCP (everyday case) | `cairn mcp` (stdio) — see QUICKSTART |
| Long-running HTTP server on one host | `cairn mcp --transport streamable-http` |
| Same, in a container | the bundled `src/cairn/mcp/Dockerfile` |
| Throwaway HTTP server for tests / fixtures | `cairn dev serve` (not for production) |
| Pair a project repo with a remote cairn | `cairn link --endpoint <url> --name <handle>` |

---

## Server side

### Direct invocation

`cairn mcp` takes a `--transport` flag. The full HTTP surface:

```sh
cairn mcp \
  --transport streamable-http \
  --host 127.0.0.1 \           # default; bind 0.0.0.0 for remote access
  --port 8765 \                # default
  --path /mcp \                # default — the URL the client POSTs to
  --allowed-host cairn.example.com   # repeatable; see "DNS-rebinding" below
```

Defaults bind to `127.0.0.1:8765/mcp`, which keeps the trust surface identical
to stdio (single-user, loopback only). Switching the bind host to `0.0.0.0`
**expands the trust surface** — every tool call against the bound port is
honored. Don't do that without an auth layer in front (see
[Reverse proxy + TLS + auth](#reverse-proxy--tls--auth)).

`--transport sse` is also supported for older MCP clients; the rest of this
guide assumes `streamable-http` since that's what current Claude Code and the
`cairn` CLI's remote-write path speak.

### DNS-rebinding protection and `--allowed-host`

The MCP SDK rejects requests whose `Host:` header isn't on a small allowlist
(`localhost`, `127.0.0.1`, …) as a DNS-rebinding mitigation. The moment you
put the server behind a reverse proxy that forwards requests under a public
hostname — `cairn.example.com`, `mcp.lab.internal`, anything that isn't
`localhost` — the SDK will 4xx those requests.

Add the public hostname(s) with `--allowed-host` (repeatable):

```sh
cairn mcp --transport streamable-http --host 0.0.0.0 \
          --allowed-host cairn.example.com
```

If you skip this and see "Invalid host" 4xx responses with the server
otherwise healthy, this is the cause.

### Docker

A multi-stage Dockerfile ships at
[`src/cairn/mcp/Dockerfile`](../src/cairn/mcp/Dockerfile). It builds a slim
runtime with `cairn[mcp]` installed and runs as a non-root `cairn` user, with
the streamable-HTTP server bound on `0.0.0.0:8765/mcp`:

```sh
# Build (from the repo root):
docker build -f src/cairn/mcp/Dockerfile -t cairn-mcp:latest .

# Run, mounting one or more cairns in and pointing the registry at them:
docker run --rm -it \
  -p 8765:8765 \
  -v "$HOME/projects/myproject-cairn:/home/cairn/cairns/myproject:rw" \
  -v "$HOME/.config/cairn:/home/cairn/.config/cairn:rw" \
  cairn-mcp:latest
```

Two things to wire up inside the container before the server is useful:

1. **The registry.** Either bind-mount your existing
   `~/.config/cairn/server.toml` (as above), or write a fresh
   `server.toml` inside the container listing the cairns you mounted.
   `cairn register <name> <path>` works inside an exec shell.
2. **Git identity** for any cairn the server writes into — `cairn` refuses
   to commit otherwise. Mount your `~/.gitconfig` in, or run
   `git config --global user.{name,email}` as the `cairn` user.

For a quick smoke test you can also pass `--cairn-path` to register an ad-hoc
cairn at startup without touching the registry file:

```sh
docker run --rm -it -p 8765:8765 \
  -v "$HOME/projects/myproject-cairn:/mnt/cairn:rw" \
  cairn-mcp:latest \
  cairn mcp --transport streamable-http \
            --host 0.0.0.0 --port 8765 \
            --cairn-path /mnt/cairn
```

### Reverse proxy + TLS + auth

The server has **no built-in TLS and no built-in authentication** — this is
intentional per [ADR-0012](decisions/0012-mcp-http-transport.md#decision):
operators front it with a reverse proxy that handles both. The client side
does send `Authorization: Bearer <token>` (see
[Credentials](#credentials)); the proxy is responsible for validating it.

#### Caddy (simplest)

```caddy
cairn.example.com {
    # Caddy gets a real cert from Let's Encrypt automatically.

    # Bearer-token check. Keep the secret out of the Caddyfile via env.
    @authorized header Authorization "Bearer {env.CAIRN_TOKEN}"
    handle @authorized {
        reverse_proxy 127.0.0.1:8765
    }
    respond 401
}
```

#### nginx

```nginx
server {
    listen 443 ssl http2;
    server_name cairn.example.com;

    ssl_certificate     /etc/letsencrypt/live/cairn.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/cairn.example.com/privkey.pem;

    location /mcp {
        # Validate the bearer token (cleartext compare against an env-injected secret).
        if ($http_authorization != "Bearer ${CAIRN_TOKEN}") {
            return 401;
        }

        proxy_pass http://127.0.0.1:8765;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header Connection "";

        # MCP streamable-HTTP can use SSE for responses — disable buffering.
        proxy_buffering off;
        proxy_read_timeout 1h;
    }
}
```

Either way, run the cairn server bound to loopback only and let the proxy
own the public surface:

```sh
cairn mcp --transport streamable-http \
          --host 127.0.0.1 --port 8765 \
          --allowed-host cairn.example.com
```

For stronger auth (OIDC, mTLS, SSO) put the standard plugin for your proxy
in the same spot the bearer check sits above. The cairn server doesn't care
how the token gets validated, only that the proxy lets the request through.

### Production vs. `cairn dev serve`

`cairn dev serve` is **dev scaffolding for the multi-user/multi-cairn test
methodology** ([ADR-0014](decisions/0014-cairn-dev-subgroup-and-server-lifecycle.md)),
not a deployment mode. It picks a free port, writes a state file to
`$XDG_CACHE_HOME/cairn`, and exposes a `scaffold_fixture` dev tool that
real deployments must not enable. Use it for tests; use the direct
invocation above (or Docker) for anything you want to keep running.

---

## Client side

### Pairing a project repo with a remote cairn

`cairn link --endpoint <url> --name <handle>` is the remote analogue of the
local-mode `cairn link --name <handle>` from QUICKSTART:

```sh
cd ~/projects/myproject                   # your code repo
cairn link --endpoint https://cairn.example.com/mcp --name myproject
```

This writes a remote-mode `cairn.toml` at the project repo root containing
just the endpoint + handle. Credentials are *not* written into `cairn.toml`,
so the pointer is safe to commit. A connectivity probe runs first; pass
`--no-probe` if you're pairing offline.

After this, the four write commands — `cairn decision add`, `cairn finding
add`, `cairn action add`, `cairn action complete` — transparently dispatch
over HTTP from inside the project repo, each printing the server's resolved
cairn name and new entity ID so you can confirm the write landed in the
right cairn.

**Reads are deferred.** `cairn status`, `cairn validate`, and
`cairn agenda draft` still error in remote mode; for now, agents handle
reads through their MCP client (see next section). The read-side CLI story
is filed as US-P-14.

### Credentials

The CLI looks up a bearer token in this order:

1. The `CAIRN_BEARER_TOKEN` environment variable.
2. `~/.config/cairn/credentials.toml`, keyed by endpoint URL:

   ```toml
   [endpoints."https://cairn.example.com/mcp"]
   token = "your-bearer-token"
   ```

   The file is created mode `0600` if `cairn` writes it.

Either form works for any number of endpoints. Pick whichever fits your
secret-management story — env var for ephemeral shells, the file for
persistent setups.

### Wiring the remote into Claude Code

Two patterns, depending on whether the remote is always-on:

```sh
# Always-on remote server — point Claude Code directly at the URL:
claude mcp add cairn-remote https://cairn.example.com/mcp

# Otherwise, let Claude Code spawn a local `cairn mcp` client subprocess
# that talks to the remote (useful when you want to multiplex local +
# remote cairns through one MCP entry):
claude mcp add cairn-remote -- cairn mcp --transport streamable-http
```

Restart any open Claude Code sessions to pick up the new entry. The agent
then has the full ~28-tool surface against the remote cairn(s), and reads
land via MCP rather than via the CLI.

---

## What works remote, what doesn't

| Surface | Remote mode |
|---|---|
| All MCP tools (reads + writes), called by an agent | ✅ |
| `cairn decision add` / `finding add` / `action add` / `action complete` | ✅ (HTTP dispatch, prints server-resolved ID) |
| `cairn status`, `cairn validate`, `cairn agenda draft` | ❌ errors today (US-P-14) |
| Built-in TLS / OAuth in `cairn mcp` itself | ❌ — use a reverse proxy |
| Binding the bearer-token holder to `author` attribution | ❌ — attribution is by `author` arg, follow-up ADR |

Two consequences of that last row worth being explicit about:

- **Attribution is not authentication.** A write claiming `author = "kyle"`
  is recorded as kyle if that id is in `state/collaborators.yaml`, regardless
  of whose token signed the request. The proxy decides who gets through;
  `collaborators.yaml` decides what id their write lands under.
- **Token-to-id binding is future work** ([ADR-0012 §Attribution vs
  authentication](decisions/0012-mcp-http-transport.md#attribution-vs-authentication)).
  Until that ADR lands, don't treat remote-MCP attribution as cryptographically
  enforced — treat it as best-effort identity that the reverse proxy gates
  network access to.

---

## Troubleshooting

**`HTTP 400 Invalid host`** — you fronted the server with a reverse proxy on
a public hostname but didn't pass `--allowed-host`. Add the hostname (see
[DNS-rebinding](#dns-rebinding-protection-and---allowed-host)).

**`HTTP 401/403` from the CLI** — credentials aren't being sent or aren't
being accepted. Check `echo $CAIRN_BEARER_TOKEN` and that
`~/.config/cairn/credentials.toml` uses the *exact* endpoint URL (trailing
slash matters). On the proxy, log the `Authorization` header to confirm
what's arriving.

**`could not reach …`** — network error before the server responded.
`cairn link` runs this probe at pair time; pass `--no-probe` to skip the
check if you know the endpoint is correct but currently unreachable.

**Writes succeed but land in the wrong cairn** — the server echoes the
resolved cairn name on every write (e.g., `"Recorded D-001 in cairn
'other-name' at …"`). If that doesn't match the `name` in your
`cairn.toml`, your local pointer is wrong; re-run `cairn link --endpoint
… --name <correct-handle> --force`.

---

## Related ADRs

- [ADR-0009](decisions/0009-mcp-server-design.md) — original MCP server design (stdio).
- [ADR-0010](decisions/0010-single-mcp-server-multiple-cairns.md) — one server, many cairns.
- [ADR-0012](decisions/0012-mcp-http-transport.md) — HTTP transport + remote dispatch (this doc's spec).
- [ADR-0014](decisions/0014-cairn-dev-subgroup-and-server-lifecycle.md) — `cairn dev serve` lifecycle (tests, not production).
