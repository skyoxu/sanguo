#!/usr/bin/env python3
"""Run deterministic project doctor checks and refresh project-health artifacts."""

from __future__ import annotations

import argparse

from _project_health_support import doctor_project, write_project_health_record


def main() -> int:
    parser = argparse.ArgumentParser(description="Run project doctor checks.")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    payload = doctor_project(args.repo_root)
    paths = write_project_health_record(root=args.repo_root, kind=payload["kind"], payload=payload)
    counts = payload.get("counts", {})
    print(
        f"PROJECT_DOCTOR status={payload['status']} fail={counts.get('fail', 0)} "
        f"warn={counts.get('warn', 0)} dashboard={paths['dashboard_html']}"
    )
    return int(payload.get("exit_code", 0))


if __name__ == "__main__":
    raise SystemExit(main())
