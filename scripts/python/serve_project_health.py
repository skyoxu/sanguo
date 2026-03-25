#!/usr/bin/env python3
"""Serve the local project-health dashboard on 127.0.0.1."""

from __future__ import annotations

import argparse
import os

from _project_health_server import ensure_project_health_server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the local project-health dashboard.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args(argv)

    if os.environ.get("CI"):
        print("PROJECT_HEALTH_SERVER status=fail reason=serve_not_allowed_in_ci")
        return 2

    payload = ensure_project_health_server(root=args.repo_root, preferred_port=args.port)
    print(
        f"PROJECT_HEALTH_SERVER status=ok reused={str(bool(payload.get('reused'))).lower()} "
        f"url={payload['url']} server_json={payload['server_json']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
