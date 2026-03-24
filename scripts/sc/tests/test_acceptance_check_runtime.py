#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
sys.path.insert(0, str(SC_DIR))

from _acceptance_runtime import (  # noqa: E402
    apply_delivery_profile_defaults,
    compute_perf_p95_ms,
    normalize_subtasks_mode,
    parse_only_steps,
    should_mark_hard_failure,
    validate_arg_conflicts,
)


class AcceptanceCheckRuntimeTests(unittest.TestCase):
    def test_apply_delivery_profile_defaults_should_promote_standard_hard_gates(self) -> None:
        args = Namespace(
            delivery_profile="standard",
            perf_p95_ms=None,
            strict_adr_status=False,
            strict_test_quality=False,
            strict_quality_rules=False,
            require_task_test_refs=False,
            require_executed_refs=False,
            require_headless_e2e=False,
            subtasks_coverage="skip",
        )
        resolved = apply_delivery_profile_defaults(args)
        self.assertTrue(resolved.strict_adr_status)
        self.assertTrue(resolved.strict_test_quality)
        self.assertTrue(resolved.strict_quality_rules)
        self.assertTrue(resolved.require_task_test_refs)
        self.assertTrue(resolved.require_executed_refs)
        self.assertTrue(resolved.require_headless_e2e)
        self.assertEqual("require", resolved.subtasks_coverage)
        self.assertEqual(20, resolved.perf_p95_ms)

    def test_parse_only_steps_should_parse_and_dedup(self) -> None:
        self.assertIsNone(parse_only_steps(None))
        self.assertEqual({"tests", "links"}, parse_only_steps("tests, links,tests"))

    def test_normalize_subtasks_mode_should_fallback_to_skip(self) -> None:
        self.assertEqual("skip", normalize_subtasks_mode(None))
        self.assertEqual("skip", normalize_subtasks_mode("bad"))
        self.assertEqual("require", normalize_subtasks_mode("require"))

    def test_validate_conflict_require_headless_needs_tests(self) -> None:
        errs = validate_arg_conflicts(
            only_steps={"links"},
            subtasks_mode="skip",
            require_headless_e2e=True,
            require_executed_refs=False,
            audit_evidence_mode="skip",
        )
        self.assertTrue(any("require-headless-e2e" in e for e in errs))

    def test_validate_conflict_require_executed_refs_needs_tests(self) -> None:
        errs = validate_arg_conflicts(
            only_steps={"links"},
            subtasks_mode="skip",
            require_headless_e2e=False,
            require_executed_refs=True,
            audit_evidence_mode="skip",
        )
        self.assertTrue(any("require-executed-refs" in e for e in errs))

    def test_validate_conflict_audit_require_needs_tests(self) -> None:
        errs = validate_arg_conflicts(
            only_steps={"links"},
            subtasks_mode="skip",
            require_headless_e2e=False,
            require_executed_refs=False,
            audit_evidence_mode="require",
        )
        self.assertTrue(any("security-audit-evidence require" in e for e in errs))

    def test_validate_conflict_subtasks_require_needs_subtasks_step(self) -> None:
        errs = validate_arg_conflicts(
            only_steps={"links"},
            subtasks_mode="require",
            require_headless_e2e=False,
            require_executed_refs=False,
            audit_evidence_mode="skip",
        )
        self.assertTrue(any("subtasks-coverage" in e for e in errs))

    def test_validate_conflict_unknown_only_keys(self) -> None:
        errs = validate_arg_conflicts(
            only_steps={"links", "unknown-step"},
            subtasks_mode="skip",
            require_headless_e2e=False,
            require_executed_refs=False,
            audit_evidence_mode="skip",
        )
        self.assertTrue(any("unknown --only keys" in e for e in errs))

    def test_hard_failure_policy(self) -> None:
        self.assertFalse(should_mark_hard_failure(step_name="security-soft", status="fail", subtasks_mode="require"))
        self.assertFalse(should_mark_hard_failure(step_name="subtasks-coverage", status="fail", subtasks_mode="warn"))
        self.assertTrue(should_mark_hard_failure(step_name="subtasks-coverage", status="fail", subtasks_mode="require"))
        self.assertTrue(should_mark_hard_failure(step_name="tests-all", status="fail", subtasks_mode="skip"))

    def test_compute_perf_p95_ms_precedence(self) -> None:
        with patch.dict(os.environ, {"PERF_P95_THRESHOLD_MS": "33"}, clear=True):
            self.assertEqual(40, compute_perf_p95_ms(perf_p95_ms=40, require_perf=False))
            self.assertEqual(33, compute_perf_p95_ms(perf_p95_ms=None, require_perf=False))
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(20, compute_perf_p95_ms(perf_p95_ms=None, require_perf=True))
            self.assertEqual(0, compute_perf_p95_ms(perf_p95_ms=None, require_perf=False))


if __name__ == "__main__":
    unittest.main()
