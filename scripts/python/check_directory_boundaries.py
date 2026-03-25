#!/usr/bin/env python3
"""Run deterministic directory responsibility checks and refresh project-health artifacts."""

from __future__ import annotations

import argparse

from _project_health_support import check_directory_boundaries, write_project_health_record


def main() -> int:
    parser = argparse.ArgumentParser(description="Run directory boundary checks.")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    payload = check_directory_boundaries(args.repo_root)
    paths = write_project_health_record(root=args.repo_root, kind=payload["kind"], payload=payload)
    print(
        f"DIRECTORY_BOUNDARIES status={payload['status']} fail={len(payload.get('violations', []))} "
        f"warn={len(payload.get('warnings', []))} dashboard={paths['dashboard_html']}"
    )
    return int(payload.get("exit_code", 0))


if __name__ == "__main__":
    raise SystemExit(main())
