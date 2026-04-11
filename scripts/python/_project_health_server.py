#!/usr/bin/env python3
"""Lightweight local HTTP serving for project-health dashboard."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from _project_health_common import latest_dir, now_local, read_json, refresh_dashboard, resolve_root, write_json
from _project_health_schema import validate_project_health_server_payload


HOST = "127.0.0.1"
DEFAULT_PORT_START = 8765
DEFAULT_PORT_END = 8799


def server_json_path(root: Path) -> Path:
    return latest_dir(root) / "server.json"


def dashboard_dir(root: Path) -> Path:
    return latest_dir(root)


def dashboard_url(port: int) -> str:
    return f"http://{HOST}:{port}/latest.html"


def is_process_alive(pid: int) -> bool:
    if int(pid) <= 0:
        return False
    if os.name == "nt":
        try:
            proc = subprocess.run(
                ["tasklist", "/FI", f"PID eq {int(pid)}", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return False
        line = str(proc.stdout or "").strip()
        if proc.returncode != 0 or not line or "No tasks are running" in line:
            return False
        return f'"{int(pid)}"' in line
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def port_accepts_connections(port: int, *, timeout_sec: float = 0.2) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout_sec)
        return sock.connect_ex((HOST, int(port))) == 0


def wait_until_port_open(port: int, *, timeout_sec: float = 5.0, poll_sec: float = 0.1) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if port_accepts_connections(port):
            return True
        time.sleep(poll_sec)
    return False


def choose_available_port(*, preferred_port: int = 0, start: int = DEFAULT_PORT_START, end: int = DEFAULT_PORT_END) -> int:
    preferred = int(preferred_port or 0)
    if preferred > 0:
        if port_accepts_connections(preferred):
            raise RuntimeError(f"requested port is already in use: {preferred}")
        return preferred
    for candidate in range(int(start), int(end) + 1):
        if not port_accepts_connections(candidate):
            return candidate
    raise RuntimeError(f"no free project-health port found in range {start}-{end}")


def load_server_info(root: Path) -> dict[str, Any]:
    path = server_json_path(root)
    if not path.exists():
        return {}
    try:
        payload = read_json(path)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def can_reuse_server(info: dict[str, Any], *, root: Path, preferred_port: int = 0) -> bool:
    repo_root = str(info.get("repo_root") or "").replace("\\", "/")
    expected_root = str(root.resolve()).replace("\\", "/")
    if repo_root != expected_root:
        return False
    port = int(info.get("port") or 0)
    if port <= 0:
        return False
    if int(preferred_port or 0) > 0 and port != int(preferred_port):
        return False
    return port_accepts_connections(port)


def spawn_detached_http_server(*, root: Path, port: int) -> int:
    cmd = [
        sys.executable,
        "-m",
        "http.server",
        str(port),
        "--bind",
        HOST,
        "-d",
        str(dashboard_dir(root)),
    ]
    kwargs: dict[str, Any] = {
        "cwd": str(root),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        flags = 0
        for name in ("DETACHED_PROCESS", "CREATE_NEW_PROCESS_GROUP", "CREATE_NO_WINDOW"):
            flags |= int(getattr(subprocess, name, 0))
        kwargs["creationflags"] = flags
    else:  # pragma: no cover
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(cmd, **kwargs)
    return int(proc.pid)


def ensure_project_health_server(
    *,
    root: Path | str | None = None,
    preferred_port: int = 0,
    port_start: int = DEFAULT_PORT_START,
    port_end: int = DEFAULT_PORT_END,
) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    refresh_dashboard(resolved_root)
    info = load_server_info(resolved_root)
    if can_reuse_server(info, root=resolved_root, preferred_port=preferred_port):
        payload = {
            "status": "ok",
            "reused": True,
            "port": int(info["port"]),
            "pid": int(info.get("pid") or 0),
            "url": str(info["url"]),
            "host": str(info.get("host") or HOST),
            "repo_root": str(info.get("repo_root") or str(resolved_root.resolve()).replace("\\", "/")),
            "served_dir": str(info.get("served_dir") or str(dashboard_dir(resolved_root).resolve()).replace("\\", "/")),
            "started_at": str(info.get("started_at") or now_local().isoformat(timespec="seconds")),
        }
        validate_project_health_server_payload(payload)
        write_json(server_json_path(resolved_root), payload)
        return {
            **payload,
            "server_json": str(server_json_path(resolved_root)).replace("\\", "/"),
        }

    port = choose_available_port(preferred_port=preferred_port, start=port_start, end=port_end)
    pid = spawn_detached_http_server(root=resolved_root, port=port)
    if not wait_until_port_open(port):
        raise RuntimeError(f"project-health server failed to start on port {port}")

    payload = {
        "status": "ok",
        "reused": False,
        "host": HOST,
        "port": port,
        "pid": pid,
        "url": dashboard_url(port),
        "repo_root": str(resolved_root.resolve()).replace("\\", "/"),
        "served_dir": str(dashboard_dir(resolved_root).resolve()).replace("\\", "/"),
        "started_at": now_local().isoformat(timespec="seconds"),
    }
    validate_project_health_server_payload(payload)
    write_json(server_json_path(resolved_root), payload)
    return {
        **payload,
        "server_json": str(server_json_path(resolved_root)).replace("\\", "/"),
    }
