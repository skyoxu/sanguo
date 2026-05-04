#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
sys.path.insert(0, str(SC_DIR))

import llm_extract_task_obligations as obligations_script  # noqa: E402


def _valid_verdict(task_id: str = "999") -> dict:
    return {
        "task_id": task_id,
        "status": "ok",
        "obligations": [
            {
                "id": "O1",
                "source": "master",
                "kind": "core",
                "text": "Core must initialize in deterministic order.",
                "source_excerpt": "Initialize deterministic seed before battle setup.",
                "covered": True,
                "matches": [
                    {
                        "view": "back",
                        "acceptance_index": 1,
                        "acceptance_excerpt": "Seed is initialized before setup.",
                    }
                ],
                "reason": "Covered by acceptance.",
                "suggested_acceptance": [],
            }
        ],
        "uncovered_obligation_ids": [],
        "notes": [],
    }


class ObligationsPipelineOrderTests(unittest.TestCase):
    def test_reuse_hit_writes_artifacts_before_reuse_index_remember(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-02-23" / "sc-llm-obligations-task-999-round-order-reuse"
            prev_dir = root / "logs" / "ci" / "2026-02-22" / "sc-llm-obligations-task-999-round-prev"
            prev_dir.mkdir(parents=True, exist_ok=True)
            prev_verdict_path = prev_dir / "verdict.json"
            prev_verdict_path.write_text(json.dumps(_valid_verdict("999")), encoding="utf-8")

            call_order: list[str] = []
            remember_seen = {"summary_exists": False, "verdict_exists": False}

            def fake_ci_dir(_: str) -> Path:
                out_dir.mkdir(parents=True, exist_ok=True)
                return out_dir

            def fake_write(*, out_dir: Path, summary_obj: dict, verdict_obj: dict, **kwargs) -> bool:  # noqa: ANN003
                call_order.append("write")
                out_dir.mkdir(parents=True, exist_ok=True)
                (out_dir / "summary.json").write_text(json.dumps(summary_obj), encoding="utf-8")
                (out_dir / "verdict.json").write_text(json.dumps(verdict_obj), encoding="utf-8")
                report_text = kwargs.get("report_text")
                trace_text = kwargs.get("trace_text")
                output_last_message = kwargs.get("output_last_message")
                if report_text is not None:
                    (out_dir / "report.md").write_text(str(report_text), encoding="utf-8")
                if trace_text is not None:
                    (out_dir / "trace.log").write_text(str(trace_text), encoding="utf-8")
                if output_last_message is not None:
                    (out_dir / "output-last-message.txt").write_text(json.dumps(output_last_message), encoding="utf-8")
                return True

            def fake_remember(*, summary_path: Path, verdict_path: Path, **kwargs) -> dict:  # noqa: ANN003
                _ = kwargs
                call_order.append("remember")
                remember_seen["summary_exists"] = summary_path.exists()
                remember_seen["verdict_exists"] = verdict_path.exists()
                return {
                    "reuse_index_hit": False,
                    "reuse_index_fallback_scan": False,
                    "reuse_index_pruned_count": 0,
                    "reuse_index_lock_wait_ms": 0,
                }

            triplet = SimpleNamespace(
                task_id="999",
                master={"title": "Task title", "details": "Task details", "testStrategy": "", "subtasks": []},
                back={"acceptance": ["ACC:T999.1 deterministic order"]},
                gameplay=None,
            )

            with (
                patch.object(obligations_script, "repo_root", return_value=root),
                patch.object(obligations_script, "ci_dir", side_effect=fake_ci_dir),
                patch.object(obligations_script, "resolve_triplet", return_value=triplet),
                patch.object(
                    obligations_script,
                    "find_reusable_ok_result_with_stats",
                    return_value=(
                        (prev_verdict_path, {"out_dir": "logs/ci/2026-02-22/sc-llm-obligations-task-999-round-prev"}, _valid_verdict("999")),
                        {"reuse_index_hit": True, "reuse_index_fallback_scan": False, "reuse_index_pruned_count": 0, "reuse_index_lock_wait_ms": 0},
                    ),
                ),
                patch.object(obligations_script, "apply_deterministic_guards", side_effect=lambda **kwargs: (kwargs["obj"], [], [], [])),
                patch.object(obligations_script, "write_checked_and_sync_artifacts", side_effect=fake_write),
                patch.object(obligations_script, "remember_reusable_ok_result_with_stats", side_effect=fake_remember),
                patch.object(
                    sys,
                    "argv",
                    [
                        "llm_extract_task_obligations.py",
                        "--task-id",
                        "999",
                        "--round-id",
                        "order-reuse",
                        "--reuse-last-ok",
                        "--garbled-gate",
                        "off",
                    ],
                ),
            ):
                rc = obligations_script.main()

            self.assertEqual(0, rc)
            self.assertGreaterEqual(len(call_order), 2)
            self.assertEqual(["write", "remember"], call_order[:2])
            self.assertTrue(remember_seen["summary_exists"])
            self.assertTrue(remember_seen["verdict_exists"])

    def test_normal_ok_writes_artifacts_before_reuse_index_remember(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-02-23" / "sc-llm-obligations-task-999-round-order-ok"

            call_order: list[str] = []
            remember_seen = {"summary_exists": False, "verdict_exists": False}

            def fake_ci_dir(_: str) -> Path:
                out_dir.mkdir(parents=True, exist_ok=True)
                return out_dir

            def fake_write(*, out_dir: Path, summary_obj: dict, verdict_obj: dict, **kwargs) -> bool:  # noqa: ANN003
                call_order.append("write")
                out_dir.mkdir(parents=True, exist_ok=True)
                (out_dir / "summary.json").write_text(json.dumps(summary_obj), encoding="utf-8")
                (out_dir / "verdict.json").write_text(json.dumps(verdict_obj), encoding="utf-8")
                report_text = kwargs.get("report_text")
                trace_text = kwargs.get("trace_text")
                output_last_message = kwargs.get("output_last_message")
                if report_text is not None:
                    (out_dir / "report.md").write_text(str(report_text), encoding="utf-8")
                if trace_text is not None:
                    (out_dir / "trace.log").write_text(str(trace_text), encoding="utf-8")
                if output_last_message is not None:
                    (out_dir / "output-last-message.txt").write_text(json.dumps(output_last_message), encoding="utf-8")
                return True

            def fake_remember(*, summary_path: Path, verdict_path: Path, **kwargs) -> dict:  # noqa: ANN003
                _ = kwargs
                call_order.append("remember")
                remember_seen["summary_exists"] = summary_path.exists()
                remember_seen["verdict_exists"] = verdict_path.exists()
                return {
                    "reuse_index_hit": False,
                    "reuse_index_fallback_scan": False,
                    "reuse_index_pruned_count": 0,
                    "reuse_index_lock_wait_ms": 0,
                }

            triplet = SimpleNamespace(
                task_id="999",
                master={"title": "Task title", "details": "Task details", "testStrategy": "", "subtasks": []},
                back={"acceptance": ["ACC:T999.1 deterministic order"]},
                gameplay=None,
            )

            run_results = [{"run": 1, "rc": 0, "status": "ok", "error": None, "schema_errors": []}]
            run_verdicts = [{"run": 1, "status": "ok", "obj": _valid_verdict("999")}]

            with (
                patch.object(obligations_script, "repo_root", return_value=root),
                patch.object(obligations_script, "ci_dir", side_effect=fake_ci_dir),
                patch.object(obligations_script, "resolve_triplet", return_value=triplet),
                patch.object(
                    obligations_script,
                    "run_consensus_rounds",
                    return_value=(run_results, run_verdicts, ["codex", "exec"], False, []),
                ),
                patch.object(obligations_script, "apply_deterministic_guards", side_effect=lambda **kwargs: (kwargs["obj"], [], [], [])),
                patch.object(obligations_script, "write_checked_and_sync_artifacts", side_effect=fake_write),
                patch.object(obligations_script, "remember_reusable_ok_result_with_stats", side_effect=fake_remember),
                patch.object(
                    sys,
                    "argv",
                    [
                        "llm_extract_task_obligations.py",
                        "--task-id",
                        "999",
                        "--round-id",
                        "order-ok",
                        "--garbled-gate",
                        "off",
                    ],
                ),
            ):
                rc = obligations_script.main()

            self.assertEqual(0, rc)
            self.assertGreaterEqual(len(call_order), 2)
            self.assertEqual(["write", "remember"], call_order[:2])
            self.assertTrue(remember_seen["summary_exists"])
            self.assertTrue(remember_seen["verdict_exists"])


if __name__ == "__main__":
    unittest.main()
