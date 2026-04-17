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
                "preferred_lane": "inspect-first",
                "run_id": "n/a",
                "latest_reason": "n/a",
                "blocked_by": "n/a",
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

    def test_decision_should_stop_initial_phase_when_route_requests_run_67_recovery(self) -> None:
        decision = lane.build_orchestration_decision(
            initial_route={
                "preferred_lane": "run-6.7",
                "run_id": "run-15",
                "latest_reason": "step_failed:sc-test",
                "blocked_by": "",
            },
            post_review_route={"preferred_lane": "inspect-first"},
            final_route={"preferred_lane": "inspect-first"},
        )

        self.assertEqual("blocked", decision["initial_phase"]["action"])
        self.assertEqual("run-6.7", decision["initial_phase"]["stop_reason"])

    def test_decision_should_complete_when_next_action_is_continue_even_if_lane_is_inspect_first(self) -> None:
        decision = lane.build_orchestration_decision(
            initial_route={
                "preferred_lane": "inspect-first",
                "run_id": "run-15",
                "latest_reason": "pipeline_clean",
                "blocked_by": "",
                "chapter6_next_action": "continue",
            },
            post_review_route={"preferred_lane": "inspect-first"},
            final_route={"preferred_lane": "inspect-first"},
        )

        self.assertEqual("complete", decision["initial_phase"]["action"])
        self.assertEqual("continue", decision["initial_phase"]["stop_reason"])

    def test_decision_should_stop_initial_phase_when_next_action_requests_resume(self) -> None:
        decision = lane.build_orchestration_decision(
            initial_route={
                "preferred_lane": "inspect-first",
                "run_id": "run-15",
                "latest_reason": "review_pending",
                "blocked_by": "",
                "chapter6_next_action": "resume",
            },
            post_review_route={"preferred_lane": "inspect-first"},
            final_route={"preferred_lane": "inspect-first"},
        )

        self.assertEqual("blocked", decision["initial_phase"]["action"])
        self.assertEqual("resume", decision["initial_phase"]["stop_reason"])

    def test_decision_should_stop_initial_phase_when_next_action_requests_pause(self) -> None:
        decision = lane.build_orchestration_decision(
            initial_route={
                "preferred_lane": "inspect-first",
                "run_id": "run-15",
                "latest_reason": "review_pending",
                "blocked_by": "",
                "chapter6_next_action": "pause",
            },
            post_review_route={"preferred_lane": "inspect-first"},
            final_route={"preferred_lane": "inspect-first"},
        )

        self.assertEqual("blocked", decision["initial_phase"]["action"])
        self.assertEqual("pause", decision["initial_phase"]["stop_reason"])

    def test_decision_should_stop_initial_phase_when_next_action_requests_inspect(self) -> None:
        decision = lane.build_orchestration_decision(
            initial_route={
                "preferred_lane": "inspect-first",
                "run_id": "run-15",
                "latest_reason": "review_pending",
                "blocked_by": "",
                "chapter6_next_action": "inspect",
            },
            post_review_route={"preferred_lane": "inspect-first"},
            final_route={"preferred_lane": "inspect-first"},
        )

        self.assertEqual("blocked", decision["initial_phase"]["action"])
        self.assertEqual("inspect", decision["initial_phase"]["stop_reason"])

    def test_decision_should_stop_initial_phase_when_next_action_requests_rerun(self) -> None:
        decision = lane.build_orchestration_decision(
            initial_route={
                "preferred_lane": "inspect-first",
                "run_id": "run-15",
                "latest_reason": "review_pending",
                "blocked_by": "",
                "chapter6_next_action": "rerun",
            },
            post_review_route={"preferred_lane": "inspect-first"},
            final_route={"preferred_lane": "inspect-first"},
        )

        self.assertEqual("blocked", decision["initial_phase"]["action"])
        self.assertEqual("rerun", decision["initial_phase"]["stop_reason"])

    def test_decision_should_prioritize_needs_fix_next_action_over_inspect_first_lane(self) -> None:
        decision = lane.build_orchestration_decision(
            initial_route={
                "preferred_lane": "inspect-first",
                "run_id": "run-15",
                "latest_reason": "rerun_blocked:deterministic_green_llm_not_clean",
                "blocked_by": "rerun_guard",
                "chapter6_next_action": "needs-fix-fast",
            },
            post_review_route={"preferred_lane": "inspect-first"},
            final_route={"preferred_lane": "inspect-first"},
        )

        self.assertEqual("needs-fix-fast", decision["initial_phase"]["action"])
        self.assertEqual("", decision["initial_phase"]["stop_reason"])

    def test_decision_should_map_fix_and_resume_next_action_to_fix_deterministic(self) -> None:
        decision = lane.build_orchestration_decision(
            initial_route={
                "preferred_lane": "inspect-first",
                "run_id": "run-15",
                "latest_reason": "step_failed:sc-test",
                "blocked_by": "deterministic_failure",
                "chapter6_next_action": "fix-and-resume",
            },
            post_review_route={"preferred_lane": "inspect-first"},
            final_route={"preferred_lane": "inspect-first"},
        )

        self.assertEqual("blocked", decision["initial_phase"]["action"])
        self.assertEqual("fix-deterministic", decision["initial_phase"]["stop_reason"])

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

    def test_command_is_forbidden_should_match_prefix_for_review_pipeline_fork(self) -> None:
        cmd = lane.build_review_pipeline_fork_cmd(
            "15",
            profile_policy=lane.resolve_profile_policy("fast-ship"),
            godot_bin="C:/Godot/Godot.exe",
        )
        route_payload = {
            "forbidden_commands": "py -3 scripts/sc/run_review_pipeline.py --task-id 15 --fork | py -3 scripts/sc/run_review_pipeline.py --task-id 15 --resume"
        }

        self.assertTrue(lane._command_is_forbidden(route_payload, cmd))

    def test_parse_json_stdout_should_extract_object_after_bracketed_log_prefix(self) -> None:
        stdout = 'INFO [retry] waiting for response\n{"k": 2, "v": "ok"}\n'

        payload = lane._parse_json_stdout(stdout)

        self.assertEqual({"k": 2, "v": "ok"}, payload)

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

    def test_decision_should_block_initial_phase_for_pending_fork_approval_compact_payload(self) -> None:
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
                "approval_required_action": "fork",
                "approval_status": "pending",
                "approval_allowed_actions": "inspect | pause",
                "approval_blocked_actions": "fork | resume | rerun",
            },
        )

        self.assertEqual("blocked", decision["initial_phase"]["action"])
        self.assertEqual("approval_pending", decision["initial_phase"]["stop_reason"])

    def test_decision_should_defer_to_route_when_fork_approval_was_denied(self) -> None:
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

        self.assertEqual("blocked", decision["initial_phase"]["action"])
        self.assertEqual("run-6.7", decision["initial_phase"]["stop_reason"])

    def test_decision_should_enter_fork_when_approval_is_approved(self) -> None:
        decision = lane.build_orchestration_decision(
            initial_route={
                "preferred_lane": "inspect-first",
                "run_id": "run-15",
                "latest_reason": "pipeline_clean",
                "blocked_by": "approval_approved",
                "chapter6_next_action": "fork",
            },
            post_review_route={"preferred_lane": "inspect-first"},
            final_route={"preferred_lane": "inspect-first"},
            resume_payload={
                "approval": {
                    "required_action": "fork",
                    "status": "approved",
                    "allowed_actions": ["fork", "inspect"],
                    "blocked_actions": ["resume", "rerun"],
                }
            },
        )

        self.assertEqual("fork", decision["initial_phase"]["action"])
        self.assertEqual("fork", decision["initial_phase"]["stop_reason"])

    def test_decision_should_enter_fork_when_compact_payload_reports_approval_approved(self) -> None:
        decision = lane.build_orchestration_decision(
            initial_route={
                "preferred_lane": "inspect-first",
                "run_id": "run-15",
                "latest_reason": "pipeline_clean",
                "blocked_by": "approval_approved",
                "chapter6_next_action": "fork",
            },
            post_review_route={"preferred_lane": "inspect-first"},
            final_route={"preferred_lane": "inspect-first"},
            resume_payload={
                "approval_required_action": "fork",
                "approval_status": "approved",
                "approval_allowed_actions": "fork | inspect",
                "approval_blocked_actions": "resume | rerun",
            },
        )

        self.assertEqual("fork", decision["initial_phase"]["action"])
        self.assertEqual("fork", decision["initial_phase"]["stop_reason"])

    def test_decision_should_complete_when_approval_is_approved_and_next_action_is_continue(self) -> None:
        decision = lane.build_orchestration_decision(
            initial_route={
                "preferred_lane": "inspect-first",
                "run_id": "run-15",
                "latest_reason": "pipeline_clean",
                "blocked_by": "approval_approved",
                "chapter6_next_action": "continue",
            },
            post_review_route={"preferred_lane": "inspect-first"},
            final_route={"preferred_lane": "inspect-first"},
            resume_payload={
                "approval": {
                    "required_action": "fork",
                    "status": "approved",
                    "allowed_actions": ["fork", "inspect"],
                    "blocked_actions": ["resume", "rerun"],
                }
            },
        )

        self.assertEqual("complete", decision["initial_phase"]["action"])
        self.assertEqual("continue", decision["initial_phase"]["stop_reason"])

    def test_plan_should_stop_after_run_67_recovery_signal(self) -> None:
        initial_route = {
            "preferred_lane": "run-6.7",
            "run_id": "run-15",
            "latest_reason": "step_failed:sc-test",
            "blocked_by": "",
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
        self.assertEqual("run-6.7", plan["stop_reason"])

    def test_plan_should_complete_when_next_action_is_continue(self) -> None:
        initial_route = {
            "preferred_lane": "inspect-first",
            "run_id": "run-15",
            "latest_reason": "pipeline_clean",
            "blocked_by": "",
            "chapter6_next_action": "continue",
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
        self.assertEqual("complete", plan["status"])
        self.assertEqual("continue", plan["stop_reason"])

    def test_plan_should_run_needs_fix_fast_when_next_action_requests_it_even_if_lane_is_inspect_first(self) -> None:
        initial_route = {
            "preferred_lane": "inspect-first",
            "run_id": "run-15",
            "latest_reason": "rerun_blocked:deterministic_green_llm_not_clean",
            "blocked_by": "rerun_guard",
            "chapter6_next_action": "needs-fix-fast",
        }

        plan = lane.build_execution_plan(
            task_id="15",
            godot_bin="C:/Godot/Godot.exe",
            profile_policy=lane.resolve_profile_policy("fast-ship"),
            initial_route=initial_route,
            post_review_route={"preferred_lane": "inspect-first"},
            final_route={"preferred_lane": "inspect-first"},
        )

        self.assertEqual("planned", plan["status"])
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

    def test_plan_should_use_resume_next_action_when_initial_route_omits_chapter6_next_action(self) -> None:
        initial_route = {
            "preferred_lane": "inspect-first",
            "run_id": "run-15",
            "latest_reason": "pipeline_clean",
            "blocked_by": "",
        }

        plan = lane.build_execution_plan(
            task_id="15",
            godot_bin="C:/Godot/Godot.exe",
            profile_policy=lane.resolve_profile_policy("fast-ship"),
            initial_route=initial_route,
            post_review_route={"preferred_lane": "inspect-first"},
            final_route={"preferred_lane": "inspect-first"},
            resume_payload={
                "chapter6_next_action": "continue",
                "blocked_by": "n/a",
            },
        )

        self.assertEqual("complete", plan["status"])
        self.assertEqual("continue", plan["stop_reason"])
        self.assertEqual(["resume-task", "chapter6-route-initial"], [step["name"] for step in plan["steps"]])

    def test_plan_should_run_fork_lane_when_approval_is_approved(self) -> None:
        initial_route = {
            "preferred_lane": "inspect-first",
            "run_id": "run-15",
            "latest_reason": "pipeline_clean",
            "blocked_by": "approval_approved",
            "chapter6_next_action": "fork",
            "forbidden_commands": [],
        }

        plan = lane.build_execution_plan(
            task_id="15",
            godot_bin="C:/Godot/Godot.exe",
            profile_policy=lane.resolve_profile_policy("fast-ship"),
            initial_route=initial_route,
            post_review_route={"preferred_lane": "inspect-first"},
            final_route={"preferred_lane": "inspect-first"},
            resume_payload={
                "approval": {
                    "required_action": "fork",
                    "status": "approved",
                    "allowed_actions": ["fork", "inspect"],
                    "blocked_actions": ["resume", "rerun"],
                }
            },
        )

        self.assertEqual("planned", plan["status"])
        self.assertEqual(
            [
                "resume-task",
                "chapter6-route-initial",
                "review-pipeline-fork",
                "chapter6-route-post-review",
                "local-hard-checks-preflight",
                "local-hard-checks",
                "inspect-local-hard-checks",
            ],
            [step["name"] for step in plan["steps"]],
        )
        fork_cmd = plan["steps"][2]["cmd"]
        self.assertEqual("scripts/sc/run_review_pipeline.py", fork_cmd[2])
        self.assertIn("--fork", fork_cmd)

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

    def test_main_should_fallback_to_full_path_when_resume_and_route_have_no_latest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "chapter6-fresh-start"
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
                            "rc": 2,
                            "stdout_tail": "ERROR: failed to build task resume summary: No latest run index found.",
                            "stderr_tail": "",
                            "log": "resume.log",
                        },
                        {},
                    ),
                    (
                        {
                            "name": "chapter6-route-initial",
                            "cmd": [],
                            "rc": 2,
                            "stdout_tail": "ERROR: failed to route chapter6 recovery: No latest run index found.",
                            "stderr_tail": "",
                            "log": "route-initial.log",
                        },
                        {},
                    ),
                    (
                        {
                            "name": "chapter6-route-post-review",
                            "cmd": [],
                            "rc": 0,
                            "stdout_tail": "",
                            "stderr_tail": "",
                            "log": "route-post-review.log",
                        },
                        {
                            "preferred_lane": "inspect-first",
                            "run_id": "run-15",
                            "latest_reason": "pipeline_clean",
                            "blocked_by": "",
                            "chapter6_next_action": "continue",
                            "forbidden_commands": [],
                        },
                    ),
                    (
                        {
                            "name": "inspect-local-hard-checks",
                            "cmd": [],
                            "rc": 0,
                            "stdout_tail": "",
                            "stderr_tail": "",
                            "log": "inspect-local-hard-checks.log",
                        },
                        {"recommended_action": "continue"},
                    ),
                ]
            )

            def fake_run_json_step(*_args, **_kwargs):
                return next(json_steps)

            def fake_run_plain_step(*_args, name, cmd, **_kwargs):
                step_name = str(name)
                executed_steps.append(step_name)
                return {
                    "name": step_name,
                    "cmd": list(cmd),
                    "rc": 0,
                    "stdout_tail": "",
                    "stderr_tail": "",
                    "log": f"{step_name}.log",
                }

            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(lane, "_repo_root", return_value=root),
                mock.patch.object(lane, "_run_json_step", side_effect=fake_run_json_step),
                mock.patch.object(lane, "_run_plain_step", side_effect=fake_run_plain_step),
            ):
                rc = lane.main()

            self.assertEqual(0, rc)
            self.assertEqual(
                [
                    "check-tdd-plan",
                    "red-first",
                    "green",
                    "refactor",
                    "review-pipeline",
                    "local-hard-checks-preflight",
                    "local-hard-checks",
                ],
                executed_steps,
            )
            payload = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("ok", payload["status"])
            self.assertEqual("fresh-start-no-latest", payload["resume_recovery_mode"])
            self.assertEqual("fresh-start-no-latest", payload["route_recovery_mode"])

    def test_main_should_stop_early_when_route_requests_run_67_recovery(self) -> None:
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
                            "forbidden_commands": [],
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
            self.assertEqual("run-6.7", payload["stop_reason"])

    def test_main_should_finish_cleanly_when_next_action_is_continue(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "chapter6-continue"
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
                            "preferred_lane": "inspect-first",
                            "run_id": "run-15",
                            "latest_reason": "pipeline_clean",
                            "blocked_by": "",
                            "chapter6_next_action": "continue",
                            "forbidden_commands": [],
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

            self.assertEqual(0, rc)
            self.assertEqual([], executed_steps)
            payload = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("complete", payload["status"])
            self.assertEqual("continue", payload["stop_reason"])

    def test_main_should_execute_fork_lane_when_approval_is_approved(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "chapter6-fork-approved"
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
            executed_cmds: dict[str, list[str]] = {}
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
                            "approval": {
                                "required_action": "fork",
                                "status": "approved",
                                "allowed_actions": ["fork", "inspect"],
                                "blocked_actions": ["resume", "rerun"],
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
                            "preferred_lane": "inspect-first",
                            "run_id": "run-15",
                            "latest_reason": "pipeline_clean",
                            "blocked_by": "approval_approved",
                            "chapter6_next_action": "fork",
                            "forbidden_commands": [],
                        },
                    ),
                    (
                        {
                            "name": "chapter6-route-post-review",
                            "cmd": [],
                            "rc": 0,
                            "stdout_tail": "",
                            "stderr_tail": "",
                            "log": "route-post-review.log",
                        },
                        {
                            "preferred_lane": "inspect-first",
                            "run_id": "run-15",
                            "latest_reason": "pipeline_clean",
                            "blocked_by": "",
                            "chapter6_next_action": "continue",
                            "forbidden_commands": [],
                        },
                    ),
                    (
                        {
                            "name": "inspect-local-hard-checks",
                            "cmd": [],
                            "rc": 0,
                            "stdout_tail": "",
                            "stderr_tail": "",
                            "log": "inspect-local-hard-checks.log",
                        },
                        {"recommended_action": "continue"},
                    ),
                ]
            )

            def fake_run_json_step(*_args, **_kwargs):
                return next(json_steps)

            def fake_run_plain_step(*_args, name, cmd, **_kwargs):
                step_name = str(name)
                executed_steps.append(step_name)
                executed_cmds[step_name] = list(cmd)
                return {
                    "name": step_name,
                    "cmd": list(cmd),
                    "rc": 0,
                    "stdout_tail": "",
                    "stderr_tail": "",
                    "log": f"{step_name}.log",
                }

            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(lane, "_repo_root", return_value=root),
                mock.patch.object(lane, "_run_json_step", side_effect=fake_run_json_step),
                mock.patch.object(lane, "_run_plain_step", side_effect=fake_run_plain_step),
            ):
                rc = lane.main()

            self.assertEqual(0, rc)
            self.assertEqual(
                ["review-pipeline-fork", "local-hard-checks-preflight", "local-hard-checks"],
                executed_steps,
            )
            self.assertIn("--fork", executed_cmds["review-pipeline-fork"])
            payload = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("ok", payload["status"])

    def test_main_should_block_fork_when_forbidden_command_matches_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "chapter6-fork-forbidden"
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
                            "approval": {
                                "required_action": "fork",
                                "status": "approved",
                                "allowed_actions": ["fork", "inspect"],
                                "blocked_actions": ["resume", "rerun"],
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
                            "preferred_lane": "inspect-first",
                            "run_id": "run-15",
                            "latest_reason": "pipeline_clean",
                            "blocked_by": "approval_approved",
                            "chapter6_next_action": "fork",
                            "forbidden_commands": "py -3 scripts/sc/run_review_pipeline.py --task-id 15 --fork",
                        },
                    ),
                    (
                        {
                            "name": "chapter6-route-post-review",
                            "cmd": [],
                            "rc": 0,
                            "stdout_tail": "",
                            "stderr_tail": "",
                            "log": "route-post-review.log",
                        },
                        {
                            "preferred_lane": "inspect-first",
                            "run_id": "run-15",
                            "latest_reason": "pipeline_clean",
                            "blocked_by": "",
                            "chapter6_next_action": "continue",
                            "forbidden_commands": [],
                        },
                    ),
                    (
                        {
                            "name": "inspect-local-hard-checks",
                            "cmd": [],
                            "rc": 0,
                            "stdout_tail": "",
                            "stderr_tail": "",
                            "log": "inspect-local-hard-checks.log",
                        },
                        {"recommended_action": "continue"},
                    ),
                ]
            )

            def fake_run_json_step(*_args, **_kwargs):
                return next(json_steps)

            def fake_run_plain_step(*_args, name, cmd, **_kwargs):
                executed_steps.append(str(name))
                return {
                    "name": str(name),
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
            self.assertEqual("forbidden-command:review-pipeline-fork", payload["stop_reason"])

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
