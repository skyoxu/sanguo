#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))


def _load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


policy_module = _load_module("sc_execution_plan_policy_module", "scripts/sc/_execution_plan_policy.py")
check_script = _load_module("sc_check_tdd_execution_plan_module", "scripts/sc/check_tdd_execution_plan.py")


class _FakeTriplet:
    def __init__(self, task_id: str = "11") -> None:
        self.task_id = task_id
        self.master = {"title": "Generate acceptance-driven tests"}
        self.back = {
            "acceptance": [
                "Alpha. Refs: Game.Core.Tests/FooTests.cs",
                "Beta. Refs: Tests.Godot/tests/test_bar.gd",
                "Gamma. Refs: Tests/Integration/BazTests.cs",
                "Delta. Refs: Game.Core.Tests/ExistingTests.cs",
            ]
        }
        self.gameplay = None


class ExecutionPlanPolicyTests(unittest.TestCase):
    def test_assess_plan_need_should_flag_threshold_when_two_or_more_signals_hit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            existing = root / "Game.Core.Tests" / "ExistingTests.cs"
            existing.parent.mkdir(parents=True, exist_ok=True)
            existing.write_text("// existing\n", encoding="utf-8")
            triplet = _FakeTriplet()

            assessment = policy_module.assess_execution_plan_need(
                repo_root=root,
                triplet=triplet,
                task_id="11",
                tdd_stage="red-first",
                verify="auto",
            )

        self.assertEqual(3, assessment.missing_refs_count)
        self.assertEqual(4, assessment.anchor_count)
        self.assertTrue(assessment.threshold_hit)
        active_ids = {item["id"] for item in assessment.signals if item["active"]}
        self.assertIn("missing_refs_ge_3", active_ids)
        self.assertIn("mixed_cs_and_gd", active_ids)
        self.assertIn("red_first_stage", active_ids)
        self.assertIn("verify_auto_or_all", active_ids)
        self.assertIn("anchors_ge_4", active_ids)
        self.assertIn("multiple_test_roots", active_ids)

    def test_find_active_execution_plans_should_only_return_non_done_matches(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan_dir = root / "execution-plans"
            plan_dir.mkdir(parents=True, exist_ok=True)
            (plan_dir / "active.md").write_text(
                "\n".join(
                    [
                        "# Active",
                        "",
                        "- Title: Active",
                        "- Status: active",
                        "- Related task id(s): `11`",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (plan_dir / "done.md").write_text(
                "\n".join(
                    [
                        "# Done",
                        "",
                        "- Title: Done",
                        "- Status: done",
                        "- Related task id(s): `11`",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            matches = policy_module.find_active_execution_plans(root, task_id="11")

        self.assertEqual(["execution-plans/active.md"], matches)


class CheckTddExecutionPlanMainTests(unittest.TestCase):
    def _invoke_main(self, *, root: Path, out_dir: Path, argv: list[str], triplet: _FakeTriplet) -> int:
        out_dir.mkdir(parents=True, exist_ok=True)
        with mock.patch.object(sys, "argv", argv), \
            mock.patch.object(check_script, "repo_root", return_value=root), \
            mock.patch.object(check_script, "ci_dir", return_value=out_dir), \
            mock.patch.object(check_script, "resolve_triplet", return_value=triplet):
            return check_script.main()

    def test_main_warn_policy_should_emit_warning_summary_without_creating_plan(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-03-23" / "sc-tdd-execution-plan"
            argv = [
                "check_tdd_execution_plan.py",
                "--task-id",
                "11",
                "--tdd-stage",
                "red-first",
                "--verify",
                "auto",
                "--execution-plan-policy",
                "warn",
            ]

            rc = self._invoke_main(root=root, out_dir=out_dir, argv=argv, triplet=_FakeTriplet())

            self.assertEqual(0, rc)
            payload = json.loads((out_dir / "summary-11.json").read_text(encoding="utf-8"))
            self.assertEqual("warn", payload["policy"])
            self.assertEqual("warn", payload["decision"])
            self.assertTrue(payload["threshold_hit"])
            self.assertEqual([], payload["active_execution_plans"])
            self.assertEqual("", payload["created_execution_plan"])

    def test_main_draft_policy_should_create_execution_plan_when_threshold_hit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-03-23" / "sc-tdd-execution-plan"
            argv = [
                "check_tdd_execution_plan.py",
                "--task-id",
                "11",
                "--tdd-stage",
                "red-first",
                "--verify",
                "auto",
                "--execution-plan-policy",
                "draft",
            ]

            rc = self._invoke_main(root=root, out_dir=out_dir, argv=argv, triplet=_FakeTriplet())

            self.assertEqual(0, rc)
            payload = json.loads((out_dir / "summary-11.json").read_text(encoding="utf-8"))
            self.assertEqual("draft", payload["decision"])
            self.assertTrue(payload["created_execution_plan"])
            created = root / payload["created_execution_plan"]
            self.assertTrue(created.exists())
            text = created.read_text(encoding="utf-8")
            self.assertIn("- Status: active", text)
            self.assertIn("- Related task id(s): `11`", text)

    def test_main_require_policy_should_fail_without_active_plan(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-03-23" / "sc-tdd-execution-plan"
            argv = [
                "check_tdd_execution_plan.py",
                "--task-id",
                "11",
                "--tdd-stage",
                "red-first",
                "--verify",
                "auto",
                "--execution-plan-policy",
                "require",
            ]

            rc = self._invoke_main(root=root, out_dir=out_dir, argv=argv, triplet=_FakeTriplet())

            self.assertEqual(1, rc)
            payload = json.loads((out_dir / "summary-11.json").read_text(encoding="utf-8"))
            self.assertEqual("require", payload["policy"])
            self.assertEqual("require_failed", payload["decision"])

    def test_main_require_policy_should_pass_when_active_plan_exists(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-03-23" / "sc-tdd-execution-plan"
            plan_dir = root / "execution-plans"
            plan_dir.mkdir(parents=True, exist_ok=True)
            (plan_dir / "2026-03-23-task-11.md").write_text(
                "\n".join(
                    [
                        "# Task 11 Plan",
                        "",
                        "- Title: Task 11 Plan",
                        "- Status: blocked",
                        "- Related task id(s): `11`",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            argv = [
                "check_tdd_execution_plan.py",
                "--task-id",
                "11",
                "--tdd-stage",
                "red-first",
                "--verify",
                "auto",
                "--execution-plan-policy",
                "require",
            ]

            rc = self._invoke_main(root=root, out_dir=out_dir, argv=argv, triplet=_FakeTriplet())

            self.assertEqual(0, rc)
            payload = json.loads((out_dir / "summary-11.json").read_text(encoding="utf-8"))
            self.assertEqual("ok", payload["decision"])
            self.assertEqual(["execution-plans/2026-03-23-task-11.md"], payload["active_execution_plans"])


if __name__ == "__main__":
    unittest.main()
