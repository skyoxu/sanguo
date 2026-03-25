#!/usr/bin/env python3
"""Run the full project-health scan and refresh the latest dashboard."""

from __future__ import annotations

import argparse
import os

from _project_health_support import project_health_scan
from _project_health_server import ensure_project_health_server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run project-health stage, doctor, and boundary scans.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args(argv)

    if args.serve and os.environ.get("CI"):
        print("PROJECT_HEALTH_SCAN status=fail reason=serve_not_allowed_in_ci")
        return 2

    payload = project_health_scan(args.repo_root)
    suffix = "dashboard=logs/ci/project-health/latest.html"
    if args.serve:
        server = ensure_project_health_server(root=args.repo_root, preferred_port=args.port)
        suffix += f" url={server['url']}"
    print(f"PROJECT_HEALTH_SCAN status={payload['status']} {suffix}")
    return int(payload.get("exit_code", 0))


if __name__ == "__main__":
    raise SystemExit(main())
