#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


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


lane = _load_module("single_task_chapter6_lane_module", "scripts/python/run_single_task_chapter6_lane.py")


class RunSingleTaskChapter6LaneTests(unittest.TestCase):
    def test_resolve_profile_policy_should_default_to_p0_for_playable_ea(self) -> None:
        policy = lane.resolve_profile_policy("playable-ea")

        self.assertEqual("playable-ea", policy["delivery_profile"])
        self.assertEqual("host-safe", policy["security_profile"])
        self.assertEqual("P0", policy["fix_through"])
        self.assertEqual("warn", policy["execution_plan_policy"])
        self.assertEqual("unit", policy["red_verify"])

    def test_resolve_profile_policy_should_default_to_p1_for_standard(self) -> None:
        policy = lane.resolve_profile_policy("standard")

        self.assertEqual("standard", policy["delivery_profile"])
        self.assertEqual("strict", policy["security_profile"])
        self.assertEqual("P1", policy["fix_through"])
        self.assertEqual("draft", policy["execution_plan_policy"])
        self.assertEqual("auto", policy["red_verify"])

    def test_plan_should_run_full_lane_when_initial_route_has_no_real_recovery_bundle(self) -> None:
        initial_route = {
            "preferred_lane": "inspect-first",
            "run_id": "n/a",
            "latest_reason": "n/a",
            "blocked_by": "n/a",
        }

        plan = lane.build_execution_plan(
            task_id="15",
            godot_bin="C:/Godot/Godot.exe",
            profile_policy=lane.resolve_profile_policy("fast-ship"),
            initial_route=initial_route,
            post_review_route={"preferred_lane": "inspect-first"},
            final_route={"preferred_lane": "inspect-first"},
        )

        self.assertEqual(
            [
                "resume-task",
                "chapter6-route-initial",
                "check-tdd-plan",
                "red-first",
                "green",
                "refactor",
                "review-pipeline",
                "chapter6-route-post-review",
                "local-hard-checks-preflight",
                "local-hard-checks",
                "inspect-local-hard-checks",
            ],
            [step["name"] for step in plan["steps"]],
        )

    def test_plan_should_jump_to_68_when_initial_route_requires_targeted_closure(self) -> None:
        initial_route = {
            "preferred_lane": "run-6.8",
            "run_id": "run-15",
            "latest_reason": "rerun_blocked:repeat_review_needs_fix",
            "blocked_by": "rerun_guard",
        }

        plan = lane.build_execution_plan(
            task_id="15",
            godot_bin="C:/Godot/Godot.exe",
            profile_policy=lane.resolve_profile_policy("fast-ship"),
            initial_route=initial_route,
            post_review_route={"preferred_lane": "inspect-first"},
            final_route={"preferred_lane": "inspect-first"},
        )

        self.assertEqual(
            [
                "resume-task",
                "chapter6-route-initial",
                "needs-fix-fast",
                "chapter6-route-post-needs-fix",
                "local-hard-checks-preflight",
                "local-hard-checks",
                "inspect-local-hard-checks",
            ],
            [step["name"] for step in plan["steps"]],
        )

    def test_plan_should_stop_after_repo_noise_signal(self) -> None:
        initial_route = {
            "preferred_lane": "repo-noise-stop",
            "run_id": "run-15",
            "latest_reason": "step_failed:sc-test",
            "blocked_by": "recent_failure_summary",
        }

        plan = lane.build_execution_plan(
            task_id="15",
            godot_bin="C:/Godot/Godot.exe",
            profile_policy=lane.resolve_profile_policy("fast-ship"),
            initial_route=initial_route,
            post_review_route={"preferred_lane": "inspect-first"},
            final_route={"preferred_lane": "inspect-first"},
        )

        self.assertEqual(["resume-task", "chapter6-route-initial"], [step["name"] for step in plan["steps"]])
        self.assertEqual("blocked", plan["status"])
        self.assertEqual("repo-noise-stop", plan["stop_reason"])

    def test_route_command_should_record_residual_by_default_for_p1_policy(self) -> None:
        cmd = lane.build_chapter6_route_cmd(task_id="15", record_residual=True)

        self.assertEqual(["py", "-3", "scripts/python/dev_cli.py"], cmd[:3])
        self.assertIn("chapter6-route", cmd)
        self.assertIn("--record-residual", cmd)
        self.assertIn("--recommendation-only", cmd)
        self.assertIn("--recommendation-format", cmd)
        self.assertIn("json", cmd)

    def test_main_self_check_should_write_summary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "chapter6-self-check"
            argv = [
                "run_single_task_chapter6_lane.py",
                "--task-id",
                "15",
                "--godot-bin",
                "C:/Godot/Godot.exe",
                "--delivery-profile",
                "fast-ship",
                "--self-check",
                "--out-dir",
                str(out_dir),
            ]
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(lane, "_repo_root", return_value=root),
            ):
                rc = lane.main()

            self.assertEqual(0, rc)
            payload = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("ok", payload["status"])
            self.assertEqual("P1", payload["profile_policy"]["fix_through"])
            self.assertEqual("check-tdd-plan", payload["steps"][2]["name"])


if __name__ == "__main__":
    unittest.main()
