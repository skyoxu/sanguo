#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
sys.path.insert(0, str(SC_DIR))

from _obligations_extract_helpers import (  # noqa: E402
    bucket_schema_errors,
    build_input_hash,
    build_self_check_report,
    limit_schema_errors,
    validate_verdict_schema,
)
from _obligations_prompt_acceptance import compute_acceptance_dedup_stats  # noqa: E402
from _obligations_reuse_index import (  # noqa: E402
    apply_reuse_stats,
    build_reuse_lookup_key,
    find_reusable_ok_result,
    find_reusable_ok_result_with_stats,
    remember_reusable_ok_result,
)
from _obligations_runtime_helpers import build_summary_base  # noqa: E402
from _obligations_reuse_explain import explain_reuse_miss  # noqa: E402


def _valid_verdict(task_id: str = "14") -> dict:
    return {
        "task_id": task_id,
        "status": "ok",
        "obligations": [
            {
                "id": "O1",
                "source": "master",
                "kind": "godot",
                "text": "Main menu options must exist.",
                "source_excerpt": "Create main menu scene with new run and continue options.",
                "covered": True,
                "matches": [
                    {
                        "view": "back",
                        "acceptance_index": 1,
                        "acceptance_excerpt": "Main menu has New Run and Continue",
                    }
                ],
                "reason": "Covered by acceptance.",
                "suggested_acceptance": [],
            }
        ],
        "uncovered_obligation_ids": [],
        "notes": [],
    }


class ObligationsExtractHelpersTests(unittest.TestCase):
    def test_validate_verdict_schema_accepts_valid_payload(self) -> None:
        ok, errors, obj = validate_verdict_schema(_valid_verdict())
        self.assertTrue(ok)
        self.assertEqual([], errors)
        self.assertEqual("ok", obj.get("status"))

    def test_validate_verdict_schema_rejects_missing_covered(self) -> None:
        bad = _valid_verdict()
        del bad["obligations"][0]["covered"]
        ok, errors, _ = validate_verdict_schema(bad)
        self.assertFalse(ok)
        self.assertTrue(any("obligation_covered_not_bool" in e for e in errors))

    def test_build_input_hash_is_stable(self) -> None:
        a = {"b": 2, "a": 1, "nested": {"y": 2, "x": 1}}
        b = {"nested": {"x": 1, "y": 2}, "a": 1, "b": 2}
        self.assertEqual(build_input_hash(a), build_input_hash(b))

    def test_limit_schema_errors_respects_max_count(self) -> None:
        errors = ["a:1", "b:2", "c:3", "d:4"]
        self.assertEqual(["a:1", "b:2"], limit_schema_errors(errors, max_count=2))

    def test_bucket_schema_errors_groups_by_prefix(self) -> None:
        errors = [
            "obligation_text_missing:1",
            "obligation_text_missing:2",
            "status_invalid",
            "match_view_invalid:3.1",
        ]
        self.assertEqual(
            {
                "match_view_invalid": 1,
                "obligation_text_missing": 2,
                "status_invalid": 1,
            },
            bucket_schema_errors(errors),
        )

    def test_build_self_check_report_contains_status(self) -> None:
        report = build_self_check_report(True, {"issues": []})
        self.assertIn("- status: ok", report)
        self.assertIn("## Issues", report)

    def test_compute_acceptance_dedup_stats_counts_raw_and_dedup(self) -> None:
        stats = compute_acceptance_dedup_stats(
            {
                "back": ["A", "  B  ", "A"],
                "gameplay": ["b", "C", ""],
            }
        )
        self.assertEqual(5, stats.get("raw_total"))
        self.assertEqual(3, stats.get("dedup_total"))
        self.assertEqual({"back": 3, "gameplay": 2}, stats.get("per_view_raw"))

    def test_build_summary_base_contains_mandatory_keys(self) -> None:
        summary = build_summary_base(
            task_id="2",
            title="Create core project structure and namespaces",
            prompt_version="obligations-v3",
            out_dir_rel="logs/ci/2026-02-23/sc-llm-obligations-task-2",
            subtasks_total=3,
            views_present=["gameplay"],
            acceptance_counts={"raw_total": 5, "dedup_total": 5, "per_view_raw": {"gameplay": 5}},
            security_profile="host-safe",
            garbled_gate="on",
            auto_escalate="on",
            reuse_last_ok=True,
            max_schema_errors=5,
        )
        mandatory = [
            "status",
            "error",
            "input_hash",
            "runtime_code_fingerprint",
            "reuse_lookup_key",
            "schema_errors",
            "schema_error_buckets",
            "schema_error_codes",
            "schema_error_count",
            "run_results",
            "auto_escalate",
            "acceptance_counts",
        ]
        for key in mandatory:
            self.assertIn(key, summary)
        self.assertEqual(0, summary.get("schema_error_count"))
        self.assertEqual([], summary.get("schema_errors"))
        self.assertEqual({}, summary.get("schema_error_buckets"))
        self.assertEqual([], summary.get("schema_error_codes"))

    def test_find_reusable_ok_result_returns_latest_match(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            input_hash = "abc123"
            run1 = root / "2026-02-23" / "sc-llm-obligations-task-14-round-r1"
            run2 = root / "2026-02-23" / "sc-llm-obligations-task-14-round-r2"
            run1.mkdir(parents=True, exist_ok=True)
            run2.mkdir(parents=True, exist_ok=True)

            s1 = {"status": "ok", "input_hash": input_hash}
            s2 = {"status": "ok", "input_hash": input_hash}
            v1 = _valid_verdict("14")
            v2 = _valid_verdict("14")
            run1.joinpath("summary.json").write_text(json.dumps(s1), encoding="utf-8")
            run1.joinpath("verdict.json").write_text(json.dumps(v1), encoding="utf-8")
            run2.joinpath("summary.json").write_text(json.dumps(s2), encoding="utf-8")
            run2.joinpath("verdict.json").write_text(json.dumps(v2), encoding="utf-8")

            res = find_reusable_ok_result(
                task_id="14",
                input_hash=input_hash,
                logs_root=root,
                current_out_dir=root / "2026-02-23" / "sc-llm-obligations-task-14-round-current",
            )
            self.assertIsNotNone(res)
            verdict_path, _, verdict = res  # type: ignore[misc]
            self.assertTrue(str(verdict_path).endswith("verdict.json"))
            self.assertEqual("14", verdict.get("task_id"))

    def test_find_reusable_ok_result_hits_index_entry(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            task_id = "14"
            input_hash = "hash-index"
            run = root / "2026-02-23" / "sc-llm-obligations-task-14-round-r3"
            run.mkdir(parents=True, exist_ok=True)
            summary_path = run / "summary.json"
            verdict_path = run / "verdict.json"
            summary_path.write_text(json.dumps({"status": "ok", "input_hash": input_hash}), encoding="utf-8")
            verdict_path.write_text(json.dumps(_valid_verdict(task_id)), encoding="utf-8")
            remember_reusable_ok_result(
                task_id=task_id,
                input_hash=input_hash,
                prompt_version="obligations-v3",
                security_profile="host-safe",
                logs_root=root,
                summary_path=summary_path,
                verdict_path=verdict_path,
            )
            res = find_reusable_ok_result(
                task_id=task_id,
                input_hash=input_hash,
                prompt_version="obligations-v3",
                security_profile="host-safe",
                logs_root=root,
                current_out_dir=root / "2026-02-23" / "sc-llm-obligations-task-14-round-current",
            )
            self.assertIsNotNone(res)
            hit_verdict_path, _, hit_verdict = res  # type: ignore[misc]
            self.assertEqual(str(verdict_path.resolve()), str(hit_verdict_path.resolve()))
            self.assertEqual(task_id, hit_verdict.get("task_id"))

    def test_remember_reusable_ok_result_prunes_stale_entries(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            stale_run = root / "2026-02-01" / "sc-llm-obligations-task-14-round-old"
            stale_run.mkdir(parents=True, exist_ok=True)
            stale_summary = stale_run / "summary.json"
            stale_verdict = stale_run / "verdict.json"
            stale_summary.write_text(json.dumps({"status": "ok", "input_hash": "stale"}), encoding="utf-8")
            stale_verdict.write_text(json.dumps(_valid_verdict("14")), encoding="utf-8")

            idx_path = root / "sc-llm-obligations-reuse-index.json"
            stale_time = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=90)).isoformat()
            idx_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "entries": {
                            "stale-key": {
                                "task_id": "14",
                                "input_hash": "stale",
                                "prompt_version": "obligations-v3",
                                "security_profile": "host-safe",
                                "summary_path": "2026-02-01/sc-llm-obligations-task-14-round-old/summary.json",
                                "verdict_path": "2026-02-01/sc-llm-obligations-task-14-round-old/verdict.json",
                                "updated_at": stale_time,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            fresh_run = root / "2026-02-23" / "sc-llm-obligations-task-14-round-new"
            fresh_run.mkdir(parents=True, exist_ok=True)
            fresh_summary = fresh_run / "summary.json"
            fresh_verdict = fresh_run / "verdict.json"
            fresh_summary.write_text(json.dumps({"status": "ok", "input_hash": "fresh"}), encoding="utf-8")
            fresh_verdict.write_text(json.dumps(_valid_verdict("14")), encoding="utf-8")

            remember_reusable_ok_result(
                task_id="14",
                input_hash="fresh",
                prompt_version="obligations-v3",
                security_profile="host-safe",
                logs_root=root,
                summary_path=fresh_summary,
                verdict_path=fresh_verdict,
            )

            idx_obj = json.loads(idx_path.read_text(encoding="utf-8"))
            entries = idx_obj.get("entries") or {}
            self.assertNotIn("stale-key", entries)
            self.assertEqual(1, len(entries))

    def test_find_reusable_ok_result_with_stats_reports_index_hit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            task_id = "14"
            input_hash = "hit-stats"
            run = root / "2026-02-23" / "sc-llm-obligations-task-14-round-hit"
            run.mkdir(parents=True, exist_ok=True)
            summary_path = run / "summary.json"
            verdict_path = run / "verdict.json"
            summary_path.write_text(json.dumps({"status": "ok", "input_hash": input_hash}), encoding="utf-8")
            verdict_path.write_text(json.dumps(_valid_verdict(task_id)), encoding="utf-8")
            remember_reusable_ok_result(
                task_id=task_id,
                input_hash=input_hash,
                prompt_version="obligations-v3",
                security_profile="host-safe",
                logs_root=root,
                summary_path=summary_path,
                verdict_path=verdict_path,
            )

            result, stats = find_reusable_ok_result_with_stats(
                task_id=task_id,
                input_hash=input_hash,
                prompt_version="obligations-v3",
                security_profile="host-safe",
                logs_root=root,
                current_out_dir=root / "2026-02-23" / "sc-llm-obligations-task-14-round-current",
            )
            self.assertIsNotNone(result)
            self.assertTrue(stats.get("reuse_index_hit"))
            self.assertFalse(stats.get("reuse_index_fallback_scan"))
            self.assertGreaterEqual(int(stats.get("reuse_index_lock_wait_ms") or 0), 0)

    def test_apply_reuse_stats_accumulates_counts(self) -> None:
        summary = build_summary_base(
            task_id="2",
            title="Create core project structure and namespaces",
            prompt_version="obligations-v3",
            out_dir_rel="logs/ci/2026-02-23/sc-llm-obligations-task-2",
            subtasks_total=1,
            views_present=["gameplay"],
            acceptance_counts={"raw_total": 1, "dedup_total": 1, "per_view_raw": {"gameplay": 1}},
            security_profile="host-safe",
            garbled_gate="on",
            auto_escalate="on",
            reuse_last_ok=True,
            max_schema_errors=5,
        )
        apply_reuse_stats(
            summary,
            {
                "reuse_index_hit": True,
                "reuse_index_fallback_scan": False,
                "reuse_index_pruned_count": 2,
                "reuse_index_lock_wait_ms": 7,
            },
        )
        apply_reuse_stats(
            summary,
            {
                "reuse_index_hit": False,
                "reuse_index_fallback_scan": True,
                "reuse_index_pruned_count": 1,
                "reuse_index_lock_wait_ms": 3,
            },
        )
        self.assertTrue(summary.get("reuse_index_hit"))
        self.assertTrue(summary.get("reuse_index_fallback_scan"))
        self.assertEqual(3, summary.get("reuse_index_pruned_count"))
        self.assertEqual(10, summary.get("reuse_index_lock_wait_ms"))

    def test_build_reuse_lookup_key_is_stable(self) -> None:
        a = build_reuse_lookup_key(task_id="2", input_hash="abc", prompt_version="obligations-v3", security_profile="host-safe")
        b = build_reuse_lookup_key(task_id="2", input_hash="abc", prompt_version="obligations-v3", security_profile="host-safe")
        c = build_reuse_lookup_key(task_id="2", input_hash="abc", prompt_version="obligations-v3", security_profile="strict")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_explain_reuse_miss_reports_input_hash_and_runtime_fp(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run = root / "2026-02-23" / "sc-llm-obligations-task-14-round-hit"
            run.mkdir(parents=True, exist_ok=True)
            summary_path = run / "summary.json"
            verdict_path = run / "verdict.json"
            summary_path.write_text(
                json.dumps(
                    {
                        "status": "ok",
                        "input_hash": "cache-hash",
                        "runtime_code_fingerprint": "fp-cache",
                    }
                ),
                encoding="utf-8",
            )
            verdict_path.write_text(json.dumps(_valid_verdict("14")), encoding="utf-8")
            remember_reusable_ok_result(
                task_id="14",
                input_hash="cache-hash",
                prompt_version="obligations-v3",
                security_profile="host-safe",
                logs_root=root,
                summary_path=summary_path,
                verdict_path=verdict_path,
            )
            explain = explain_reuse_miss(
                logs_root=root,
                task_id="14",
                input_hash="target-hash",
                prompt_version="obligations-v3",
                security_profile="host-safe",
                runtime_code_fingerprint="fp-target",
            )
            self.assertEqual(1, explain.get("candidate_counts", {}).get("same_task"))
            mismatch = set(explain.get("mismatch_dimensions") or [])
            self.assertIn("input_hash", mismatch)
            self.assertIn("runtime_code_fingerprint", mismatch)


if __name__ == "__main__":
    unittest.main()
