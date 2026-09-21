#!/usr/bin/env python3
"""Validate semantic-topology structure without creating task or semantic facts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from _knowledge_catalog_builder import GitSnapshot
from _project_health_tasks import task_details
from _semantic_topology import TOPOLOGY_ARTIFACTS, load_topology_from_snapshot


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--authority-ref",
        default="HEAD",
        help="Git ref to validate when topology artifacts exist (default: current checkout HEAD).",
    )
    parser.add_argument("--require-available", action="store_true")
    args = parser.parse_args(argv)
    root = args.repo_root.resolve()

    present = {
        name: (root / path).is_file()
        for name, path in TOPOLOGY_ARTIFACTS.items()
    }
    present_count = sum(present.values())
    if present_count == 0:
        status = "blocked" if args.require_available else "legacy_unmapped"
        print(json.dumps({
            "status": status,
            "reason": "topology artifacts are not present in this checkout",
            "identity": {"kind": "checkout", "revision": None},
        }, ensure_ascii=False))
        return 1 if args.require_available else 0
    if present_count != len(TOPOLOGY_ARTIFACTS):
        missing = [
            path for name, path in TOPOLOGY_ARTIFACTS.items()
            if not present[name]
        ]
        print(json.dumps({
            "status": "blocked",
            "reason": "partial topology artifact set",
            "missing": missing,
        }, ensure_ascii=False))
        return 1

    snapshot = GitSnapshot(root, args.authority_ref)
    view = load_topology_from_snapshot(snapshot, task_details(snapshot), identity_kind="checkout")
    blocking = list(view.get("problems", []))
    status = "passed" if view.get("fresh") and not blocking else "blocked"
    print(json.dumps({
        "status": status,
        "identity": view.get("identity"),
        "summary": view.get("summary"),
        "problems": view.get("problems", []),
    }, ensure_ascii=False))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
