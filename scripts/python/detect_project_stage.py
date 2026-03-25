#!/usr/bin/env python3
"""Detect the current repo stage and refresh project-health artifacts."""

from __future__ import annotations

import argparse

from _project_health_support import detect_project_stage, write_project_health_record


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect the current repo stage.")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    payload = detect_project_stage(args.repo_root)
    paths = write_project_health_record(root=args.repo_root, kind=payload["kind"], payload=payload)
    print(
        f"PROJECT_STAGE status={payload['status']} stage={payload['stage']} "
        f"dashboard={paths['dashboard_html']}"
    )
    return int(payload.get("exit_code", 0))


if __name__ == "__main__":
    raise SystemExit(main())
