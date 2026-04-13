#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

from _pipeline_helpers import build_parser  # noqa: E402
from _pipeline_plan import build_acceptance_command, build_pipeline_steps  # noqa: E402
from _taskmaster import TaskmasterTriplet  # noqa: E402


class PipelinePlanPreflightTests(unittest.TestCase):
    def _args(self) -> SimpleNamespace:
        return SimpleNamespace(
            godot_bin=None,
            review_template="scripts/sc/templates/llm_review/bmad-godot-review-template.txt",
            llm_base="origin/main",
            llm_diff_mode="full",
            llm_no_uncommitted=False,
            allow_full_unit_fallback=False,
            skip_test=False,
            skip_acceptance=False,
            skip_llm_review=False,
        )

    def _triplet(self, *, gameplay: dict | None = None, back: dict | None = None) -> TaskmasterTriplet:
        return TaskmasterTriplet(
            task_id="56",
            master={"id": "56", "title": "Task 56"},
            back=back,
            gameplay=gameplay,
            tasks_json_path=".taskmaster/tasks/tasks.json",
            tasks_back_path=".taskmaster/tasks/tasks_back.json",
            tasks_gameplay_path=".taskmaster/tasks/tasks_gameplay.json",
            taskdoc_path=None,
        )

    def test_build_pipeline_steps_should_use_unit_test_type_when_task_has_no_gd_refs(self) -> None:
        steps = build_pipeline_steps(
            args=self._args(),
            task_id="56",
            run_id="a" * 32,
            delivery_profile="fast-ship",
            security_profile="host-safe",
            acceptance_defaults={},
            triplet=self._triplet(back={"test_refs": ["Game.Core.Tests/Tasks/Task0056AcceptanceTests.cs"]}),
            llm_agents="all",
            llm_timeout_sec=600,
            llm_agent_timeout_sec=180,
            llm_agent_timeouts="",
            llm_semantic_gate="warn",
            llm_strict=False,
            llm_diff_mode="summary",
        )

        test_cmd = steps[0][1]
        self.assertEqual("sc-test", steps[0][0])
        self.assertIn("--type", test_cmd)
        self.assertEqual("unit", test_cmd[test_cmd.index("--type") + 1])

    def test_build_pipeline_steps_should_use_all_test_type_when_task_has_gd_refs(self) -> None:
        steps = build_pipeline_steps(
            args=self._args(),
            task_id="56",
            run_id="b" * 32,
            delivery_profile="fast-ship",
            security_profile="host-safe",
            acceptance_defaults={},
            triplet=self._triplet(gameplay={"test_refs": ["Tests.Godot/tests/Security/Hard/test_db_open_denied_writes_audit_log.gd"]}),
            llm_agents="all",
            llm_timeout_sec=600,
            llm_agent_timeout_sec=180,
            llm_agent_timeouts="",
            llm_semantic_gate="warn",
            llm_strict=False,
            llm_diff_mode="summary",
        )

        test_cmd = steps[0][1]
        self.assertEqual("all", test_cmd[test_cmd.index("--type") + 1])

    def test_build_pipeline_steps_should_forward_allow_full_unit_fallback_to_sc_test(self) -> None:
        args = self._args()
        args.allow_full_unit_fallback = True
        steps = build_pipeline_steps(
            args=args,
            task_id="56",
            run_id="c" * 32,
            delivery_profile="fast-ship",
            security_profile="host-safe",
            acceptance_defaults={},
            triplet=self._triplet(back={"test_refs": ["Game.Core.Tests/Tasks/Task0056AcceptanceTests.cs"]}),
            llm_agents="all",
            llm_timeout_sec=600,
            llm_agent_timeout_sec=180,
            llm_agent_timeouts="",
            llm_semantic_gate="warn",
            llm_strict=False,
            llm_diff_mode="summary",
        )

        test_cmd = steps[0][1]
        self.assertIn("--allow-full-unit-fallback", test_cmd)

    def test_build_pipeline_steps_should_forward_llm_backend_to_llm_review(self) -> None:
        steps = build_pipeline_steps(
            args=self._args(),
            task_id="56",
            run_id="c" * 32,
            delivery_profile="fast-ship",
            security_profile="host-safe",
            acceptance_defaults={},
            triplet=self._triplet(back={"test_refs": ["Game.Core.Tests/Tasks/Task0056AcceptanceTests.cs"]}),
            llm_agents="all",
            llm_timeout_sec=600,
            llm_agent_timeout_sec=180,
            llm_agent_timeouts="",
            llm_semantic_gate="warn",
            llm_strict=False,
            llm_diff_mode="summary",
            llm_backend="openai-api",
        )

        llm_cmd = steps[2][1]
        self.assertIn("--llm-backend", llm_cmd)
        self.assertEqual("openai-api", llm_cmd[llm_cmd.index("--llm-backend") + 1])

    def test_build_parser_help_should_render_allow_full_unit_fallback_text(self) -> None:
        help_text = build_parser().format_help()

        self.assertIn("--allow-full-unit-fallback", help_text)
        self.assertIn("coverage is 0.0%", help_text)

    def test_build_acceptance_command_preflight_should_only_include_deterministic_groups(self) -> None:
        cmd = build_acceptance_command(
            args=self._args(),
            task_id="56",
            run_id="c" * 32,
            delivery_profile="fast-ship",
            security_profile="host-safe",
            acceptance_defaults={
                "require_task_test_refs": True,
                "require_executed_refs": True,
                "require_headless_e2e": True,
                "perf_p95_ms": 33,
            },
            preflight=True,
        )

        self.assertIn("--only", cmd)
        self.assertEqual("adr,links,overlay,contracts,arch,build", cmd[cmd.index("--only") + 1])
        self.assertIn("--require-task-test-refs", cmd)
        self.assertNotIn("--require-executed-refs", cmd)
        self.assertNotIn("--require-headless-e2e", cmd)
        self.assertNotIn("--perf-p95-ms", cmd)

    def test_build_acceptance_command_preflight_should_include_subtasks_when_enabled(self) -> None:
        cmd = build_acceptance_command(
            args=self._args(),
            task_id="56",
            run_id="d" * 32,
            delivery_profile="fast-ship",
            security_profile="host-safe",
            acceptance_defaults={
                "require_task_test_refs": True,
                "subtasks_coverage": "warn",
            },
            preflight=True,
        )

        self.assertIn("--only", cmd)
        self.assertEqual("adr,links,subtasks,overlay,contracts,arch,build", cmd[cmd.index("--only") + 1])
        self.assertIn("--subtasks-coverage", cmd)
        self.assertEqual("warn", cmd[cmd.index("--subtasks-coverage") + 1])


if __name__ == "__main__":
    unittest.main()
