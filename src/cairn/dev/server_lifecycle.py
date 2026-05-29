"""Lifecycle for background `cairn mcp` HTTP servers used by tests.

Each server runs as a detached subprocess (its own session). State is
persisted as one JSON file per server under
``$XDG_CACHE_HOME/cairn/dev-servers/<pid>.json`` (default
``~/.cache/cairn/dev-servers/``) so ``cairn dev stop --all`` can clean
up without needing the original ``serve`` invocation.
"""

from __future__ import annotations

import contextlib
import json
import os
import signal
import socket
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class ServerInfo:
    pid: int
    host: str
    port: int
    path: str
    url: str
    cairn_path: str | None
    log_path: str
    started_at: float
    sandbox_path: str | None = None
    registry_path: str | None = None


def _state_dir() -> Path:
    cache_root = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    d = Path(cache_root) / "cairn" / "dev-servers"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _pick_free_port(host: str = "127.0.0.1") -> int:
    """Bind-port-0 trick: kernel picks a free port; we close and reuse it."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, 0))
        return sock.getsockname()[1]
    finally:
        sock.close()


def _wait_for_port(host: str, port: int, timeout_s: float = 10.0) -> None:
    """Poll TCP connect until success or timeout."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.2)
        try:
            sock.connect((host, port))
            return
        except OSError:
            time.sleep(0.1)
        finally:
            sock.close()
    raise TimeoutError(f"server on {host}:{port} did not accept connections within {timeout_s}s")


def _process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    # A zombie still answers signal 0 with success but is effectively dead.
    # Treat it as not-alive so callers (and tests) see a coherent state.
    try:
        with open(f"/proc/{pid}/status") as fh:
            for line in fh:
                if line.startswith("State:"):
                    return "Z" not in line.split(maxsplit=2)[1]
    except FileNotFoundError:
        return False
    return True


def _reap_if_child(pid: int) -> None:
    """Reap a child PID if we happen to be its parent. No-op otherwise."""
    with contextlib.suppress(ChildProcessError):
        os.waitpid(pid, os.WNOHANG)


def serve(
    *,
    cairn_path: Path | None = None,
    host: str = "127.0.0.1",
    port: int | None = None,
    path: str = "/mcp",
) -> ServerInfo:
    """Start ``cairn mcp --transport streamable-http`` as a detached subprocess.

    Returns a :class:`ServerInfo` describing the running server. Writes
    ``{state_dir}/{pid}.json`` so ``stop()`` and ``list_servers()`` can find it.

    Dev servers always run with ``--allow-dev-tools`` and a sandboxed
    per-process registry under ``$XDG_CACHE_HOME/cairn/dev-servers/<pid>/``
    (see ADR-0013).
    """
    if port is None:
        port = _pick_free_port(host)

    state_dir = _state_dir()
    log_dir = state_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{int(time.time())}-{port}.log"

    # Per-server sandbox + registry. Created here; cleaned by stop().
    # We use the port as a stable handle since the PID isn't known until
    # after Popen; the directory is renamed at the end if a PID-based
    # name is more useful (no — we just keep port-based naming).
    sandbox_root = state_dir / f"sandbox-{port}"
    sandbox_dir = sandbox_root / "cairns"
    sandbox_dir.mkdir(parents=True, exist_ok=True)
    registry_file = sandbox_root / "registry.toml"

    cmd = [
        sys.executable,
        "-m",
        "cairn",
        "mcp",
        "--transport",
        "streamable-http",
        "--host",
        host,
        "--port",
        str(port),
        "--path",
        path,
        "--registry-path",
        str(registry_file),
        "--allow-dev-tools",
        "--sandbox-path",
        str(sandbox_dir),
    ]
    if cairn_path is not None:
        cmd.extend(["--cairn-path", str(cairn_path)])

    # The child needs its own copy of the log fd; we close ours so we
    # don't keep the file open after Popen returns.
    with open(log_path, "wb") as log_fh:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    try:
        _wait_for_port(host, port)
    except TimeoutError:
        with contextlib.suppress(ProcessLookupError):
            os.kill(proc.pid, signal.SIGTERM)
        raise

    info = ServerInfo(
        pid=proc.pid,
        host=host,
        port=port,
        path=path,
        url=f"http://{host}:{port}{path}",
        cairn_path=str(cairn_path) if cairn_path is not None else None,
        log_path=str(log_path),
        started_at=time.time(),
        sandbox_path=str(sandbox_root),
        registry_path=str(registry_file),
    )

    state_file = state_dir / f"{proc.pid}.json"
    state_file.write_text(json.dumps(asdict(info), indent=2))
    return info


def list_servers() -> list[ServerInfo]:
    """Return all dev servers recorded in the state dir.

    Stale entries (process no longer alive) are pruned as a side effect,
    along with their sandbox directories.
    """
    import shutil

    servers: list[ServerInfo] = []
    for sf in sorted(_state_dir().glob("*.json")):
        try:
            data = json.loads(sf.read_text())
            info = ServerInfo(**data)
        except (json.JSONDecodeError, TypeError):
            continue
        if not _process_alive(info.pid):
            if info.sandbox_path:
                shutil.rmtree(info.sandbox_path, ignore_errors=True)
            sf.unlink(missing_ok=True)
            continue
        servers.append(info)
    return servers


def stop(*, pid: int | None = None, all_: bool = False, timeout_s: float = 5.0) -> list[int]:
    """Stop one server by PID or all of them. Returns list of PIDs stopped."""
    if (pid is None) == (not all_):
        raise ValueError("stop() requires exactly one of `pid` or `all_=True`")

    targets: list[ServerInfo]
    if all_:
        targets = list_servers()
    else:
        sf = _state_dir() / f"{pid}.json"
        if not sf.exists():
            return []
        try:
            targets = [ServerInfo(**json.loads(sf.read_text()))]
        except (json.JSONDecodeError, TypeError):
            sf.unlink(missing_ok=True)
            return []

    stopped: list[int] = []
    for info in targets:
        sf = _state_dir() / f"{info.pid}.json"
        try:
            os.kill(info.pid, signal.SIGTERM)
        except ProcessLookupError:
            sf.unlink(missing_ok=True)
            _reap_if_child(info.pid)
            continue
        deadline = time.time() + timeout_s
        while time.time() < deadline and _process_alive(info.pid):
            _reap_if_child(info.pid)
            time.sleep(0.1)
        if _process_alive(info.pid):
            with contextlib.suppress(ProcessLookupError):
                os.kill(info.pid, signal.SIGKILL)
            # Give the kernel a moment to flip state, then reap.
            for _ in range(20):
                _reap_if_child(info.pid)
                if not _process_alive(info.pid):
                    break
                time.sleep(0.05)
        _reap_if_child(info.pid)
        sf.unlink(missing_ok=True)
        if info.sandbox_path:
            import shutil

            shutil.rmtree(info.sandbox_path, ignore_errors=True)
        stopped.append(info.pid)
    return stopped
