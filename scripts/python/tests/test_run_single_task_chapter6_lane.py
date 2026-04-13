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

    def test_plan_should_stop_after_inspect_first_signal(self) -> None:
        initial_route = {
            "preferred_lane": "inspect-first",
            "run_id": "run-15",
            "latest_reason": "planned_only_incomplete",
            "blocked_by": "artifact_integrity",
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
        self.assertEqual("artifact-integrity", plan["stop_reason"])

    def test_plan_should_stop_after_record_residual_signal(self) -> None:
        initial_route = {
            "preferred_lane": "record-residual",
            "run_id": "run-15",
            "latest_reason": "rerun_blocked:repeat_review_needs_fix",
            "blocked_by": "waste_signals",
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
        self.assertEqual("record-residual", plan["stop_reason"])

    def test_plan_should_stop_on_artifact_integrity_even_when_lane_is_run_67(self) -> None:
        initial_route = {
            "preferred_lane": "run-6.7",
            "run_id": "run-15",
            "latest_reason": "planned_only_incomplete",
            "blocked_by": "artifact_integrity",
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
        self.assertEqual("artifact-integrity", plan["stop_reason"])

    def test_route_command_should_record_residual_by_default_for_p1_policy(self) -> None:
        cmd = lane.build_chapter6_route_cmd(task_id="15", record_residual=True)

        self.assertEqual(["py", "-3", "scripts/python/dev_cli.py"], cmd[:3])
        self.assertIn("chapter6-route", cmd)
        self.assertIn("--record-residual", cmd)
        self.assertIn("--recommendation-only", cmd)
        self.assertIn("--recommendation-format", cmd)
        self.assertIn("json", cmd)

    def test_decision_should_block_initial_phase_for_artifact_integrity(self) -> None:
        decision = lane.build_orchestration_decision(
            initial_route={
                "preferred_lane": "inspect-first",
                "run_id": "run-15",
                "latest_reason": "planned_only_incomplete",
                "blocked_by": "artifact_integrity",
            },
            post_review_route={"preferred_lane": "inspect-first"},
            final_route={"preferred_lane": "inspect-first"},
        )

        self.assertEqual("blocked", decision["initial_phase"]["action"])
        self.assertEqual("artifact-integrity", decision["initial_phase"]["stop_reason"])

    def test_decision_should_require_needs_fix_after_post_review_run_68(self) -> None:
        decision = lane.build_orchestration_decision(
            initial_route={
                "preferred_lane": "run-6.7",
                "run_id": "run-15",
                "latest_reason": "step_failed:sc-test",
                "blocked_by": "",
            },
            post_review_route={
                "preferred_lane": "run-6.8",
                "run_id": "run-15",
                "latest_reason": "rerun_blocked:repeat_review_needs_fix",
                "blocked_by": "rerun_guard",
            },
            final_route={"preferred_lane": "inspect-first"},
        )

        self.assertEqual("full-path", decision["initial_phase"]["action"])
        self.assertEqual("needs-fix-fast", decision["post_review_phase"]["action"])

    def test_decision_should_stop_initial_phase_when_needs_fix_path_has_no_increment(self) -> None:
        decision = lane.build_orchestration_decision(
            initial_route={
                "preferred_lane": "run-6.8",
                "run_id": "run-15",
                "latest_reason": "rerun_blocked:repeat_review_needs_fix",
                "blocked_by": "rerun_guard",
            },
            post_review_route={"preferred_lane": "inspect-first"},
            final_route={"preferred_lane": "inspect-first"},
            resume_payload={
                "recommended_action": "needs-fix-fast",
                "run_event_summary": {
                    "turn_count": 3,
                    "new_reviewers": [],
                    "new_sidecars": [],
                    "approval_changed": False,
                },
            },
        )

        self.assertEqual("blocked", decision["initial_phase"]["action"])
        self.assertEqual("record-residual", decision["initial_phase"]["stop_reason"])

    def test_decision_should_block_initial_phase_for_pending_fork_approval(self) -> None:
        decision = lane.build_orchestration_decision(
            initial_route={
                "preferred_lane": "run-6.7",
                "run_id": "run-15",
                "latest_reason": "step_failed:sc-test",
                "blocked_by": "",
            },
            post_review_route={"preferred_lane": "inspect-first"},
            final_route={"preferred_lane": "inspect-first"},
            resume_payload={
                "approval": {
                    "required_action": "fork",
                    "status": "pending",
                    "allowed_actions": ["inspect", "pause"],
                    "blocked_actions": ["fork", "resume", "rerun"],
                }
            },
        )

        self.assertEqual("blocked", decision["initial_phase"]["action"])
        self.assertEqual("approval_pending", decision["initial_phase"]["stop_reason"])

    def test_decision_should_allow_initial_phase_when_fork_approval_was_denied(self) -> None:
        decision = lane.build_orchestration_decision(
            initial_route={
                "preferred_lane": "run-6.7",
                "run_id": "run-15",
                "latest_reason": "step_failed:sc-test",
                "blocked_by": "approval_denied",
            },
            post_review_route={"preferred_lane": "inspect-first"},
            final_route={"preferred_lane": "inspect-first"},
            resume_payload={
                "approval": {
                    "required_action": "fork",
                    "status": "denied",
                    "recommended_action": "resume",
                    "allowed_actions": ["resume", "inspect"],
                    "blocked_actions": ["fork"],
                }
            },
        )

        self.assertEqual("full-path", decision["initial_phase"]["action"])

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

    def test_main_should_stop_before_running_forbidden_review_pipeline_command(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "chapter6-forbidden"
            argv = [
                "run_single_task_chapter6_lane.py",
                "--task-id",
                "15",
                "--godot-bin",
                "C:/Godot/Godot.exe",
                "--delivery-profile",
                "fast-ship",
                "--out-dir",
                str(out_dir),
            ]
            review_cmd = lane.build_review_pipeline_cmd(
                "15",
                profile_policy=lane.resolve_profile_policy("fast-ship"),
                godot_bin="C:/Godot/Godot.exe",
            )
            executed_steps: list[str] = []

            json_steps = iter(
                [
                    (
                        {
                            "name": "resume-task",
                            "cmd": [],
                            "rc": 0,
                            "stdout_tail": "",
                            "stderr_tail": "",
                            "log": "resume.log",
                        },
                        {"task_id": "15", "recommended_action": "continue"},
                    ),
                    (
                        {
                            "name": "chapter6-route-initial",
                            "cmd": [],
                            "rc": 0,
                            "stdout_tail": "",
                            "stderr_tail": "",
                            "log": "route-initial.log",
                        },
                        {
                            "preferred_lane": "run-6.7",
                            "run_id": "run-15",
                            "latest_reason": "step_failed:sc-test",
                            "blocked_by": "",
                            "forbidden_commands": [" ".join(review_cmd)],
                        },
                    ),
                ]
            )

            def fake_run_json_step(*_args, **_kwargs):
                return next(json_steps)

            def fake_run_plain_step(*_args, name, cmd, **_kwargs):
                executed_steps.append(str(name))
                return {
                    "name": name,
                    "cmd": list(cmd),
                    "rc": 0,
                    "stdout_tail": "",
                    "stderr_tail": "",
                    "log": f"{name}.log",
                }

            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(lane, "_repo_root", return_value=root),
                mock.patch.object(lane, "_run_json_step", side_effect=fake_run_json_step),
                mock.patch.object(lane, "_run_plain_step", side_effect=fake_run_plain_step),
            ):
                rc = lane.main()

            self.assertEqual(1, rc)
            self.assertEqual(["check-tdd-plan", "red-first", "green", "refactor"], executed_steps)
            payload = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("blocked", payload["status"])
            self.assertEqual("forbidden-command:review-pipeline", payload["stop_reason"])

    def test_main_should_stop_before_expensive_steps_when_no_increment_converged(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "chapter6-no-increment"
            argv = [
                "run_single_task_chapter6_lane.py",
                "--task-id",
                "15",
                "--godot-bin",
                "C:/Godot/Godot.exe",
                "--delivery-profile",
                "fast-ship",
                "--out-dir",
                str(out_dir),
            ]
            executed_steps: list[str] = []
            json_steps = iter(
                [
                    (
                        {
                            "name": "resume-task",
                            "cmd": [],
                            "rc": 0,
                            "stdout_tail": "",
                            "stderr_tail": "",
                            "log": "resume.log",
                        },
                        {
                            "task_id": "15",
                            "recommended_action": "needs-fix-fast",
                            "run_event_summary": {
                                "turn_count": 3,
                                "new_reviewers": [],
                                "new_sidecars": [],
                                "approval_changed": False,
                            },
                        },
                    ),
                    (
                        {
                            "name": "chapter6-route-initial",
                            "cmd": [],
                            "rc": 0,
                            "stdout_tail": "",
                            "stderr_tail": "",
                            "log": "route-initial.log",
                        },
                        {
                            "preferred_lane": "run-6.8",
                            "run_id": "run-15",
                            "latest_reason": "rerun_blocked:repeat_review_needs_fix",
                            "blocked_by": "rerun_guard",
                        },
                    ),
                ]
            )

            def fake_run_json_step(*_args, **_kwargs):
                return next(json_steps)

            def fake_run_plain_step(*_args, name, cmd, **_kwargs):
                executed_steps.append(str(name))
                return {
                    "name": name,
                    "cmd": list(cmd),
                    "rc": 0,
                    "stdout_tail": "",
                    "stderr_tail": "",
                    "log": f"{name}.log",
                }

            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(lane, "_repo_root", return_value=root),
                mock.patch.object(lane, "_run_json_step", side_effect=fake_run_json_step),
                mock.patch.object(lane, "_run_plain_step", side_effect=fake_run_plain_step),
            ):
                rc = lane.main()

            self.assertEqual(1, rc)
            self.assertEqual([], executed_steps)
            payload = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("blocked", payload["status"])
            self.assertEqual("record-residual", payload["stop_reason"])


if __name__ == "__main__":
    unittest.main()
