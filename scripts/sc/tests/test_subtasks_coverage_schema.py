#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
sys.path.insert(0, str(SC_DIR))

from _subtasks_coverage_schema import validate_subtasks_coverage_schema  # noqa: E402


def _valid_payload() -> dict:
    return {
        "task_id": "17",
        "status": "ok",
        "subtasks": [
            {
                "id": "17.1",
                "title": "Setup core service",
                "covered": True,
                "matches": [{"view": "back", "acceptance_index": 1, "acceptance_excerpt": "setup core service"}],
                "reason": "Covered by back:1",
            }
        ],
        "uncovered_subtask_ids": [],
        "notes": [],
    }


class SubtasksCoverageSchemaTests(unittest.TestCase):
    def test_accepts_valid_payload(self) -> None:
        ok, errors, obj = validate_subtasks_coverage_schema(_valid_payload())
        self.assertTrue(ok)
        self.assertEqual([], errors)
        self.assertEqual("ok", obj.get("status"))

    def test_rejects_non_bool_covered(self) -> None:
        bad = _valid_payload()
        bad["subtasks"][0]["covered"] = "true"
        ok, errors, _ = validate_subtasks_coverage_schema(bad)
        self.assertFalse(ok)
        self.assertTrue(any("subtask_covered_not_bool" in e for e in errors))

    def test_rejects_covered_without_matches(self) -> None:
        bad = _valid_payload()
        bad["subtasks"][0]["covered"] = True
        bad["subtasks"][0]["matches"] = []
        ok, errors, _ = validate_subtasks_coverage_schema(bad)
        self.assertFalse(ok)
        self.assertTrue(any("subtask_matches_required_when_covered" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
