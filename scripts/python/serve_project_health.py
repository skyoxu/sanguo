#!/usr/bin/env python3
"""Serve the local project-health dashboard on 127.0.0.1."""

from __future__ import annotations

import argparse
import os

from _project_health_cli_status import (
    render_project_health_server_ci_fail_line,
    render_project_health_server_status_line,
)
from _project_health_server import ensure_project_health_server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the local project-health dashboard.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args(argv)

    if os.environ.get("CI"):
        print(render_project_health_server_ci_fail_line())
        return 2

    payload = ensure_project_health_server(root=args.repo_root, preferred_port=args.port)
    print(
        render_project_health_server_status_line(
            reused=bool(payload.get("reused")),
            url=str(payload["url"]),
            server_json=str(payload["server_json"]),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
