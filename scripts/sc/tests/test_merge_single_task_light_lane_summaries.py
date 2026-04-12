#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON_DIR = REPO_ROOT / "scripts" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))


def _load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


merge_mod = _load_module("merge_light_lane_module", "scripts/python/merge_single_task_light_lane_summaries.py")


class MergeSingleTaskLightLaneSummariesTests(unittest.TestCase):
    def test_merge_summaries_should_include_source_metadata_and_task_source_map(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            logs_root = root / "logs" / "ci" / "2026-03-29"
            source_a = logs_root / "single-task-light-lane-v2-a" / "summary.json"
            source_b = logs_root / "single-task-light-lane-v2-b" / "summary.json"
            source_a.parent.mkdir(parents=True, exist_ok=True)
            source_b.parent.mkdir(parents=True, exist_ok=True)

            source_a.write_text(
                json.dumps(
                    {
                        "task_id_start": 11,
                        "task_id_end": 12,
                        "task_count": 2,
                        "processed_tasks": 2,
                        "passed_tasks": 1,
                        "failed_tasks": 1,
                        "status": "fail",
                        "results": [
                            {"task_id": 11, "ok": False, "failed_steps": ["extract"], "first_failed_step": "extract", "steps": [{"step": "extract", "rc": 1, "duration_sec": 9.0}]},
                            {"task_id": 12, "ok": True, "failed_steps": [], "first_failed_step": "", "steps": [{"step": "extract", "rc": 0, "duration_sec": 3.0}]},
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            time.sleep(0.02)
            source_b.write_text(
                json.dumps(
                    {
                        "task_id_start": 11,
                        "task_id_end": 13,
                        "task_count": 3,
                        "processed_tasks": 2,
                        "passed_tasks": 2,
                        "failed_tasks": 0,
                        "status": "ok",
                        "results": [
                            {"task_id": 11, "ok": True, "failed_steps": [], "first_failed_step": "", "steps": [{"step": "extract", "rc": 0, "duration_sec": 5.0}]},
                            {"task_id": 13, "ok": True, "failed_steps": [], "first_failed_step": "", "steps": [{"step": "extract", "rc": 0, "duration_sec": 7.0}]},
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            merged = merge_mod.merge_summaries(root, [source_a, source_b])

            self.assertEqual(3, merged["covered_count"])
            self.assertEqual([], merged["missing_task_ids"])
            self.assertEqual([11, 12, 13], merged["passed_task_ids"])
            self.assertEqual([], merged["failed_task_ids"])
            self.assertEqual([11], merged["overridden_task_ids"])
            self.assertEqual("logs/ci/2026-03-29/single-task-light-lane-v2-b/summary.json", merged["task_source_map"]["11"])
            self.assertEqual(2, len(merged["source_summaries"]))
            self.assertEqual("ok", merged["status"])
            self.assertEqual(0, merged["validation"]["hard_issue_count"])
            self.assertEqual([11], merged["validation"]["overlapping_task_ids"])
            self.assertEqual({"extract": 15.0}, merged["step_duration_totals"])
            self.assertEqual({"extract": 5.0}, merged["step_duration_avg"])
            self.assertEqual({"extract": 3}, merged["step_duration_task_counts"])
            self.assertEqual(
                [
                    {"task_id": 13, "duration_sec": 7.0, "first_failed_step": "", "ok": True},
                    {"task_id": 11, "duration_sec": 5.0, "first_failed_step": "", "ok": True},
                    {"task_id": 12, "duration_sec": 3.0, "first_failed_step": "", "ok": True},
                ],
                merged["slowest_tasks"],
            )
            self.assertEqual(
                {
                    "extract": 0,
                    "align": 0,
                    "coverage": 0,
                    "semantic_gate": 0,
                    "other": 0,
                },
                merged["failed_first_step_counter"],
            )

    def test_merge_summaries_should_preserve_failed_first_step_counter(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            logs_root = root / "logs" / "ci" / "2026-03-29"
            source = logs_root / "single-task-light-lane-v2" / "summary.json"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(
                json.dumps(
                    {
                        "task_id_start": 21,
                        "task_id_end": 23,
                        "task_count": 3,
                        "processed_tasks": 3,
                        "passed_tasks": 0,
                        "failed_tasks": 3,
                        "status": "fail",
                        "results": [
                            {"task_id": 21, "ok": False, "failed_steps": ["extract"], "first_failed_step": "extract", "steps": [{"step": "extract", "rc": 1}]},
                            {"task_id": 22, "ok": False, "failed_steps": ["coverage"], "first_failed_step": "coverage", "steps": [{"step": "coverage", "rc": 1}]},
                            {"task_id": 23, "ok": False, "failed_steps": ["semantic_gate"], "first_failed_step": "semantic_gate", "steps": [{"step": "semantic_gate", "rc": 1}]},
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            merged = merge_mod.merge_summaries(root, [source])

            self.assertEqual(
                {
                    "extract": 1,
                    "align": 0,
                    "coverage": 1,
                    "semantic_gate": 1,
                    "other": 0,
                },
                merged["failed_first_step_counter"],
            )

    def test_merge_summaries_should_fail_validation_when_result_is_outside_declared_scope(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            logs_root = root / "logs" / "ci" / "2026-03-29"
            source = logs_root / "single-task-light-lane-v2" / "summary.json"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(
                json.dumps(
                    {
                        "task_id_start": 21,
                        "task_id_end": 21,
                        "task_count": 1,
                        "processed_tasks": 2,
                        "passed_tasks": 2,
                        "failed_tasks": 0,
                        "status": "ok",
                        "results": [
                            {"task_id": 21, "ok": True, "failed_steps": [], "first_failed_step": "", "steps": [{"step": "extract", "rc": 0}]},
                            {"task_id": 22, "ok": True, "failed_steps": [], "first_failed_step": "", "steps": [{"step": "extract", "rc": 0}]},
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            merged = merge_mod.merge_summaries(root, [source])

            self.assertEqual("fail", merged["status"])
            self.assertEqual([22], merged["validation"]["undeclared_result_task_ids"])
            self.assertEqual(2, merged["validation"]["hard_issue_count"])
            issue_kinds = {item["kind"] for item in merged["validation"]["hard_issues"]}
            self.assertEqual({"undeclared_result_task_ids", "source_result_outside_declared_scope"}, issue_kinds)

    def test_merge_summaries_should_warn_on_incomplete_source_without_failing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            logs_root = root / "logs" / "ci" / "2026-03-29"
            source_a = logs_root / "single-task-light-lane-v2-a" / "summary.json"
            source_b = logs_root / "single-task-light-lane-v2-b" / "summary.json"
            source_a.parent.mkdir(parents=True, exist_ok=True)
            source_b.parent.mkdir(parents=True, exist_ok=True)
            source_a.write_text(
                json.dumps(
                    {
                        "task_id_start": 11,
                        "task_id_end": 13,
                        "task_count": 3,
                        "processed_tasks": 2,
                        "passed_tasks": 2,
                        "failed_tasks": 0,
                        "status": "fail",
                        "results": [
                            {"task_id": 11, "ok": True, "failed_steps": [], "first_failed_step": "", "steps": [{"step": "extract", "rc": 0}]},
                            {"task_id": 12, "ok": True, "failed_steps": [], "first_failed_step": "", "steps": [{"step": "extract", "rc": 0}]},
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            time.sleep(0.02)
            source_b.write_text(
                json.dumps(
                    {
                        "task_id_start": 13,
                        "task_id_end": 13,
                        "task_count": 1,
                        "processed_tasks": 1,
                        "passed_tasks": 1,
                        "failed_tasks": 0,
                        "status": "ok",
                        "results": [
                            {"task_id": 13, "ok": True, "failed_steps": [], "first_failed_step": "", "steps": [{"step": "extract", "rc": 0}]},
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            merged = merge_mod.merge_summaries(root, [source_a, source_b])

            self.assertEqual("ok", merged["status"])
            self.assertEqual(0, merged["validation"]["hard_issue_count"])
            warning_kinds = {item["kind"] for item in merged["validation"]["warnings"]}
            self.assertIn("source_declared_missing_results", warning_kinds)


if __name__ == "__main__":
    unittest.main()
