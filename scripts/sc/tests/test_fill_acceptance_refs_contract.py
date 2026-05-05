#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
sys.path.insert(0, str(SC_DIR))

from _acceptance_refs_contract import (  # noqa: E402
    run_fill_acceptance_refs_self_check,
    validate_anchor_bound_ref_updates,
    validate_fill_acceptance_summary,
)
from _acceptance_refs_helpers import is_allowed_test_path, parse_model_items_to_paths  # noqa: E402


class FillAcceptanceRefsContractTests(unittest.TestCase):
    def test_validate_summary_should_pass_for_minimal_valid_payload(self) -> None:
        payload = {
            "cmd": "sc-llm-fill-acceptance-refs",
            "date": "2026-02-24",
            "write": False,
            "overwrite_existing": False,
            "rewrite_placeholders": False,
            "tasks": 1,
            "any_updates": 0,
            "results": [{"task_id": 1, "status": "ok"}],
            "missing_after_write": 0,
            "out_dir": "logs/ci/2026-02-24/sc-llm-acceptance-refs",
            "status": "ok",
            "consensus_runs": 1,
            "prd_source": ".taskmaster/docs/prd.txt",
        }
        ok, errors, checked = validate_fill_acceptance_summary(payload)
        self.assertTrue(ok)
        self.assertEqual([], errors)
        self.assertIn("schema_version", checked)

    def test_validate_summary_should_fail_when_missing_required_key(self) -> None:
        payload = {
            "cmd": "sc-llm-fill-acceptance-refs",
            "date": "2026-02-24",
        }
        ok, errors, _ = validate_fill_acceptance_summary(payload)
        self.assertFalse(ok)
        self.assertTrue(any("missing:results" in e for e in errors))

    def test_self_check_should_pass(self) -> None:
        ok, payload, report = run_fill_acceptance_refs_self_check(
            is_allowed_test_path=is_allowed_test_path,
            parse_model_items_to_paths=parse_model_items_to_paths,
        )
        self.assertTrue(ok)
        self.assertEqual("ok", payload.get("status"))
        self.assertIn("self-check", report)

    def test_anchor_bound_ref_updates_should_fail_when_referenced_file_lacks_acceptance_anchor(self) -> None:
        with self.subTest("missing anchor should be hard failure"):
            ok, errors = validate_anchor_bound_ref_updates(
                root=REPO_ROOT,
                updates=[
                    {
                        "task_id": 77,
                        "view": "back",
                        "index": 0,
                        "anchor": "ACC:T77.1",
                        "paths": ["Game.Core.Tests/Tasks/Task77AcceptanceTests.cs"],
                    }
                ],
                read_text=lambda _path: "public sealed class Task77AcceptanceTests {}\n",
            )

            self.assertFalse(ok)
            self.assertIn("missing_anchor:back[0]:ACC:T77.1:Game.Core.Tests/Tasks/Task77AcceptanceTests.cs", errors)


if __name__ == "__main__":
    unittest.main()
