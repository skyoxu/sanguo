#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
sys.path.insert(0, str(SC_DIR))

from _marathon_policy import apply_context_refresh_policy, refresh_diff_stats  # noqa: E402


class MarathonPolicyTests(unittest.TestCase):
    def test_refresh_diff_stats_should_capture_categories_and_axes_growth(self) -> None:
        state = {}
        refresh_diff_stats(
            state,
            snapshot={
                "files_changed": 2,
                "untracked_files": 0,
                "lines_added": 10,
                "lines_deleted": 5,
                "total_lines": 15,
                "categories": ["docs", "scripts"],
                "axes": ["governance", "implementation"],
            },
        )
        refresh_diff_stats(
            state,
            snapshot={
                "files_changed": 4,
                "untracked_files": 1,
                "lines_added": 80,
                "lines_deleted": 40,
                "total_lines": 120,
                "categories": ["docs", "scripts", "core-contracts", "core-tests"],
                "axes": ["governance", "implementation", "contracts", "tests"],
            },
        )
        self.assertEqual(["docs", "scripts"], state["diff_stats"]["baseline"]["categories"])
        self.assertEqual(["contracts", "tests"], state["diff_stats"]["growth"]["new_axes"])
        self.assertEqual(["core-contracts", "core-tests"], state["diff_stats"]["growth"]["new_categories"])

    def test_apply_context_refresh_policy_should_flag_large_diff_growth(self) -> None:
        state = {
            "status": "running",
            "resume_count": 1,
            "steps": {
                "sc-test": {"status": "ok", "attempt_count": 1},
                "sc-acceptance-check": {"status": "pending", "attempt_count": 0},
                "sc-llm-review": {"status": "pending", "attempt_count": 0},
            },
            "diff_stats": {
                "baseline": {"total_lines": 20, "files_changed": 2, "untracked_files": 0, "categories": ["scripts"], "axes": ["implementation"]},
                "current": {"total_lines": 360, "files_changed": 9, "untracked_files": 1, "categories": ["docs", "scripts"], "axes": ["governance", "implementation"]},
                "growth": {"total_lines": 340, "files_changed": 7, "untracked_files": 1, "new_categories": ["docs"], "new_axes": ["governance"]},
            },
        }
        apply_context_refresh_policy(state, failure_threshold=3, resume_threshold=3, diff_lines_threshold=300, diff_categories_threshold=0)
        self.assertTrue(state["context_refresh_needed"])
        self.assertIn("diff_lines_growth>=300(20->360)", state["context_refresh_reasons"])

    def test_apply_context_refresh_policy_should_flag_repeated_failures(self) -> None:
        state = {
            "status": "fail",
            "resume_count": 1,
            "steps": {
                "sc-test": {"status": "fail", "attempt_count": 2},
                "sc-acceptance-check": {"status": "pending", "attempt_count": 0},
                "sc-llm-review": {"status": "pending", "attempt_count": 0},
            },
        }
        apply_context_refresh_policy(state, failure_threshold=2, resume_threshold=3, diff_lines_threshold=0, diff_categories_threshold=0)
        self.assertTrue(state["context_refresh_needed"])
        self.assertIn("step_failures:sc-test>=2", state["context_refresh_reasons"])

    def test_apply_context_refresh_policy_should_flag_repeated_resumes(self) -> None:
        state = {
            "status": "fail",
            "resume_count": 2,
            "steps": {
                "sc-test": {"status": "ok", "attempt_count": 1},
                "sc-acceptance-check": {"status": "fail", "attempt_count": 1},
                "sc-llm-review": {"status": "pending", "attempt_count": 0},
            },
        }
        apply_context_refresh_policy(state, failure_threshold=3, resume_threshold=2, diff_lines_threshold=0, diff_categories_threshold=0)
        self.assertTrue(state["context_refresh_needed"])
        self.assertIn("resume_count>=2", state["context_refresh_reasons"])

    def test_apply_context_refresh_policy_should_flag_category_growth_and_semantic_mix(self) -> None:
        state = {
            "status": "running",
            "resume_count": 1,
            "steps": {
                "sc-test": {"status": "ok", "attempt_count": 1},
                "sc-acceptance-check": {"status": "pending", "attempt_count": 0},
                "sc-llm-review": {"status": "pending", "attempt_count": 0},
            },
            "diff_stats": {
                "baseline": {"total_lines": 15, "files_changed": 2, "untracked_files": 0, "categories": ["scripts"], "axes": ["implementation"]},
                "current": {
                    "total_lines": 120,
                    "files_changed": 5,
                    "untracked_files": 0,
                    "categories": ["docs", "scripts", "core-contracts", "core-tests"],
                    "axes": ["governance", "implementation", "contracts", "tests"],
                },
                "growth": {
                    "total_lines": 105,
                    "files_changed": 3,
                    "untracked_files": 0,
                    "new_categories": ["docs", "core-contracts", "core-tests"],
                    "new_axes": ["governance", "contracts", "tests"],
                },
            },
        }
        apply_context_refresh_policy(state, failure_threshold=3, resume_threshold=3, diff_lines_threshold=0, diff_categories_threshold=2)
        self.assertTrue(state["context_refresh_needed"])
        self.assertIn("diff_categories_added>=2(core-contracts,core-tests,docs)", state["context_refresh_reasons"])
        self.assertIn("semantic_axes_mix(governance+implementation|new=contracts,governance,tests)", state["context_refresh_reasons"])


if __name__ == "__main__":
    unittest.main()
