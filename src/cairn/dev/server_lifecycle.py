"""Lifecycle for background `cairn mcp` HTTP servers used by tests.

Each server runs as a detached subprocess (its own session). State is
persisted as one JSON file per server under
``$XDG_CACHE_HOME/cairn/dev-servers/<pid>.json`` (default
``~/.cache/cairn/dev-servers/``) so ``cairn dev stop --all`` can clean
up without needing the original ``serve`` invocation.
"""

from __future__ import annotations

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
    raise TimeoutError(
        f"server on {host}:{port} did not accept connections within {timeout_s}s"
    )


def _process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


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
    """
    if port is None:
        port = _pick_free_port(host)

    state_dir = _state_dir()
    log_dir = state_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{int(time.time())}-{port}.log"

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
    ]
    if cairn_path is not None:
        cmd.extend(["--cairn-path", str(cairn_path)])

    log_fh = open(log_path, "wb")
    try:
        proc = subprocess.Popen(  # noqa: S603 - args are constructed, not user input
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    finally:
        # Don't keep our copy of the log fd; the child has it.
        log_fh.close()

    try:
        _wait_for_port(host, port)
    except TimeoutError:
        try:
            os.kill(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
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
    )

    state_file = state_dir / f"{proc.pid}.json"
    state_file.write_text(json.dumps(asdict(info), indent=2))
    return info


def list_servers() -> list[ServerInfo]:
    """Return all dev servers recorded in the state dir.

    Stale entries (process no longer alive) are pruned as a side effect.
    """
    servers: list[ServerInfo] = []
    for sf in sorted(_state_dir().glob("*.json")):
        try:
            data = json.loads(sf.read_text())
            info = ServerInfo(**data)
        except (json.JSONDecodeError, TypeError):
            continue
        if not _process_alive(info.pid):
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
            continue
        deadline = time.time() + timeout_s
        while time.time() < deadline and _process_alive(info.pid):
            time.sleep(0.1)
        if _process_alive(info.pid):
            try:
                os.kill(info.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        sf.unlink(missing_ok=True)
        stopped.append(info.pid)
    return stopped
