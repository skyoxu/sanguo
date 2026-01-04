#!/usr/bin/env python3
"""
Unit test/coverage metrics extraction helpers.

Why:
  - sc-acceptance-check should surface key unit-test metrics (count + coverage)
    without forcing humans to open multiple log files.
  - Keep sc-acceptance-check.py under the repo's script size guideline.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


SC_TEST_OUT_RE = re.compile(r"^SC_TEST\s+status=\w+\s+out=(.+)\s*$", re.MULTILINE)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _parse_trx_counters(path: Path) -> dict[str, int] | None:
    try:
        tree = ET.parse(path)  # noqa: S314
        root = tree.getroot()
        for elem in root.iter():
            if not str(elem.tag).endswith("Counters"):
                continue
            counters: dict[str, int] = {}
            for k, v in elem.attrib.items():
                try:
                    counters[k] = int(v)
                except Exception:
                    continue
            return counters or None
    except Exception:
        return None


def _collect_unit_metrics_from_dir(unit_dir: Path) -> dict[str, Any] | None:
    summary_path = unit_dir / "summary.json"
    summary = _read_json(summary_path)
    if not isinstance(summary, dict):
        return None

    coverage = summary.get("coverage") if isinstance(summary.get("coverage"), dict) else {}
    trx_path_str = None
    sel = summary.get("artifacts_selected")
    if isinstance(sel, dict):
        trx_path_str = sel.get("trx")
    trx_path = Path(trx_path_str) if trx_path_str else None

    counters = _parse_trx_counters(trx_path) if (trx_path and trx_path.exists()) else None

    return {
        "unit_dir": str(unit_dir),
        "summary_path": str(summary_path),
        "threshold_ok": bool(summary.get("threshold_ok")),
        "coverage": {
            "line_pct": coverage.get("line_pct"),
            "branch_pct": coverage.get("branch_pct"),
            "lines_covered": coverage.get("lines_covered"),
            "lines_valid": coverage.get("lines_valid"),
            "branches_covered": coverage.get("branches_covered"),
            "branches_valid": coverage.get("branches_valid"),
        },
        "tests": counters,
        "trx": str(trx_path) if trx_path else None,
        "coverage_cobertura": (sel.get("coverage") if isinstance(sel, dict) else None),
    }


def collect_unit_metrics(*, tests_all_log: Path | None, fallback_unit_dir: Path) -> dict[str, Any] | None:
    """
    Best-effort extraction:
      1) Parse tests-all.log for SC_TEST out=<dir>, then read sc-test/summary.json to locate unit artifacts dir.
      2) Fallback to logs/unit/<date>/summary.json if present.
    """
    unit_dir: Path | None = None

    if tests_all_log and tests_all_log.is_file():
        try:
            log_text = tests_all_log.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            log_text = ""

        m = SC_TEST_OUT_RE.search(log_text)
        sc_test_dir = Path(m.group(1).strip()) if m else None
        if sc_test_dir and sc_test_dir.exists():
            sc_test_summary = _read_json(sc_test_dir / "summary.json")
            if isinstance(sc_test_summary, dict):
                steps_list = sc_test_summary.get("steps")
                if isinstance(steps_list, list):
                    for st in steps_list:
                        if isinstance(st, dict) and st.get("name") == "unit" and st.get("artifacts_dir"):
                            unit_dir = Path(str(st.get("artifacts_dir")))
                            break

    if not unit_dir:
        unit_dir = fallback_unit_dir

    return _collect_unit_metrics_from_dir(unit_dir) if unit_dir.exists() else None

