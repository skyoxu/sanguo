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

from _acceptance_runtime import compute_perf_p95_ms, resolve_security_modes  # noqa: E402
from _delivery_profile import (  # noqa: E402
    build_delivery_profile_context,
    delivery_profile_payload,
    profile_acceptance_defaults,
    profile_build_defaults,
    profile_gate_bundle_defaults,
    profile_needs_fix_fast_defaults,
    profile_review_pipeline_defaults,
    profile_llm_review_defaults,
    profile_test_defaults,
    resolve_delivery_profile,
)


class DeliveryProfileTests(unittest.TestCase):
    def test_resolve_delivery_profile_should_default_to_fast_ship(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual("fast-ship", resolve_delivery_profile(None))

    def test_resolve_delivery_profile_should_read_env(self) -> None:
        with patch.dict(os.environ, {"DELIVERY_PROFILE": "playable-ea"}, clear=True):
            self.assertEqual("playable-ea", resolve_delivery_profile(None))

    def test_build_defaults_should_relax_warn_as_error_for_playable(self) -> None:
        self.assertFalse(profile_build_defaults("playable-ea")["warn_as_error"])
        self.assertTrue(profile_build_defaults("fast-ship")["warn_as_error"])
        self.assertTrue(profile_build_defaults("standard")["warn_as_error"])

    def test_test_defaults_should_scale_coverage_and_perf_expectations(self) -> None:
        playable = profile_test_defaults("playable-ea")
        fast_ship = profile_test_defaults("fast-ship")
        standard = profile_test_defaults("standard")

        self.assertFalse(playable["coverage_gate"])
        self.assertEqual(70, fast_ship["coverage_lines_min"])
        self.assertEqual(60, fast_ship["coverage_branches_min"])
        self.assertEqual(90, standard["coverage_lines_min"])
        self.assertEqual(85, standard["coverage_branches_min"])

    def test_acceptance_defaults_should_scale_hardness(self) -> None:
        playable = profile_acceptance_defaults("playable-ea")
        fast_ship = profile_acceptance_defaults("fast-ship")
        standard = profile_acceptance_defaults("standard")

        self.assertEqual("skip", playable["subtasks_coverage"])
        self.assertFalse(playable["require_task_test_refs"])
        self.assertFalse(playable["require_executed_refs"])
        self.assertFalse(playable["require_headless_e2e"])
        self.assertEqual("warn", fast_ship["subtasks_coverage"])
        self.assertTrue(fast_ship["require_task_test_refs"])
        self.assertTrue(standard["require_executed_refs"])
        self.assertTrue(standard["require_headless_e2e"])

    def test_gate_bundle_defaults_should_move_stability_gate_out_of_hard_for_non_standard(self) -> None:
        self.assertFalse(profile_gate_bundle_defaults("playable-ea")["stability_template_hard"])
        self.assertFalse(profile_gate_bundle_defaults("fast-ship")["stability_template_hard"])
        self.assertTrue(profile_gate_bundle_defaults("standard")["stability_template_hard"])

    def test_llm_review_defaults_should_relax_prompt_and_semantic_gate(self) -> None:
        playable = profile_llm_review_defaults("playable-ea")
        fast_ship = profile_llm_review_defaults("fast-ship")
        standard = profile_llm_review_defaults("standard")

        self.assertEqual("skip", playable["semantic_gate"])
        self.assertEqual("skip", playable["prompt_budget_gate"])
        self.assertEqual("warn", fast_ship["semantic_gate"])
        self.assertEqual("warn", fast_ship["prompt_budget_gate"])
        self.assertEqual("require", standard["semantic_gate"])

    def test_review_pipeline_defaults_should_retry_only_in_faster_profiles(self) -> None:
        self.assertEqual(1, profile_review_pipeline_defaults("playable-ea")["max_step_retries"])
        self.assertEqual(1, profile_review_pipeline_defaults("fast-ship")["max_step_retries"])
        self.assertEqual(0, profile_review_pipeline_defaults("standard")["max_step_retries"])

    def test_needs_fix_fast_defaults_should_follow_profile_budget(self) -> None:
        playable = profile_needs_fix_fast_defaults("playable-ea")
        fast_ship = profile_needs_fix_fast_defaults("fast-ship")
        standard = profile_needs_fix_fast_defaults("standard")

        self.assertEqual("summary", playable["diff_mode"])
        self.assertEqual(1, playable["max_rounds"])
        self.assertEqual(20, playable["time_budget_min"])
        self.assertEqual(8, playable["min_llm_budget_min"])

        self.assertEqual("summary", fast_ship["diff_mode"])
        self.assertEqual(2, fast_ship["max_rounds"])
        self.assertEqual(30, fast_ship["time_budget_min"])
        self.assertEqual(10, fast_ship["min_llm_budget_min"])

        self.assertEqual("full", standard["diff_mode"])
        self.assertEqual(2, standard["max_rounds"])
        self.assertEqual(45, standard["time_budget_min"])
        self.assertEqual(12, standard["min_llm_budget_min"])

    def test_delivery_profile_payload_should_include_security_profile_default(self) -> None:
        payload = delivery_profile_payload("fast-ship")
        self.assertEqual("fast-ship", payload["profile"])
        self.assertEqual("host-safe", payload["security_profile_default"])
        self.assertIn("acceptance", payload)
        self.assertIn("llm_review", payload)
        self.assertIn("review_pipeline", payload)
        self.assertIn("needs_fix_fast", payload)

    def test_context_should_describe_playable_ea_stop_loss(self) -> None:
        ctx = build_delivery_profile_context("playable-ea")
        self.assertIn("profile: playable-ea", ctx)
        self.assertIn("playability", ctx.lower())
        self.assertIn("do not raise needs-fix", ctx.lower())

    def test_resolve_security_modes_should_follow_delivery_profile_default_security(self) -> None:
        args = Namespace(
            delivery_profile="standard",
            security_profile=None,
            security_path_gate=None,
            security_sql_gate=None,
            security_audit_schema_gate=None,
            ui_event_json_guards=None,
            ui_event_source_verify=None,
            security_audit_evidence=None,
        )
        profile, modes = resolve_security_modes(args)
        self.assertEqual("strict", profile)
        self.assertEqual("require", modes["audit_evidence"])

    def test_compute_perf_p95_ms_should_accept_delivery_profile_defaults(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(0, compute_perf_p95_ms(perf_p95_ms=profile_acceptance_defaults("playable-ea")["perf_p95_ms"], require_perf=False))
            self.assertEqual(33, compute_perf_p95_ms(perf_p95_ms=profile_acceptance_defaults("fast-ship")["perf_p95_ms"], require_perf=False))
            self.assertEqual(20, compute_perf_p95_ms(perf_p95_ms=profile_acceptance_defaults("standard")["perf_p95_ms"], require_perf=False))


if __name__ == "__main__":
    unittest.main()
