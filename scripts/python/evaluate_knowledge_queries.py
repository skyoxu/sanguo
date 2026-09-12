from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _run_locator(root: Path, request: dict[str, Any]) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(root / "scripts/python/knowledge_locator.py"), "--repository-root", str(root)],
        input=json.dumps(request, ensure_ascii=False),
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
        cwd=root,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "knowledge_locator_failed")
    return json.loads(completed.stdout)


def _matches_expectation(candidate: dict[str, Any], expectation: dict[str, Any]) -> bool:
    path = str(candidate.get("path", ""))
    any_paths = expectation.get("any_paths", [])
    any_prefixes = expectation.get("any_path_prefixes", [])
    domains = expectation.get("domains", [])
    statuses = expectation.get("statuses", [])
    if any_paths and path not in any_paths:
        return False
    if any_prefixes and not any(path.startswith(prefix) for prefix in any_prefixes):
        return False
    if domains and candidate.get("primary_domain") not in domains:
        return False
    if statuses and candidate.get("status") not in statuses:
        return False
    return True


def evaluate(root: Path, suite: dict[str, Any]) -> dict[str, Any]:
    snapshot = json.loads(
        (root / "knowledge/snapshots/repository-source-snapshot.v1.json").read_text(encoding="utf-8")
    )
    passed = 0
    failures: list[dict[str, Any]] = []
    cases = suite.get("cases", [])
    for case in cases:
        request = {
            "schema_version": "newrouge.knowledge-locator-request.v1",
            "request_id": str(case["id"]),
            "consumer": case["consumer"],
            "query": case["query"],
            "snapshot": {"ref": snapshot["ref"], "commit": snapshot["commit"]},
            "policy_revision": "newrouge-knowledge-consumer-policies.v1",
        }
        result = _run_locator(root, request)
        expected_status = case.get("expected_status", "matched")
        ok = result.get("status") == expected_status
        candidates = list(result.get("candidates", []))
        for forbidden in case.get("forbidden_path_prefixes", []):
            if any(str(candidate.get("path", "")).startswith(forbidden) for candidate in candidates):
                ok = False
        for expectation in case.get("must_include", []):
            if not any(_matches_expectation(candidate, expectation) for candidate in candidates):
                ok = False
        if ok:
            passed += 1
        else:
            failures.append(
                {
                    "id": case.get("id"),
                    "result_status": result.get("status"),
                    "candidate_paths": [candidate.get("path") for candidate in candidates],
                }
            )
    return {
        "schema_version": "newrouge.knowledge-evaluation-report.v1",
        "status": "passed" if passed == len(cases) else "failed",
        "passed": passed,
        "total": len(cases),
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the newrouge Knowledge Locator against repository-real queries.")
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--suite",
        type=Path,
        default=Path("knowledge/evaluation/queries.v1.json"),
    )
    args = parser.parse_args()
    root = args.repository_root.resolve()
    suite_path = args.suite if args.suite.is_absolute() else root / args.suite
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    report = evaluate(root, suite)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
