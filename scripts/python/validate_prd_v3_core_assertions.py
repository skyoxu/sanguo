#!/usr/bin/env python3
"""
Validate PRD V3 core assertions (A-001~A-007) against dotnet TRX execution.

Windows usage:
  py -3 scripts/python/validate_prd_v3_core_assertions.py
  py -3 scripts/python/validate_prd_v3_core_assertions.py --trx logs/ci/2026-03-17/tests.trx
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import sys
import xml.etree.ElementTree as ET


def _default_date() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _default_trx_path() -> str:
    return os.path.join("logs", "ci", _default_date(), "tests.trx")


def _default_summary_path() -> str:
    return os.path.join("logs", "ci", _default_date(), "prd-v3-core-assertions-summary.json")


def _read_json(path: str) -> dict:
    with io.open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"invalid mapping root in {path}")
    return data


def _write_json(path: str, payload: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _load_trx_results(trx_path: str) -> list[dict]:
    tree = ET.parse(trx_path)
    root = tree.getroot()
    ns_prefix = ""
    if root.tag.startswith("{"):
        ns_prefix = root.tag.split("}", 1)[0] + "}"

    results: list[dict] = []
    for node in root.findall(f".//{ns_prefix}UnitTestResult"):
        test_name = (node.attrib.get("testName") or "").strip()
        outcome = (node.attrib.get("outcome") or "").strip()
        if not test_name:
            continue
        results.append(
            {
                "testName": test_name,
                "outcome": outcome,
            }
        )
    return results


def _find_result_by_pattern(results: list[dict], pattern: str) -> dict | None:
    for row in results:
        if pattern in row["testName"]:
            return row
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--map",
        default=os.path.join("scripts", "python", "config", "prd-v3-core-assertions-map.json"),
        help="Assertion mapping JSON path.",
    )
    parser.add_argument("--trx", default=_default_trx_path(), help="TRX file path.")
    parser.add_argument("--summary-out", default=_default_summary_path(), help="Summary output path.")
    args = parser.parse_args()

    summary: dict = {
        "status": "fail",
        "mapPath": args.map,
        "trxPath": args.trx,
        "requiredAssertions": [],
        "checks": [],
        "failures": [],
        "missingMappings": [],
    }

    if not os.path.isfile(args.map):
        summary["failures"].append(f"missing map file: {args.map}")
        _write_json(args.summary_out, summary)
        print(f"PRD_V3_CORE_ASSERTIONS status=fail reason=missing_map summary={args.summary_out}")
        return 1

    if not os.path.isfile(args.trx):
        summary["failures"].append(f"missing trx file: {args.trx}")
        _write_json(args.summary_out, summary)
        print(f"PRD_V3_CORE_ASSERTIONS status=fail reason=missing_trx summary={args.summary_out}")
        return 1

    mapping = _read_json(args.map)
    required = mapping.get("requiredAssertions") or []
    assertions = mapping.get("assertions") or []
    if not isinstance(required, list) or not isinstance(assertions, list):
        summary["failures"].append("invalid map schema: requiredAssertions/assertions")
        _write_json(args.summary_out, summary)
        print(f"PRD_V3_CORE_ASSERTIONS status=fail reason=invalid_schema summary={args.summary_out}")
        return 1

    summary["requiredAssertions"] = list(required)
    assertions_by_id = {}
    for item in assertions:
        if isinstance(item, dict) and isinstance(item.get("assertionId"), str):
            assertions_by_id[item["assertionId"]] = item

    results = _load_trx_results(args.trx)

    failures: list[str] = []

    for assertion_id in required:
        item = assertions_by_id.get(assertion_id)
        if item is None:
            summary["missingMappings"].append(assertion_id)
            failures.append(f"{assertion_id}: missing mapping entry")
            continue

        patterns = item.get("testNameContains") or []
        if not isinstance(patterns, list) or not patterns:
            failures.append(f"{assertion_id}: empty testNameContains")
            summary["checks"].append(
                {"assertionId": assertion_id, "status": "fail", "reason": "empty_test_patterns"}
            )
            continue

        assertion_ok = True
        matched_rows = []
        for pattern in patterns:
            if not isinstance(pattern, str) or not pattern.strip():
                assertion_ok = False
                matched_rows.append(
                    {"pattern": pattern, "status": "fail", "reason": "invalid_pattern"}
                )
                continue

            row = _find_result_by_pattern(results, pattern)
            if row is None:
                assertion_ok = False
                matched_rows.append(
                    {"pattern": pattern, "status": "fail", "reason": "not_found_in_trx"}
                )
                continue

            passed = str(row["outcome"]).lower() == "passed"
            if not passed:
                assertion_ok = False

            matched_rows.append(
                {
                    "pattern": pattern,
                    "status": "pass" if passed else "fail",
                    "testName": row["testName"],
                    "outcome": row["outcome"],
                }
            )

        if not assertion_ok:
            failures.append(f"{assertion_id}: one or more mapped tests missing/failed")

        summary["checks"].append(
            {
                "assertionId": assertion_id,
                "status": "pass" if assertion_ok else "fail",
                "name": item.get("name"),
                "matches": matched_rows,
                "testFileRefs": item.get("testFileRefs") or [],
            }
        )

    summary["failures"].extend(failures)
    summary["status"] = "ok" if not failures else "fail"
    _write_json(args.summary_out, summary)

    if summary["status"] != "ok":
        print(
            f"PRD_V3_CORE_ASSERTIONS status=fail required={len(required)} failures={len(failures)} summary={args.summary_out}"
        )
        return 1

    print(f"PRD_V3_CORE_ASSERTIONS status=ok required={len(required)} summary={args.summary_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

