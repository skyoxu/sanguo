#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
sys.path.insert(0, str(SC_DIR))

from _semantic_gate_all_contract import (  # noqa: E402
    evaluate_semantic_gate_exit,
    run_semantic_gate_all_self_check,
    validate_semantic_gate_summary,
)
from llm_semantic_gate_all import _parse_tsv_output  # noqa: E402


class SemanticGateAllContractTests(unittest.TestCase):
    def test_evaluate_exit_should_fail_when_needs_fix_exceeds_limit(self) -> None:
        fail, reasons = evaluate_semantic_gate_exit(
            needs_fix_count=2,
            unknown_count=0,
            max_needs_fix=0,
            max_unknown=0,
        )
        self.assertTrue(fail)
        self.assertTrue(any("needs_fix_exceeds_limit" in r for r in reasons))

    def test_validate_summary_should_pass_for_minimal_valid_payload(self) -> None:
        summary = {
            "cmd": "sc-semantic-gate-all",
            "date": "2026-02-24",
            "batches": 1,
            "batch_size": 8,
            "total_tasks": 2,
            "counts": {"ok": 1, "needs_fix": 1, "unknown": 0},
            "needs_fix": [2],
            "unknown": [],
            "findings": [
                {"task_id": 1, "verdict": "OK", "reason": "ok"},
                {"task_id": 2, "verdict": "Needs Fix", "reason": "missing"},
            ],
            "status": "fail",
            "max_needs_fix": 0,
            "max_unknown": 0,
            "fail_reasons": ["needs_fix_exceeds_limit:1>0"],
        }
        ok, errors, checked = validate_semantic_gate_summary(summary)
        self.assertTrue(ok)
        self.assertEqual([], errors)
        self.assertIn("schema_version", checked)

    def test_self_check_should_pass(self) -> None:
        def _parse(text: str) -> list[object]:
            from types import SimpleNamespace

            lines = []
            for raw in text.splitlines():
                line = raw.replace("\\t", "\t")
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) < 2:
                    continue
                lines.append(SimpleNamespace(task_id=int(parts[0].lstrip("T")), verdict=parts[1]))
            return lines

        ok, payload, report = run_semantic_gate_all_self_check(parse_tsv_output=_parse)
        self.assertTrue(ok)
        self.assertEqual("ok", payload.get("status"))
        self.assertIn("self-check", report)

    def test_parse_tsv_output_should_normalize_verdicts_and_task_tokens(self) -> None:
        parsed = _parse_tsv_output(
            "\n".join(
                [
                    "T1\tok\treason-a",
                    "t2\tNeeds_Fix\treason-b",
                    "3\tPASS\treason-c",
                    "T4\tFAILED\treason-d",
                    "bad\tOK\treason-e",
                ]
            )
        )
        self.assertEqual(4, len(parsed))
        by_id = {x.task_id: x for x in parsed}
        self.assertEqual("OK", by_id[1].verdict)
        self.assertEqual("Needs Fix", by_id[2].verdict)
        self.assertEqual("OK", by_id[3].verdict)
        self.assertEqual("Needs Fix", by_id[4].verdict)


if __name__ == "__main__":
    unittest.main()

