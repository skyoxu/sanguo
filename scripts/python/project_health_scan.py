#!/usr/bin/env python3
"""Run the full project-health scan and refresh the latest dashboard."""

from __future__ import annotations

import argparse
import os

from _project_health_cli_status import (
    render_project_health_scan_ci_fail_line,
    render_project_health_scan_status_line,
)
from _project_health_support import project_health_scan
from _project_health_server import ensure_project_health_server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run project-health stage, doctor, and boundary scans.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args(argv)

    if args.serve and os.environ.get("CI"):
        print(render_project_health_scan_ci_fail_line())
        return 2

    payload = project_health_scan(args.repo_root)
    url = ""
    if args.serve:
        server = ensure_project_health_server(root=args.repo_root, preferred_port=args.port)
        url = str(server["url"])
    print(render_project_health_scan_status_line(status=str(payload["status"]), url=url))
    return int(payload.get("exit_code", 0))


if __name__ == "__main__":
    raise SystemExit(main())
