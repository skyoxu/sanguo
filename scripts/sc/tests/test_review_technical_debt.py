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

from _technical_debt import collect_low_priority_review_findings, update_technical_debt_register, write_low_priority_debt_artifacts  # noqa: E402


class ReviewTechnicalDebtTests(unittest.TestCase):
    def test_collect_low_priority_findings_should_keep_only_p2_to_p4(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            review_md = root / "review-code-reviewer.md"
            review_md.write_text(
                "\n".join(
                    [
                        "## P1",
                        "- P1 fix save corruption before merge",
                        "",
                        "## P2",
                        "- P2 trim duplicate helper in Scripts/Core/Foo.cs",
                        "- P3 rename brittle local variable in Scripts/Core/Bar.cs",
                        "",
                        "Verdict: Needs Fix",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            summary = {
                "results": [
                    {
                        "agent": "code-reviewer",
                        "status": "ok",
                        "details": {"verdict": "Needs Fix"},
                        "output_path": str(review_md),
                    }
                ]
            }

            findings = collect_low_priority_review_findings(summary=summary, root=root)

            severities = [item["severity"] for item in findings]
            self.assertEqual(["P2", "P3"], severities)
            self.assertTrue(all(item["agent"] == "code-reviewer" for item in findings))
            self.assertTrue(all("P1" not in item["message"] for item in findings))

    def test_update_register_should_replace_existing_task_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            doc_path = root / "docs" / "technical-debt.md"
            doc_path.parent.mkdir(parents=True, exist_ok=True)
            doc_path.write_text(
                "\n".join(
                    [
                        "# Technical Debt Register",
                        "",
                        "<!-- BEGIN AUTO:RUN_REVIEW_PIPELINE_TECHNICAL_DEBT -->",
                        "## Task 11",
                        "- latest_run_id: oldrun",
                        "",
                        "### P2",
                        "- stale item",
                        "",
                        "<!-- END AUTO:RUN_REVIEW_PIPELINE_TECHNICAL_DEBT -->",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            findings = [
                {
                    "severity": "P2",
                    "agent": "architect-reviewer",
                    "message": "trim duplicate helper in Scripts/Core/Foo.cs",
                    "source_path": "logs/ci/2026-03-22/sc-llm-review-task-11/review-architect-reviewer.md",
                },
                {
                    "severity": "P4",
                    "agent": "code-reviewer",
                    "message": "consider simplifying local naming in Scripts/Core/Bar.cs",
                    "source_path": "logs/ci/2026-03-22/sc-llm-review-task-11/review-code-reviewer.md",
                },
            ]

            payload = update_technical_debt_register(
                doc_path=doc_path,
                task_id="11",
                run_id="newrun",
                findings=findings,
                delivery_profile="fast-ship",
            )

            text = doc_path.read_text(encoding="utf-8")
            self.assertEqual("updated", payload["status"])
            self.assertIn("## Task 11", text)
            self.assertIn("newrun", text)
            self.assertIn("trim duplicate helper", text)
            self.assertIn("consider simplifying local naming", text)
            self.assertNotIn("stale item", text)
            persisted = json.loads(json.dumps(payload, ensure_ascii=False))
            self.assertEqual("11", persisted["task_id"])

    def test_write_artifacts_should_not_touch_register_when_llm_review_not_executed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            doc_path = root / "docs" / "technical-debt.md"
            doc_path.parent.mkdir(parents=True, exist_ok=True)
            original = "\n".join(
                [
                    "# Technical Debt Register",
                    "",
                    "<!-- BEGIN AUTO:RUN_REVIEW_PIPELINE_TECHNICAL_DEBT -->",
                    "## Task 11",
                    "- latest_run_id: oldrun",
                    "",
                    "### P2",
                    "- stale item",
                    "",
                    "<!-- END AUTO:RUN_REVIEW_PIPELINE_TECHNICAL_DEBT -->",
                    "",
                ]
            )
            doc_path.write_text(original, encoding="utf-8")
            out_dir = root / "logs" / "ci" / "2026-03-22" / "sc-review-pipeline-task-11-run"
            out_dir.mkdir(parents=True, exist_ok=True)

            result = write_low_priority_debt_artifacts(
                out_dir=out_dir,
                summary={
                    "steps": [{"name": "sc-llm-review", "status": "planned"}],
                    "results": [],
                },
                task_id="11",
                run_id="run",
                delivery_profile="fast-ship",
                root=root,
            )

            self.assertEqual("skipped", result["register_status"])
            self.assertEqual(original, doc_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
