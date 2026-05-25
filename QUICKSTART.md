# Quickstart

Cairn supports two setup paths. Pick the one that matches your situation:

- **[QUICKSTART-standalone.md](QUICKSTART-standalone.md)** — Set up cairn on your own machine for a personal project. The cairn lives in a local git repo; your Claude Code sessions reach it over a local stdio MCP connection. Choose this if you're getting started with cairn for the first time and don't already have a group cairn server set up.

- **[QUICKSTART-with-server.md](QUICKSTART-with-server.md)** — Connect to a cairn that's already running on a shared HTTP server (typically a group machine for a multi-author project). The cairn exists, the team is already writing to it, and you're hooking your local machine to it. Choose this if someone on your team has already set up the server and given you an endpoint URL and credentials.

You can use both at once — cairn supports a personal local cairn for your own projects alongside a remote group cairn for shared work. Each is set up independently.

**Want your agent to walk you through either setup?** Paste [`AGENT-BOOTSTRAP.md`](AGENT-BOOTSTRAP.md) into a fresh Claude Code session. It handles both paths and asks at the start which one applies.

**Setting up the group server itself?** That's a separate operational concern — see [`docs/group-deployment.md`](docs/group-deployment.md).
