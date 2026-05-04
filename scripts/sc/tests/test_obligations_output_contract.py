#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
sys.path.insert(0, str(SC_DIR))

from _obligations_extract_helpers import validate_verdict_schema  # noqa: E402
from _obligations_artifacts import write_checked_and_sync_artifacts, write_checked_summary_only_and_sync  # noqa: E402
from _obligations_output_contract import (  # noqa: E402
    SUMMARY_SCHEMA_VERSION,
    VERDICT_SCHEMA_VERSION,
    prepare_checked_outputs,
)
from _obligations_runtime_helpers import build_summary_base  # noqa: E402


def _valid_verdict(task_id: str = "2") -> dict:
    return {
        "task_id": task_id,
        "status": "ok",
        "obligations": [
            {
                "id": "O1",
                "source": "master",
                "kind": "core",
                "text": "Must keep deterministic behavior.",
                "source_excerpt": "deterministic",
                "covered": True,
                "matches": [
                    {
                        "view": "gameplay",
                        "acceptance_index": 1,
                        "acceptance_excerpt": "deterministic behavior",
                    }
                ],
                "reason": "Covered.",
                "suggested_acceptance": [],
            }
        ],
        "uncovered_obligation_ids": [],
        "notes": [],
    }


class ObligationsOutputContractTests(unittest.TestCase):
    def test_prepare_checked_outputs_stamps_schema_versions(self) -> None:
        summary = build_summary_base(
            task_id="2",
            title="Create core project structure and namespaces",
            prompt_version="obligations-v3",
            out_dir_rel="logs/ci/2026-02-23/sc-llm-obligations-task-2",
            subtasks_total=2,
            views_present=["gameplay"],
            acceptance_counts={"raw_total": 1, "dedup_total": 1, "per_view_raw": {"gameplay": 1}},
            security_profile="host-safe",
            garbled_gate="on",
            auto_escalate="on",
            reuse_last_ok=True,
            max_schema_errors=5,
        )
        summary["status"] = "ok"
        summary["rc"] = 0
        summary["runtime_code_fingerprint"] = "fp-ut"
        summary["reuse_lookup_key"] = "2|hash|obligations-v3|host-safe"
        verdict = _valid_verdict("2")
        ok, errors, checked_summary, checked_verdict = prepare_checked_outputs(
            summary=summary,
            verdict=verdict,
            validate_verdict_schema=validate_verdict_schema,
        )
        self.assertTrue(ok)
        self.assertEqual([], errors)
        self.assertEqual(SUMMARY_SCHEMA_VERSION, checked_summary.get("schema_version"))
        self.assertEqual(VERDICT_SCHEMA_VERSION, checked_verdict.get("schema_version"))

    def test_prepare_checked_outputs_detects_invalid_verdict(self) -> None:
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
            reuse_last_ok=False,
            max_schema_errors=5,
        )
        summary["status"] = "fail"
        summary["error"] = "test"
        summary["runtime_code_fingerprint"] = "fp-ut"
        summary["reuse_lookup_key"] = "2|hash|obligations-v3|host-safe"
        bad_verdict = {"task_id": "2", "status": "ok", "obligations": [{}]}
        ok, errors, _, _ = prepare_checked_outputs(
            summary=summary,
            verdict=bad_verdict,
            validate_verdict_schema=validate_verdict_schema,
        )
        self.assertFalse(ok)
        self.assertTrue(any(e.startswith("verdict:verdict:") for e in errors))

    def test_prepare_checked_outputs_requires_runtime_fingerprint_and_reuse_key(self) -> None:
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
            reuse_last_ok=False,
            max_schema_errors=5,
        )
        summary["status"] = "ok"
        summary["rc"] = 0
        verdict = _valid_verdict("2")
        ok, errors, _, _ = prepare_checked_outputs(
            summary=summary,
            verdict=verdict,
            validate_verdict_schema=validate_verdict_schema,
        )
        self.assertFalse(ok)
        self.assertIn("summary:runtime_code_fingerprint_missing", errors)
        self.assertIn("summary:reuse_lookup_key_missing", errors)

    def test_write_checked_and_sync_artifacts_writes_all_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "logs" / "ci" / "2026-02-23" / "sc-llm-obligations-task-2-round-ut"
            summary = build_summary_base(
                task_id="2",
                title="Create core project structure and namespaces",
                prompt_version="obligations-v3",
                out_dir_rel="logs/ci/2026-02-23/sc-llm-obligations-task-2-round-ut",
                subtasks_total=1,
                views_present=["gameplay"],
                acceptance_counts={"raw_total": 1, "dedup_total": 1, "per_view_raw": {"gameplay": 1}},
                security_profile="host-safe",
                garbled_gate="on",
                auto_escalate="on",
                reuse_last_ok=True,
                max_schema_errors=5,
            )
            summary["status"] = "ok"
            summary["rc"] = 0
            summary["runtime_code_fingerprint"] = "fp-ut"
            summary["reuse_lookup_key"] = "2|hash|obligations-v3|host-safe"
            verdict = _valid_verdict("2")
            ok = write_checked_and_sync_artifacts(
                out_dir=out_dir,
                summary_obj=summary,
                verdict_obj=verdict,
                validate_verdict_schema=validate_verdict_schema,
                report_text="# report\n",
                trace_text="trace=true\n",
                output_last_message={"task_id": "2", "status": "ok"},
            )
            self.assertTrue(ok)
            self.assertTrue((out_dir / "summary.json").exists())
            self.assertTrue((out_dir / "verdict.json").exists())
            self.assertTrue((out_dir / "report.md").exists())
            self.assertTrue((out_dir / "trace.log").exists())
            self.assertTrue((out_dir / "output-last-message.txt").exists())
            saved_summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(SUMMARY_SCHEMA_VERSION, saved_summary.get("schema_version"))

    def test_write_checked_summary_only_and_sync_updates_summary_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "logs" / "ci" / "2026-02-23" / "sc-llm-obligations-task-2-round-summary-only"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "verdict.json").write_text(json.dumps(_valid_verdict("2"), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            summary = build_summary_base(
                task_id="2",
                title="Create core project structure and namespaces",
                prompt_version="obligations-v3",
                out_dir_rel="logs/ci/2026-02-23/sc-llm-obligations-task-2-round-summary-only",
                subtasks_total=1,
                views_present=["gameplay"],
                acceptance_counts={"raw_total": 1, "dedup_total": 1, "per_view_raw": {"gameplay": 1}},
                security_profile="host-safe",
                garbled_gate="on",
                auto_escalate="on",
                reuse_last_ok=True,
                max_schema_errors=5,
            )
            summary["status"] = "ok"
            summary["rc"] = 0
            summary["reuse_index_hit"] = True
            summary["runtime_code_fingerprint"] = "fp-ut"
            summary["reuse_lookup_key"] = "2|hash|obligations-v3|host-safe"
            ok = write_checked_summary_only_and_sync(out_dir=out_dir, summary_obj=summary)
            self.assertTrue(ok)
            self.assertTrue((out_dir / "summary.json").exists())
            self.assertTrue((out_dir / "verdict.json").exists())
            saved_summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(SUMMARY_SCHEMA_VERSION, saved_summary.get("schema_version"))
            self.assertTrue(saved_summary.get("reuse_index_hit"))


if __name__ == "__main__":
    unittest.main()
