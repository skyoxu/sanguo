#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from unittest import mock
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON_DIR = REPO_ROOT / "scripts" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))


def _load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


dev_cli = _load_module("dev_cli_module", "scripts/python/dev_cli.py")


class DevCliRecoveryCommandsTests(unittest.TestCase):
    def test_new_execution_plan_should_forward_arguments(self) -> None:
        with mock.patch.object(dev_cli, "run", return_value=0) as run_mock:
            rc = dev_cli.main(
                [
                    "new-execution-plan",
                    "--title",
                    "demo-plan",
                    "--task-id",
                    "7",
                    "--run-id",
                    "abc123",
                    "--latest-json",
                    "logs/ci/2026-03-21/sc-review-pipeline-task-7/latest.json",
                    "--adr",
                    "docs/adr/ADR-0019-godot-security-baseline.md",
                ]
            )
        self.assertEqual(0, rc)
        cmd = run_mock.call_args[0][0]
        self.assertEqual(["py", "-3", "scripts/python/new_execution_plan.py"], cmd[:3])
        self.assertIn("--task-id", cmd)
        self.assertIn("7", cmd)
        self.assertIn("--run-id", cmd)
        self.assertIn("abc123", cmd)
        self.assertIn("--latest-json", cmd)

    def test_new_decision_log_should_forward_arguments(self) -> None:
        with mock.patch.object(dev_cli, "run", return_value=0) as run_mock:
            rc = dev_cli.main(
                [
                    "new-decision-log",
                    "--title",
                    "decision-demo",
                    "--task-id",
                    "5",
                    "--execution-plan",
                    "execution-plans/2026-03-21-demo.md",
                    "--supersedes",
                    "none",
                ]
            )
        self.assertEqual(0, rc)
        cmd = run_mock.call_args[0][0]
        self.assertEqual(["py", "-3", "scripts/python/new_decision_log.py"], cmd[:3])
        self.assertIn("--task-id", cmd)
        self.assertIn("5", cmd)
        self.assertIn("--execution-plan", cmd)
        self.assertIn("execution-plans/2026-03-21-demo.md", cmd)

    def test_resume_task_should_forward_arguments(self) -> None:
        with mock.patch.object(dev_cli, "run", return_value=0) as run_mock:
            rc = dev_cli.main(
                [
                    "resume-task",
                    "--task-id",
                    "7",
                    "--run-id",
                    "abc123",
                    "--latest",
                    "logs/ci/2026-03-21/sc-review-pipeline-task-7/latest.json",
                    "--out-json",
                    "logs/ci/2026-03-21/task-resume/task-7.json",
                    "--out-md",
                    "logs/ci/2026-03-21/task-resume/task-7.md",
                ]
            )
        self.assertEqual(0, rc)
        cmd = run_mock.call_args[0][0]
        self.assertEqual(["py", "-3", "scripts/python/resume_task.py"], cmd[:3])
        self.assertIn("--task-id", cmd)
        self.assertIn("7", cmd)
        self.assertIn("--run-id", cmd)
        self.assertIn("abc123", cmd)
        self.assertIn("--latest", cmd)
        self.assertIn("--out-json", cmd)
        self.assertIn("--out-md", cmd)

    def test_resume_task_should_forward_recommendation_only_flag(self) -> None:
        with mock.patch.object(dev_cli, "run", return_value=0) as run_mock:
            rc = dev_cli.main(
                [
                    "resume-task",
                    "--task-id",
                    "15",
                    "--recommendation-only",
                ]
            )
        self.assertEqual(0, rc)
        cmd = run_mock.call_args[0][0]
        self.assertEqual(["py", "-3", "scripts/python/resume_task.py"], cmd[:3])
        self.assertIn("--task-id", cmd)
        self.assertIn("15", cmd)
        self.assertIn("--recommendation-only", cmd)

    def test_inspect_run_should_forward_recommendation_only_flag(self) -> None:
        with mock.patch.object(dev_cli, "run", return_value=0) as run_mock:
            rc = dev_cli.main(
                [
                    "inspect-run",
                    "--kind",
                    "pipeline",
                    "--task-id",
                    "15",
                    "--recommendation-only",
                ]
            )
        self.assertEqual(0, rc)
        cmd = run_mock.call_args[0][0]
        self.assertEqual(["py", "-3", "scripts/python/inspect_run.py"], cmd[:3])
        self.assertIn("--kind", cmd)
        self.assertIn("pipeline", cmd)
        self.assertIn("--task-id", cmd)
        self.assertIn("15", cmd)
        self.assertIn("--recommendation-only", cmd)

    def test_resume_task_should_forward_recommendation_format(self) -> None:
        with mock.patch.object(dev_cli, "run", return_value=0) as run_mock:
            rc = dev_cli.main(
                [
                    "resume-task",
                    "--task-id",
                    "15",
                    "--recommendation-only",
                    "--recommendation-format",
                    "json",
                ]
            )
        self.assertEqual(0, rc)
        cmd = run_mock.call_args[0][0]
        self.assertIn("--recommendation-format", cmd)
        self.assertIn("json", cmd)

    def test_inspect_run_should_forward_recommendation_format(self) -> None:
        with mock.patch.object(dev_cli, "run", return_value=0) as run_mock:
            rc = dev_cli.main(
                [
                    "inspect-run",
                    "--kind",
                    "pipeline",
                    "--task-id",
                    "15",
                    "--recommendation-only",
                    "--recommendation-format",
                    "json",
                ]
            )
        self.assertEqual(0, rc)
        cmd = run_mock.call_args[0][0]
        self.assertIn("--recommendation-format", cmd)
        self.assertIn("json", cmd)

    def test_chapter6_route_should_forward_recommendation_only_and_record_residual(self) -> None:
        with mock.patch.object(dev_cli, "run", return_value=0) as run_mock:
            rc = dev_cli.main(
                [
                    "chapter6-route",
                    "--task-id",
                    "15",
                    "--recommendation-only",
                    "--recommendation-format",
                    "json",
                    "--record-residual",
                ]
            )
        self.assertEqual(0, rc)
        cmd = run_mock.call_args[0][0]
        self.assertEqual(["py", "-3", "scripts/python/chapter6_route.py"], cmd[:3])
        self.assertIn("--task-id", cmd)
        self.assertIn("15", cmd)
        self.assertIn("--recommendation-only", cmd)
        self.assertIn("--recommendation-format", cmd)
        self.assertIn("json", cmd)
        self.assertIn("--record-residual", cmd)

    def test_run_single_task_chapter6_should_forward_arguments(self) -> None:
        with mock.patch.object(dev_cli, "run", return_value=0) as run_mock:
            rc = dev_cli.main(
                [
                    "run-single-task-chapter6",
                    "--task-id",
                    "15",
                    "--godot-bin",
                    "C:/Godot/Godot.exe",
                    "--delivery-profile",
                    "standard",
                    "--fix-through",
                    "P2",
                    "--out-dir",
                    "logs/ci/demo/chapter6-task-15",
                ]
            )

        self.assertEqual(0, rc)
        cmd = run_mock.call_args[0][0]
        self.assertEqual(["py", "-3", "scripts/python/run_single_task_chapter6_lane.py"], cmd[:3])
        self.assertIn("--task-id", cmd)
        self.assertIn("15", cmd)
        self.assertIn("--godot-bin", cmd)
        self.assertIn("C:/Godot/Godot.exe", cmd)
        self.assertIn("--delivery-profile", cmd)
        self.assertIn("standard", cmd)
        self.assertIn("--fix-through", cmd)
        self.assertIn("P2", cmd)
        self.assertIn("--out-dir", cmd)


if __name__ == "__main__":
    unittest.main()
