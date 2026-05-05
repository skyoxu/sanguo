#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "sc" / "run_review_pipeline.py"
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

import run_review_pipeline as run_review_pipeline_module  # noqa: E402
from _artifact_schema import validate_pipeline_latest_index_payload  # noqa: E402
from _taskmaster import TaskmasterTriplet  # noqa: E402


def _stable_env() -> dict[str, str]:
    env = dict(os.environ)
    for key in ("DELIVERY_PROFILE", "SECURITY_PROFILE", "SC_PIPELINE_RUN_ID", "SC_TEST_RUN_ID", "SC_ACCEPTANCE_RUN_ID"):
        env.pop(key, None)
    return env


class RunReviewPipelinePreflightTests(unittest.TestCase):
    def _triplet(self) -> TaskmasterTriplet:
        return TaskmasterTriplet(
            task_id="56",
            master={"id": "56", "title": "Task 56"},
            back={"test_refs": ["Game.Core.Tests/Tasks/Task0056AcceptanceTests.cs"]},
            gameplay=None,
            tasks_json_path=".taskmaster/tasks/tasks.json",
            tasks_back_path=".taskmaster/tasks/tasks_back.json",
            tasks_gameplay_path=".taskmaster/tasks/tasks_gameplay.json",
            taskdoc_path=None,
        )

    def test_preflight_failure_should_stop_before_sc_test(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-56-{run_id}"
            latest_path = tmp_root / "sc-review-pipeline-task-56" / "latest.json"
            calls: list[tuple[str, list[str]]] = []

            def fake_run_step(*, out_dir: Path, name: str, cmd: list[str], timeout_sec: int) -> dict:
                calls.append((name, cmd))
                if name == "sc-acceptance-preflight":
                    return {
                        "name": name,
                        "cmd": cmd,
                        "rc": 1,
                        "status": "fail",
                        "log": str(out_dir / f"{name}.log"),
                        "reported_out_dir": str(out_dir / "acceptance-preflight"),
                        "summary_file": str(out_dir / "acceptance-preflight" / "summary.json"),
                    }
                raise AssertionError(f"unexpected step executed after preflight failure: {name}")

            argv = [
                str(SCRIPT),
                "--task-id",
                "56",
                "--run-id",
                run_id,
                "--delivery-profile",
                "fast-ship",
                "--skip-agent-review",
            ]
            with (
                mock.patch.dict(os.environ, _stable_env(), clear=False),
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(run_review_pipeline_module, "repo_root", return_value=tmp_root),
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir),
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path),
                mock.patch.object(run_review_pipeline_module, "run_review_prerequisite_check", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_derive_change_scope_ceiling_guard", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_derive_rerun_forbidden_payload", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_find_reusable_clean_pipeline_steps", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_find_reusable_deterministic_steps_from_llm_only_failure", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_find_reusable_successful_acceptance_step", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_run_step", side_effect=fake_run_step),
                mock.patch.object(run_review_pipeline_module, "resolve_triplet", return_value=self._triplet()),
            ):
                rc = run_review_pipeline_module.main()

            self.assertEqual(1, rc)
            self.assertEqual(["sc-acceptance-preflight"], [name for name, _ in calls])

            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("fail", summary["status"])
            self.assertEqual(["sc-acceptance-check"], [item["name"] for item in summary["steps"]])
            cmd = summary["steps"][0]["cmd"]
            self.assertIn("--only", cmd)
            expected_only = "adr,links,overlay,contracts,arch,build"
            if str(run_review_pipeline_module.profile_acceptance_defaults("fast-ship").get("subtasks_coverage") or "skip") in {"warn", "require"}:
                expected_only = "adr,links,subtasks,overlay,contracts,arch,build"
            self.assertEqual(expected_only, cmd[cmd.index("--only") + 1])

    def test_cli_preflight_failure_should_stop_before_sc_test(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-56-{run_id}"
            latest_path = tmp_root / "sc-review-pipeline-task-56" / "latest.json"
            argv = [
                str(SCRIPT),
                "--task-id",
                "56",
                "--run-id",
                run_id,
                "--delivery-profile",
                "fast-ship",
                "--skip-agent-review",
            ]
            with (
                mock.patch.dict(os.environ, _stable_env(), clear=False),
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(run_review_pipeline_module, "repo_root", return_value=tmp_root),
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir),
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path),
                mock.patch.object(run_review_pipeline_module, "run_review_prerequisite_check", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_derive_change_scope_ceiling_guard", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_derive_rerun_forbidden_payload", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_find_reusable_clean_pipeline_steps", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_find_reusable_deterministic_steps_from_llm_only_failure", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_find_reusable_successful_acceptance_step", return_value=None),
                mock.patch.object(run_review_pipeline_module, "resolve_triplet", return_value=self._triplet()),
                mock.patch.object(
                    run_review_pipeline_module,
                    "_run_cli_capability_preflight",
                    return_value={
                        "name": "sc-acceptance-check",
                        "cmd": ["py", "-3", "scripts/sc/acceptance_check.py", "--self-check"],
                        "rc": 2,
                        "status": "fail",
                        "log": str(out_dir / "cli-preflight-sc-acceptance-check.log"),
                        "reported_out_dir": "",
                        "summary_file": "",
                    },
                ),
                mock.patch.object(run_review_pipeline_module, "_run_step") as run_step_mock,
            ):
                rc = run_review_pipeline_module.main()

            self.assertEqual(1, rc)
            run_step_mock.assert_not_called()
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("fail", summary["status"])
            self.assertEqual(["sc-acceptance-check"], [item["name"] for item in summary["steps"]])

    def test_refactor_preflight_failure_should_stop_before_sc_test(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-56-{run_id}"
            latest_path = tmp_root / "sc-review-pipeline-task-56" / "latest.json"
            argv = [
                str(SCRIPT),
                "--task-id",
                "56",
                "--run-id",
                run_id,
                "--delivery-profile",
                "fast-ship",
                "--skip-agent-review",
            ]
            with (
                mock.patch.dict(os.environ, _stable_env(), clear=False),
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(run_review_pipeline_module, "repo_root", return_value=tmp_root),
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir),
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path),
                mock.patch.object(run_review_pipeline_module, "resolve_triplet", return_value=self._triplet()),
                mock.patch.object(run_review_pipeline_module, "_load_latest_task_execution_context", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_derive_change_scope_ceiling_guard", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_derive_rerun_forbidden_payload", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_find_reusable_clean_pipeline_steps", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_find_reusable_deterministic_steps_from_llm_only_failure", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_find_reusable_successful_acceptance_step", return_value=None),
                mock.patch.object(
                    run_review_pipeline_module,
                    "run_review_prerequisite_check",
                    return_value={
                        "name": "sc-build-tdd-refactor-preflight",
                        "cmd": ["internal:review_prerequisite_check"],
                        "rc": 1,
                        "status": "fail",
                        "log": str(out_dir / "sc-build-tdd-refactor-preflight.log"),
                        "reported_out_dir": "",
                        "summary_file": "",
                    },
                ),
                mock.patch.object(run_review_pipeline_module, "_run_step") as run_step_mock,
            ):
                rc = run_review_pipeline_module.main()

            self.assertEqual(1, rc)
            run_step_mock.assert_not_called()
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("fail", summary["status"])
            self.assertEqual(["sc-build-tdd-refactor-preflight"], [item["name"] for item in summary["steps"]])

    def test_build_pipeline_steps_should_pass_explicit_llm_agent_timeouts_to_llm_review(self) -> None:
        args = run_review_pipeline_module.build_parser().parse_args(
            [
                "--task-id",
                "56",
                "--run-id",
                "run-a",
                "--delivery-profile",
                "fast-ship",
                "--llm-agent-timeouts",
                "code-reviewer=480",
            ]
        )
        triplet = self._triplet()
        llm_defaults = run_review_pipeline_module.profile_llm_review_defaults("fast-ship")
        llm_plan = run_review_pipeline_module.resolve_llm_review_tier_plan(
            delivery_profile="fast-ship",
            triplet=triplet,
            profile_defaults=llm_defaults,
        )
        planned_steps = run_review_pipeline_module.build_pipeline_steps(
            args=args,
            task_id="56",
            run_id="run-a",
            delivery_profile="fast-ship",
            security_profile="host-safe",
            acceptance_defaults=run_review_pipeline_module.profile_acceptance_defaults("fast-ship"),
            triplet=triplet,
            llm_agents=str(llm_plan.get("agents") or llm_defaults.get("agents") or "all"),
            llm_timeout_sec=int(llm_plan.get("timeout_sec") or llm_defaults.get("timeout_sec") or 900),
            llm_agent_timeout_sec=int(llm_plan.get("agent_timeout_sec") or llm_defaults.get("agent_timeout_sec") or 300),
            llm_agent_timeouts="code-reviewer=480",
            llm_semantic_gate=str(llm_plan.get("semantic_gate") or llm_defaults.get("semantic_gate") or "warn"),
            llm_strict=bool(llm_plan.get("strict", llm_defaults.get("strict", False))),
            llm_diff_mode=str(llm_plan.get("diff_mode") or llm_defaults.get("diff_mode") or "summary"),
        )
        llm_cmd = next(cmd for name, cmd, _timeout, skipped in planned_steps if name == "sc-llm-review" and not skipped)
        self.assertIn("--agent-timeouts", llm_cmd)
        self.assertEqual("code-reviewer=480", llm_cmd[llm_cmd.index("--agent-timeouts") + 1])

    def test_build_parser_should_accept_llm_backend(self) -> None:
        args = run_review_pipeline_module.build_parser().parse_args(
            [
                "--task-id",
                "56",
                "--run-id",
                "run-a",
                "--llm-backend",
                "openai-api",
            ]
        )

        self.assertEqual("openai-api", args.llm_backend)

    def test_build_pipeline_steps_should_pass_llm_backend_to_llm_review(self) -> None:
        args = run_review_pipeline_module.build_parser().parse_args(
            [
                "--task-id",
                "56",
                "--run-id",
                "run-a",
                "--delivery-profile",
                "fast-ship",
                "--llm-backend",
                "openai-api",
            ]
        )
        triplet = self._triplet()
        llm_defaults = run_review_pipeline_module.profile_llm_review_defaults("fast-ship")
        llm_plan = run_review_pipeline_module.resolve_llm_review_tier_plan(
            delivery_profile="fast-ship",
            triplet=triplet,
            profile_defaults=llm_defaults,
        )
        planned_steps = run_review_pipeline_module.build_pipeline_steps(
            args=args,
            task_id="56",
            run_id="run-a",
            delivery_profile="fast-ship",
            security_profile="host-safe",
            acceptance_defaults=run_review_pipeline_module.profile_acceptance_defaults("fast-ship"),
            triplet=triplet,
            llm_agents=str(llm_plan.get("agents") or llm_defaults.get("agents") or "all"),
            llm_timeout_sec=int(llm_plan.get("timeout_sec") or llm_defaults.get("timeout_sec") or 900),
            llm_agent_timeout_sec=int(llm_plan.get("agent_timeout_sec") or llm_defaults.get("agent_timeout_sec") or 300),
            llm_agent_timeouts="",
            llm_semantic_gate=str(llm_plan.get("semantic_gate") or llm_defaults.get("semantic_gate") or "warn"),
            llm_strict=bool(llm_plan.get("strict", llm_defaults.get("strict", False))),
            llm_diff_mode=str(llm_plan.get("diff_mode") or llm_defaults.get("diff_mode") or "summary"),
            llm_backend=args.llm_backend,
        )

        llm_cmd = next(cmd for name, cmd, _timeout, skipped in planned_steps if name == "sc-llm-review" and not skipped)
        self.assertIn("--llm-backend", llm_cmd)
        self.assertEqual("openai-api", llm_cmd[llm_cmd.index("--llm-backend") + 1])

    def test_find_reusable_successful_acceptance_step_should_match_latest_successful_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            logs_root = tmp_root / "logs" / "ci" / "2026-04-06"
            previous_out_dir = logs_root / "sc-review-pipeline-task-56-previous"
            previous_out_dir.mkdir(parents=True, exist_ok=True)
            args = run_review_pipeline_module.build_parser().parse_args(
                [
                    "--task-id",
                    "56",
                    "--run-id",
                    "previous",
                    "--delivery-profile",
                    "fast-ship",
                    "--skip-agent-review",
                ]
            )
            triplet = self._triplet()
            llm_defaults = run_review_pipeline_module.profile_llm_review_defaults("fast-ship")
            llm_plan = run_review_pipeline_module.resolve_llm_review_tier_plan(
                delivery_profile="fast-ship",
                triplet=triplet,
                profile_defaults=llm_defaults,
            )
            planned_steps = run_review_pipeline_module.build_pipeline_steps(
                args=args,
                task_id="56",
                run_id="previous",
                delivery_profile="fast-ship",
                security_profile="host-safe",
                acceptance_defaults=run_review_pipeline_module.profile_acceptance_defaults("fast-ship"),
                triplet=triplet,
                llm_agents=str(llm_plan.get("agents") or llm_defaults.get("agents") or "all"),
                llm_timeout_sec=int(llm_plan.get("timeout_sec") or llm_defaults.get("timeout_sec") or 900),
                llm_agent_timeout_sec=int(llm_plan.get("agent_timeout_sec") or llm_defaults.get("agent_timeout_sec") or 300),
                llm_agent_timeouts="",
                llm_semantic_gate=str(llm_plan.get("semantic_gate") or llm_defaults.get("semantic_gate") or "warn"),
                llm_strict=bool(llm_plan.get("strict", llm_defaults.get("strict", False))),
                llm_diff_mode=str(llm_plan.get("diff_mode") or llm_defaults.get("diff_mode") or "summary"),
            )
            planned_cmd_map = {name: cmd for name, cmd, _timeout, skipped in planned_steps if not skipped}

            child_dir = previous_out_dir / "sc-acceptance-check-artifacts"
            child_dir.mkdir(parents=True, exist_ok=True)
            (child_dir / "summary.json").write_text(
                json.dumps({"step": "sc-acceptance-check", "status": "ok"}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (previous_out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "cmd": "sc-review-pipeline",
                        "task_id": "56",
                        "run_id": "previous",
                        "status": "fail",
                        "steps": [
                            {
                                "name": "sc-acceptance-check",
                                "cmd": planned_cmd_map["sc-acceptance-check"],
                                "rc": 0,
                                "status": "ok",
                                "log": str(previous_out_dir / "sc-acceptance-check.log"),
                                "reported_out_dir": str(child_dir),
                                "summary_file": str(child_dir / "summary.json"),
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (previous_out_dir / "execution-context.json").write_text(
                json.dumps(
                    {
                        "delivery_profile": "fast-ship",
                        "security_profile": "host-safe",
                        "git": {"head": "prev-head", "status_short": []},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            out_dir = tmp_root / "logs" / "ci" / "2026-04-07" / "sc-review-pipeline-task-56-current"
            with (
                mock.patch.object(run_review_pipeline_module, "repo_root", return_value=tmp_root),
                mock.patch.object(
                    run_review_pipeline_module,
                    "classify_change_scope_between_snapshots",
                    return_value={
                        "deterministic_strategy": "reuse-latest",
                        "changed_paths": ["docs/architecture/overlays/PRD-NEWROUGE-GAME-0001/08/_index.md"],
                        "unsafe_paths": [],
                    },
                ),
            ):
                reused_step = run_review_pipeline_module._find_reusable_successful_acceptance_step(
                    out_dir=out_dir,
                    task_id="56",
                    delivery_profile="fast-ship",
                    security_profile="host-safe",
                    planned_cmd=planned_cmd_map["sc-acceptance-check"],
                    git_fingerprint={"head": "current-head", "status_short": []},
                )

            self.assertIsNotNone(reused_step)
            assert reused_step is not None
            self.assertEqual("sc-acceptance-check", reused_step["name"])
            self.assertEqual("ok", reused_step["status"])
            self.assertTrue(str(reused_step["summary_file"]).endswith("summary.json"))

    def test_find_reusable_successful_acceptance_step_should_allow_preflight_to_reuse_successful_full_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            logs_root = tmp_root / "logs" / "ci" / "2026-04-06"
            previous_out_dir = logs_root / "sc-review-pipeline-task-56-previous"
            previous_out_dir.mkdir(parents=True, exist_ok=True)
            args = run_review_pipeline_module.build_parser().parse_args(
                [
                    "--task-id",
                    "56",
                    "--run-id",
                    "previous",
                    "--delivery-profile",
                    "fast-ship",
                    "--skip-agent-review",
                ]
            )
            acceptance_defaults = run_review_pipeline_module.profile_acceptance_defaults("fast-ship")
            acceptance_defaults["subtasks_coverage"] = "warn"
            planned_preflight_cmd = run_review_pipeline_module.build_acceptance_command(
                args=args,
                task_id="56",
                run_id="current",
                delivery_profile="fast-ship",
                security_profile="host-safe",
                acceptance_defaults=acceptance_defaults,
                preflight=True,
            )
            full_acceptance_cmd = run_review_pipeline_module.build_acceptance_command(
                args=args,
                task_id="56",
                run_id="previous",
                delivery_profile="fast-ship",
                security_profile="host-safe",
                acceptance_defaults=acceptance_defaults,
                preflight=False,
            )

            child_dir = previous_out_dir / "sc-acceptance-check-artifacts"
            child_dir.mkdir(parents=True, exist_ok=True)
            (child_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "cmd": "sc-acceptance-check",
                        "status": "ok",
                        "task_id": "56",
                        "steps": [
                            {"name": "adr-compliance", "status": "ok", "rc": 0},
                            {"name": "task-links-validate", "status": "ok", "rc": 0},
                            {"name": "task-test-refs", "status": "ok", "rc": 0},
                            {"name": "acceptance-refs", "status": "ok", "rc": 0},
                            {"name": "acceptance-anchors", "status": "ok", "rc": 0},
                            {"name": "subtasks-coverage", "status": "ok", "rc": 0},
                            {"name": "validate-task-overlays", "status": "ok", "rc": 0},
                            {"name": "validate-contracts", "status": "ok", "rc": 0},
                            {"name": "architecture-boundary", "status": "ok", "rc": 0},
                            {"name": "dotnet-build-warnaserror", "status": "ok", "rc": 0},
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (previous_out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "cmd": "sc-review-pipeline",
                        "task_id": "56",
                        "run_id": "previous",
                        "status": "ok",
                        "steps": [
                            {
                                "name": "sc-acceptance-check",
                                "cmd": full_acceptance_cmd,
                                "rc": 0,
                                "status": "ok",
                                "log": str(previous_out_dir / "sc-acceptance-check.log"),
                                "reported_out_dir": str(child_dir),
                                "summary_file": str(child_dir / "summary.json"),
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (previous_out_dir / "execution-context.json").write_text(
                json.dumps(
                    {
                        "delivery_profile": "fast-ship",
                        "security_profile": "host-safe",
                        "git": {"head": "prev-head", "status_short": []},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            out_dir = tmp_root / "logs" / "ci" / "2026-04-07" / "sc-review-pipeline-task-56-current"
            with (
                mock.patch.object(run_review_pipeline_module, "repo_root", return_value=tmp_root),
                mock.patch.object(
                    run_review_pipeline_module,
                    "classify_change_scope_between_snapshots",
                    return_value={
                        "deterministic_strategy": "reuse-latest",
                        "changed_paths": ["docs/architecture/overlays/PRD-NEWROUGE-GAME-0001/08/_index.md"],
                        "unsafe_paths": [],
                    },
                ),
            ):
                reused_step = run_review_pipeline_module._find_reusable_successful_acceptance_step(
                    out_dir=out_dir,
                    task_id="56",
                    delivery_profile="fast-ship",
                    security_profile="host-safe",
                    planned_cmd=planned_preflight_cmd,
                    git_fingerprint={"head": "current-head", "status_short": []},
                )

            self.assertIsNotNone(reused_step)
            assert reused_step is not None
            self.assertEqual("sc-acceptance-check", reused_step["name"])
            self.assertEqual("ok", reused_step["status"])
            self.assertTrue(str(reused_step["summary_file"]).endswith("summary.json"))

    def test_clean_skip_should_reuse_latest_successful_full_pipeline_for_docs_only_delta(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            logs_root = tmp_root / "logs" / "ci" / "2026-04-06"
            previous_out_dir = logs_root / "sc-review-pipeline-task-56-previous"
            previous_out_dir.mkdir(parents=True, exist_ok=True)
            args = run_review_pipeline_module.build_parser().parse_args(
                [
                    "--task-id",
                    "56",
                    "--run-id",
                    "previous",
                    "--delivery-profile",
                    "fast-ship",
                    "--skip-agent-review",
                ]
            )
            triplet = self._triplet()
            llm_defaults = run_review_pipeline_module.profile_llm_review_defaults("fast-ship")
            llm_plan = run_review_pipeline_module.resolve_llm_review_tier_plan(
                delivery_profile="fast-ship",
                triplet=triplet,
                profile_defaults=llm_defaults,
            )
            planned_steps = run_review_pipeline_module.build_pipeline_steps(
                args=args,
                task_id="56",
                run_id="previous",
                delivery_profile="fast-ship",
                security_profile="host-safe",
                acceptance_defaults=run_review_pipeline_module.profile_acceptance_defaults("fast-ship"),
                triplet=triplet,
                llm_agents=str(llm_plan.get("agents") or llm_defaults.get("agents") or "all"),
                llm_timeout_sec=int(llm_plan.get("timeout_sec") or llm_defaults.get("timeout_sec") or 900),
                llm_agent_timeout_sec=int(llm_plan.get("agent_timeout_sec") or llm_defaults.get("agent_timeout_sec") or 300),
                llm_agent_timeouts="",
                llm_semantic_gate=str(llm_plan.get("semantic_gate") or llm_defaults.get("semantic_gate") or "warn"),
                llm_strict=bool(llm_plan.get("strict", llm_defaults.get("strict", False))),
                llm_diff_mode=str(llm_plan.get("diff_mode") or llm_defaults.get("diff_mode") or "summary"),
            )
            planned_cmd_map = {name: cmd for name, cmd, _timeout, skipped in planned_steps if not skipped}

            for step_name in ("sc-test", "sc-acceptance-check", "sc-llm-review"):
                child_dir = previous_out_dir / f"{step_name}-artifacts"
                child_dir.mkdir(parents=True, exist_ok=True)
                payload = {"step": step_name, "status": "ok"}
                if step_name == "sc-llm-review":
                    payload = {
                        "status": "ok",
                        "results": [
                            {"agent": "code-reviewer", "status": "ok", "rc": 0, "details": {"verdict": "OK"}},
                            {"agent": "security-auditor", "status": "ok", "rc": 0, "details": {"verdict": "OK"}},
                            {"agent": "semantic-equivalence-auditor", "status": "ok", "rc": 0, "details": {"verdict": "OK"}},
                        ],
                    }
                (child_dir / "summary.json").write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )

            summary_payload = {
                "cmd": "sc-review-pipeline",
                "task_id": "56",
                "requested_run_id": "previous",
                "run_id": "previous",
                "allow_overwrite": False,
                "force_new_run_id": False,
                "status": "ok",
                "steps": [
                    {
                        "name": "sc-test",
                        "cmd": planned_cmd_map["sc-test"],
                        "rc": 0,
                        "status": "ok",
                        "log": str(previous_out_dir / "sc-test.log"),
                        "reported_out_dir": str(previous_out_dir / "sc-test-artifacts"),
                        "summary_file": str(previous_out_dir / "sc-test-artifacts" / "summary.json"),
                    },
                    {
                        "name": "sc-acceptance-check",
                        "cmd": planned_cmd_map["sc-acceptance-check"],
                        "rc": 0,
                        "status": "ok",
                        "log": str(previous_out_dir / "sc-acceptance-check.log"),
                        "reported_out_dir": str(previous_out_dir / "sc-acceptance-check-artifacts"),
                        "summary_file": str(previous_out_dir / "sc-acceptance-check-artifacts" / "summary.json"),
                    },
                    {
                        "name": "sc-llm-review",
                        "cmd": planned_cmd_map["sc-llm-review"],
                        "rc": 0,
                        "status": "ok",
                        "log": str(previous_out_dir / "sc-llm-review.log"),
                        "reported_out_dir": str(previous_out_dir / "sc-llm-review-artifacts"),
                        "summary_file": str(previous_out_dir / "sc-llm-review-artifacts" / "summary.json"),
                    },
                ],
            }
            (previous_out_dir / "summary.json").write_text(
                json.dumps(summary_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (previous_out_dir / "execution-context.json").write_text(
                json.dumps(
                    {
                        "delivery_profile": "fast-ship",
                        "security_profile": "host-safe",
                        "git": {"head": "prev-head", "status_short": []},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            out_dir = tmp_root / "logs" / "ci" / "2026-04-07" / f"sc-review-pipeline-task-56-{run_id}"
            latest_path = tmp_root / "logs" / "ci" / "2026-04-07" / "sc-review-pipeline-task-56" / "latest.json"
            argv = [
                str(SCRIPT),
                "--task-id",
                "56",
                "--run-id",
                run_id,
                "--delivery-profile",
                "fast-ship",
                "--skip-agent-review",
            ]
            with (
                mock.patch.dict(os.environ, _stable_env(), clear=False),
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir),
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path),
                mock.patch.object(run_review_pipeline_module, "repo_root", return_value=tmp_root),
                mock.patch.object(run_review_pipeline_module, "run_review_prerequisite_check", return_value=None),
                mock.patch.object(run_review_pipeline_module, "resolve_triplet", return_value=self._triplet()),
                mock.patch.object(
                    run_review_pipeline_module,
                    "current_git_fingerprint",
                    return_value={"head": "current-head", "status_short": []},
                ),
                mock.patch.object(
                    run_review_pipeline_module,
                    "classify_change_scope_between_snapshots",
                    return_value={
                        "deterministic_strategy": "reuse-latest",
                        "changed_paths": ["decision-logs/active-task.md"],
                        "unsafe_paths": [],
                    },
                ),
                mock.patch.object(run_review_pipeline_module, "_run_step") as run_step_mock,
            ):
                rc = run_review_pipeline_module.main()

            self.assertEqual(0, rc)
            run_step_mock.assert_not_called()
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("ok", summary["status"])
            self.assertEqual("pipeline_clean", summary["reason"])
            self.assertEqual("full-clean-reuse", summary["reuse_mode"])
            self.assertGreaterEqual(int(summary["elapsed_sec"]), 0)
            self.assertEqual(
                ["sc-test", "sc-acceptance-check", "sc-llm-review"],
                [item["name"] for item in summary["steps"]],
            )
            self.assertTrue(all(item["status"] == "ok" for item in summary["steps"]))
            self.assertIn("decision-logs/active-task.md", (out_dir / "sc-llm-review.log").read_text(encoding="utf-8"))

    def test_reuse_deterministic_steps_should_reuse_sc_test_and_acceptance_after_llm_only_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            logs_root = tmp_root / "logs" / "ci" / "2026-04-06"
            previous_out_dir = logs_root / "sc-review-pipeline-task-56-previous"
            previous_out_dir.mkdir(parents=True, exist_ok=True)
            args = run_review_pipeline_module.build_parser().parse_args(
                [
                    "--task-id",
                    "56",
                    "--run-id",
                    "previous",
                    "--delivery-profile",
                    "fast-ship",
                    "--skip-agent-review",
                ]
            )
            triplet = self._triplet()
            llm_defaults = run_review_pipeline_module.profile_llm_review_defaults("fast-ship")
            llm_plan = run_review_pipeline_module.resolve_llm_review_tier_plan(
                delivery_profile="fast-ship",
                triplet=triplet,
                profile_defaults=llm_defaults,
            )
            planned_steps = run_review_pipeline_module.build_pipeline_steps(
                args=args,
                task_id="56",
                run_id="previous",
                delivery_profile="fast-ship",
                security_profile="host-safe",
                acceptance_defaults=run_review_pipeline_module.profile_acceptance_defaults("fast-ship"),
                triplet=triplet,
                llm_agents=str(llm_plan.get("agents") or llm_defaults.get("agents") or "all"),
                llm_timeout_sec=int(llm_plan.get("timeout_sec") or llm_defaults.get("timeout_sec") or 900),
                llm_agent_timeout_sec=int(llm_plan.get("agent_timeout_sec") or llm_defaults.get("agent_timeout_sec") or 300),
                llm_agent_timeouts="",
                llm_semantic_gate=str(llm_plan.get("semantic_gate") or llm_defaults.get("semantic_gate") or "warn"),
                llm_strict=bool(llm_plan.get("strict", llm_defaults.get("strict", False))),
                llm_diff_mode=str(llm_plan.get("diff_mode") or llm_defaults.get("diff_mode") or "summary"),
            )
            planned_cmd_map = {name: cmd for name, cmd, _timeout, skipped in planned_steps if not skipped}

            for step_name in ("sc-test", "sc-acceptance-check", "sc-llm-review"):
                child_dir = previous_out_dir / f"{step_name}-artifacts"
                child_dir.mkdir(parents=True, exist_ok=True)
                (child_dir / "summary.json").write_text(
                    json.dumps({"step": step_name, "status": "ok" if step_name != "sc-llm-review" else "fail"}, ensure_ascii=False, indent=2)
                    + "\n",
                    encoding="utf-8",
                )

            summary_payload = {
                "cmd": "sc-review-pipeline",
                "task_id": "56",
                "requested_run_id": "previous",
                "run_id": "previous",
                "status": "fail",
                "steps": [
                    {
                        "name": "sc-test",
                        "cmd": planned_cmd_map["sc-test"],
                        "rc": 0,
                        "status": "ok",
                        "log": str(previous_out_dir / "sc-test.log"),
                        "reported_out_dir": str(previous_out_dir / "sc-test-artifacts"),
                        "summary_file": str(previous_out_dir / "sc-test-artifacts" / "summary.json"),
                    },
                    {
                        "name": "sc-acceptance-check",
                        "cmd": planned_cmd_map["sc-acceptance-check"],
                        "rc": 0,
                        "status": "ok",
                        "log": str(previous_out_dir / "sc-acceptance-check.log"),
                        "reported_out_dir": str(previous_out_dir / "sc-acceptance-check-artifacts"),
                        "summary_file": str(previous_out_dir / "sc-acceptance-check-artifacts" / "summary.json"),
                    },
                    {
                        "name": "sc-llm-review",
                        "cmd": planned_cmd_map["sc-llm-review"],
                        "rc": 124,
                        "status": "fail",
                        "log": str(previous_out_dir / "sc-llm-review.log"),
                        "reported_out_dir": str(previous_out_dir / "sc-llm-review-artifacts"),
                        "summary_file": str(previous_out_dir / "sc-llm-review-artifacts" / "summary.json"),
                    },
                ],
            }
            (previous_out_dir / "summary.json").write_text(
                json.dumps(summary_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (previous_out_dir / "execution-context.json").write_text(
                json.dumps(
                    {
                        "delivery_profile": "fast-ship",
                        "security_profile": "host-safe",
                        "git": {"head": "prev-head", "status_short": []},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            out_dir = tmp_root / "logs" / "ci" / "2026-04-07" / "sc-review-pipeline-task-56-current"
            with (
                mock.patch.object(run_review_pipeline_module, "repo_root", return_value=tmp_root),
                mock.patch.object(
                    run_review_pipeline_module,
                    "classify_change_scope_between_snapshots",
                    return_value={
                        "deterministic_strategy": "reuse-latest",
                        "changed_paths": ["docs/architecture/overlays/PRD-NEWROUGE-GAME-0001/08/_index.md"],
                        "unsafe_paths": [],
                    },
                ),
            ):
                reused_steps = run_review_pipeline_module._find_reusable_deterministic_steps_from_llm_only_failure(
                    out_dir=out_dir,
                    task_id="56",
                    delivery_profile="fast-ship",
                    security_profile="host-safe",
                    planned_steps=planned_steps,
                    git_fingerprint={"head": "current-head", "status_short": []},
                )

            self.assertIsNotNone(reused_steps)
            assert reused_steps is not None
            self.assertEqual(["sc-test", "sc-acceptance-check"], [step["name"] for step in reused_steps])
            self.assertTrue(all(step["status"] == "ok" for step in reused_steps))

    def test_clean_skip_should_reject_parent_ok_when_llm_child_summary_is_not_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            logs_root = tmp_root / "logs" / "ci" / "2026-04-06"
            previous_out_dir = logs_root / "sc-review-pipeline-task-56-previous"
            previous_out_dir.mkdir(parents=True, exist_ok=True)
            args = run_review_pipeline_module.build_parser().parse_args(
                [
                    "--task-id",
                    "56",
                    "--run-id",
                    "previous",
                    "--delivery-profile",
                    "fast-ship",
                    "--skip-agent-review",
                ]
            )
            triplet = self._triplet()
            llm_defaults = run_review_pipeline_module.profile_llm_review_defaults("fast-ship")
            llm_plan = run_review_pipeline_module.resolve_llm_review_tier_plan(
                delivery_profile="fast-ship",
                triplet=triplet,
                profile_defaults=llm_defaults,
            )
            planned_steps = run_review_pipeline_module.build_pipeline_steps(
                args=args,
                task_id="56",
                run_id="previous",
                delivery_profile="fast-ship",
                security_profile="host-safe",
                acceptance_defaults=run_review_pipeline_module.profile_acceptance_defaults("fast-ship"),
                triplet=triplet,
                llm_agents=str(llm_plan.get("agents") or llm_defaults.get("agents") or "all"),
                llm_timeout_sec=int(llm_plan.get("timeout_sec") or llm_defaults.get("timeout_sec") or 900),
                llm_agent_timeout_sec=int(llm_plan.get("agent_timeout_sec") or llm_defaults.get("agent_timeout_sec") or 300),
                llm_agent_timeouts="",
                llm_semantic_gate=str(llm_plan.get("semantic_gate") or llm_defaults.get("semantic_gate") or "warn"),
                llm_strict=bool(llm_plan.get("strict", llm_defaults.get("strict", False))),
                llm_diff_mode=str(llm_plan.get("diff_mode") or llm_defaults.get("diff_mode") or "summary"),
            )
            planned_cmd_map = {name: cmd for name, cmd, _timeout, skipped in planned_steps if not skipped}
            for step_name in ("sc-test", "sc-acceptance-check", "sc-llm-review"):
                child_dir = previous_out_dir / f"{step_name}-artifacts"
                child_dir.mkdir(parents=True, exist_ok=True)
                payload = {"step": step_name, "status": "ok"}
                if step_name == "sc-llm-review":
                    payload = {
                        "status": "ok",
                        "results": [
                            {"agent": "code-reviewer", "status": "ok", "rc": 0, "details": {"verdict": "Needs Fix"}},
                        ],
                    }
                (child_dir / "summary.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            summary_payload = {
                "cmd": "sc-review-pipeline",
                "task_id": "56",
                "run_id": "previous",
                "status": "ok",
                "steps": [
                    {
                        "name": "sc-test",
                        "cmd": planned_cmd_map["sc-test"],
                        "rc": 0,
                        "status": "ok",
                        "reported_out_dir": str(previous_out_dir / "sc-test-artifacts"),
                        "summary_file": str(previous_out_dir / "sc-test-artifacts" / "summary.json"),
                    },
                    {
                        "name": "sc-acceptance-check",
                        "cmd": planned_cmd_map["sc-acceptance-check"],
                        "rc": 0,
                        "status": "ok",
                        "reported_out_dir": str(previous_out_dir / "sc-acceptance-check-artifacts"),
                        "summary_file": str(previous_out_dir / "sc-acceptance-check-artifacts" / "summary.json"),
                    },
                    {
                        "name": "sc-llm-review",
                        "cmd": planned_cmd_map["sc-llm-review"],
                        "rc": 0,
                        "status": "ok",
                        "reported_out_dir": str(previous_out_dir / "sc-llm-review-artifacts"),
                        "summary_file": str(previous_out_dir / "sc-llm-review-artifacts" / "summary.json"),
                    },
                ],
            }
            (previous_out_dir / "summary.json").write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (previous_out_dir / "execution-context.json").write_text(
                json.dumps(
                    {
                        "delivery_profile": "fast-ship",
                        "security_profile": "host-safe",
                        "git": {"head": "same-head", "status_short": []},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            out_dir = tmp_root / "logs" / "ci" / "2026-04-07" / "sc-review-pipeline-task-56-current"
            with mock.patch.object(run_review_pipeline_module, "repo_root", return_value=tmp_root):
                reused_steps = run_review_pipeline_module._find_reusable_clean_pipeline_steps(
                    out_dir=out_dir,
                    task_id="56",
                    delivery_profile="fast-ship",
                    security_profile="host-safe",
                    planned_steps=planned_steps,
                    git_fingerprint={"head": "same-head", "status_short": []},
                )
            self.assertIsNone(reused_steps)

    def test_main_should_block_full_rerun_when_latest_run_is_deterministic_ok_but_llm_not_clean(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            previous_out_dir = tmp_root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-56-previous"
            previous_out_dir.mkdir(parents=True, exist_ok=True)
            args = run_review_pipeline_module.build_parser().parse_args(
                [
                    "--task-id",
                    "56",
                    "--run-id",
                    "previous",
                    "--delivery-profile",
                    "fast-ship",
                    "--skip-agent-review",
                ]
            )
            triplet = self._triplet()
            llm_defaults = run_review_pipeline_module.profile_llm_review_defaults("fast-ship")
            llm_plan = run_review_pipeline_module.resolve_llm_review_tier_plan(
                delivery_profile="fast-ship",
                triplet=triplet,
                profile_defaults=llm_defaults,
            )
            planned_steps = run_review_pipeline_module.build_pipeline_steps(
                args=args,
                task_id="56",
                run_id="previous",
                delivery_profile="fast-ship",
                security_profile="host-safe",
                acceptance_defaults=run_review_pipeline_module.profile_acceptance_defaults("fast-ship"),
                triplet=triplet,
                llm_agents=str(llm_plan.get("agents") or llm_defaults.get("agents") or "all"),
                llm_timeout_sec=int(llm_plan.get("timeout_sec") or llm_defaults.get("timeout_sec") or 900),
                llm_agent_timeout_sec=int(llm_plan.get("agent_timeout_sec") or llm_defaults.get("agent_timeout_sec") or 300),
                llm_agent_timeouts="",
                llm_semantic_gate=str(llm_plan.get("semantic_gate") or llm_defaults.get("semantic_gate") or "warn"),
                llm_strict=bool(llm_plan.get("strict", llm_defaults.get("strict", False))),
                llm_diff_mode=str(llm_plan.get("diff_mode") or llm_defaults.get("diff_mode") or "summary"),
            )
            planned_cmd_map = {name: cmd for name, cmd, _timeout, skipped in planned_steps if not skipped}
            for step_name in ("sc-test", "sc-acceptance-check", "sc-llm-review"):
                child_dir = previous_out_dir / f"{step_name}-artifacts"
                child_dir.mkdir(parents=True, exist_ok=True)
                payload = {"step": step_name, "status": "ok"}
                if step_name == "sc-llm-review":
                    payload = {
                        "status": "fail",
                        "results": [
                            {"agent": "code-reviewer", "status": "fail", "rc": 124, "details": {"verdict": ""}},
                        ],
                    }
                (child_dir / "summary.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (previous_out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "cmd": "sc-review-pipeline",
                        "task_id": "56",
                        "requested_run_id": "previous",
                        "run_id": "previous",
                        "status": "fail",
                        "steps": [
                            {
                                "name": "sc-test",
                                "cmd": planned_cmd_map["sc-test"],
                                "rc": 0,
                                "status": "ok",
                                "log": str(previous_out_dir / "sc-test.log"),
                                "reported_out_dir": str(previous_out_dir / "sc-test-artifacts"),
                                "summary_file": str(previous_out_dir / "sc-test-artifacts" / "summary.json"),
                            },
                            {
                                "name": "sc-acceptance-check",
                                "cmd": planned_cmd_map["sc-acceptance-check"],
                                "rc": 0,
                                "status": "ok",
                                "log": str(previous_out_dir / "sc-acceptance-check.log"),
                                "reported_out_dir": str(previous_out_dir / "sc-acceptance-check-artifacts"),
                                "summary_file": str(previous_out_dir / "sc-acceptance-check-artifacts" / "summary.json"),
                            },
                            {
                                "name": "sc-llm-review",
                                "cmd": planned_cmd_map["sc-llm-review"],
                                "rc": 124,
                                "status": "fail",
                                "log": str(previous_out_dir / "sc-llm-review.log"),
                                "reported_out_dir": str(previous_out_dir / "sc-llm-review-artifacts"),
                                "summary_file": str(previous_out_dir / "sc-llm-review-artifacts" / "summary.json"),
                            },
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (previous_out_dir / "execution-context.json").write_text(
                json.dumps(
                    {
                        "run_id": "previous",
                        "delivery_profile": "fast-ship",
                        "security_profile": "host-safe",
                        "git": {"head": "prev-head", "status_short": []},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            out_dir = tmp_root / "logs" / "ci" / "2026-04-07" / f"sc-review-pipeline-task-56-{run_id}"
            latest_path = tmp_root / "logs" / "ci" / "2026-04-07" / "sc-review-pipeline-task-56" / "latest.json"
            argv = [
                str(SCRIPT),
                "--task-id",
                "56",
                "--run-id",
                run_id,
                "--delivery-profile",
                "fast-ship",
                "--skip-agent-review",
            ]
            with (
                mock.patch.dict(os.environ, _stable_env(), clear=False),
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir),
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path),
                mock.patch.object(run_review_pipeline_module, "repo_root", return_value=tmp_root),
                mock.patch.object(run_review_pipeline_module, "resolve_triplet", return_value=self._triplet()),
                mock.patch.object(
                    run_review_pipeline_module,
                    "current_git_fingerprint",
                    return_value={"head": "current-head", "status_short": []},
                ),
                mock.patch.object(
                    run_review_pipeline_module,
                    "classify_change_scope_between_snapshots",
                    return_value={
                        "deterministic_strategy": "reuse-latest",
                        "changed_paths": ["docs/architecture/overlays/PRD-NEWROUGE-GAME-0001/08/_index.md"],
                        "unsafe_paths": [],
                    },
                ),
                mock.patch.object(run_review_pipeline_module, "_run_step") as run_step_mock,
            ):
                rc = run_review_pipeline_module.main()

            self.assertEqual(1, rc)
            run_step_mock.assert_not_called()
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            latest = json.loads(latest_path.read_text(encoding="utf-8"))
            validate_pipeline_latest_index_payload(latest)
            self.assertEqual("fail", summary["status"])
            self.assertEqual("rerun_blocked:deterministic_green_llm_not_clean", summary["reason"])
            self.assertEqual("needs-fix-fast", summary["recommended_action"])
            self.assertIn("llm-only closure", summary["recommended_action_why"].lower())
            self.assertEqual("none", summary["reuse_mode"])
            self.assertTrue(summary["diagnostics"]["rerun_guard"]["blocked"])
            self.assertEqual("llm-only", summary["diagnostics"]["rerun_guard"]["recommended_path"])
            self.assertEqual("rerun_blocked:deterministic_green_llm_not_clean", latest["reason"])
            self.assertTrue(latest["diagnostics"]["rerun_guard"]["blocked"])

    def test_main_should_block_full_rerun_when_chapter6_route_requests_inspect_first(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / "logs" / "ci" / "2026-04-07" / f"sc-review-pipeline-task-56-{run_id}"
            latest_path = tmp_root / "logs" / "ci" / "2026-04-07" / "sc-review-pipeline-task-56" / "latest.json"
            argv = [
                str(SCRIPT),
                "--task-id",
                "56",
                "--run-id",
                run_id,
                "--delivery-profile",
                "fast-ship",
                "--skip-agent-review",
            ]
            with (
                mock.patch.dict(os.environ, _stable_env(), clear=False),
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir),
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path),
                mock.patch.object(run_review_pipeline_module, "repo_root", return_value=tmp_root),
                mock.patch.object(run_review_pipeline_module, "resolve_triplet", return_value=self._triplet()),
                mock.patch.object(run_review_pipeline_module, "_find_recent_deterministic_green_llm_not_clean_run", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_find_repeated_deterministic_failure_guard", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_derive_change_scope_ceiling_guard", return_value=None),
                mock.patch.object(
                    run_review_pipeline_module,
                    "_derive_chapter6_route_guard",
                    create=True,
                    return_value={
                        "kind": "chapter6_route_inspect_first",
                        "blocked": True,
                        "recommended_path": "inspect-first",
                        "recommended_command": "py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id 56",
                        "allow_override_flag": "--allow-full-rerun",
                    },
                ),
                mock.patch.object(run_review_pipeline_module, "_run_step", side_effect=AssertionError("run_step should not execute when route blocks rerun")),
            ):
                rc = run_review_pipeline_module.main()

            self.assertEqual(1, rc)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("rerun_blocked:chapter6_route_inspect_first", summary["reason"])
            self.assertTrue(summary["diagnostics"]["rerun_guard"]["blocked"])
            self.assertEqual("inspect-first", summary["diagnostics"]["rerun_guard"]["recommended_path"])

    def test_main_should_block_full_rerun_when_chapter6_route_requests_repo_noise_stop(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / "logs" / "ci" / "2026-04-07" / f"sc-review-pipeline-task-56-{run_id}"
            latest_path = tmp_root / "logs" / "ci" / "2026-04-07" / "sc-review-pipeline-task-56" / "latest.json"
            argv = [
                str(SCRIPT),
                "--task-id",
                "56",
                "--run-id",
                run_id,
                "--delivery-profile",
                "fast-ship",
                "--skip-agent-review",
            ]
            with (
                mock.patch.dict(os.environ, _stable_env(), clear=False),
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir),
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path),
                mock.patch.object(run_review_pipeline_module, "repo_root", return_value=tmp_root),
                mock.patch.object(run_review_pipeline_module, "resolve_triplet", return_value=self._triplet()),
                mock.patch.object(run_review_pipeline_module, "_find_recent_deterministic_green_llm_not_clean_run", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_find_repeated_deterministic_failure_guard", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_derive_change_scope_ceiling_guard", return_value=None),
                mock.patch.object(
                    run_review_pipeline_module,
                    "_derive_chapter6_route_guard",
                    create=True,
                    return_value={
                        "kind": "chapter6_route_repo_noise_stop",
                        "blocked": True,
                        "recommended_path": "repo-noise-stop",
                        "recommended_command": "py -3 scripts/python/dev_cli.py chapter6-route --task-id 56 --recommendation-only",
                        "allow_override_flag": "",
                    },
                ),
                mock.patch.object(run_review_pipeline_module, "_run_step", side_effect=AssertionError("run_step should not execute when route blocks rerun")),
            ):
                rc = run_review_pipeline_module.main()

            self.assertEqual(1, rc)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("rerun_blocked:chapter6_route_repo_noise_stop", summary["reason"])
            self.assertEqual("repo-noise-stop", summary["diagnostics"]["rerun_guard"]["recommended_path"])

    def test_main_should_block_full_rerun_when_chapter6_route_requests_run_6_8(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / "logs" / "ci" / "2026-04-07" / f"sc-review-pipeline-task-56-{run_id}"
            latest_path = tmp_root / "logs" / "ci" / "2026-04-07" / "sc-review-pipeline-task-56" / "latest.json"
            argv = [
                str(SCRIPT),
                "--task-id",
                "56",
                "--run-id",
                run_id,
                "--delivery-profile",
                "fast-ship",
                "--skip-agent-review",
            ]
            with (
                mock.patch.dict(os.environ, _stable_env(), clear=False),
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir),
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path),
                mock.patch.object(run_review_pipeline_module, "repo_root", return_value=tmp_root),
                mock.patch.object(run_review_pipeline_module, "resolve_triplet", return_value=self._triplet()),
                mock.patch.object(run_review_pipeline_module, "_find_recent_deterministic_green_llm_not_clean_run", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_find_repeated_deterministic_failure_guard", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_derive_change_scope_ceiling_guard", return_value=None),
                mock.patch.object(
                    run_review_pipeline_module,
                    "_derive_chapter6_route_guard",
                    create=True,
                    return_value={
                        "kind": "chapter6_route_run_6_8",
                        "blocked": True,
                        "recommended_path": "run-6.8",
                    },
                ),
                mock.patch.object(run_review_pipeline_module, "_run_step", side_effect=AssertionError("run_step should not execute when route blocks rerun")),
            ):
                rc = run_review_pipeline_module.main()

            self.assertEqual(1, rc)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("rerun_blocked:chapter6_route_run_6_8", summary["reason"])
            self.assertEqual("run-6.8", summary["diagnostics"]["rerun_guard"]["recommended_path"])

    def test_main_should_stop_after_first_llm_timeout_when_deterministic_already_green(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-56-{run_id}"
            latest_path = tmp_root / "sc-review-pipeline-task-56" / "latest.json"
            calls: list[str] = []

            def fake_run_step(*, out_dir: Path, name: str, cmd: list[str], timeout_sec: int) -> dict:
                calls.append(name)
                if name == "sc-acceptance-preflight":
                    return {
                        "name": name,
                        "cmd": cmd,
                        "rc": 0,
                        "status": "ok",
                        "duration_sec": 2.0,
                        "log": str(out_dir / f"{name}.log"),
                        "reported_out_dir": str(out_dir / "acceptance-preflight"),
                        "summary_file": str(out_dir / "acceptance-preflight" / "summary.json"),
                    }
                if name in {"sc-test", "sc-acceptance-check"}:
                    duration = 11.0 if name == "sc-test" else 7.5
                    return {
                        "name": name,
                        "cmd": cmd,
                        "rc": 0,
                        "status": "ok",
                        "duration_sec": duration,
                        "log": str(out_dir / f"{name}.log"),
                        "reported_out_dir": str(out_dir / name),
                        "summary_file": str(out_dir / name / "summary.json"),
                    }
                if name == "sc-llm-review":
                    return {
                        "name": name,
                        "cmd": cmd,
                        "rc": 124,
                        "status": "fail",
                        "duration_sec": 19.0,
                        "log": str(out_dir / f"{name}.log"),
                        "reported_out_dir": "",
                        "summary_file": "",
                    }
                raise AssertionError(f"unexpected step: {name}")

            argv = [
                str(SCRIPT),
                "--task-id",
                "56",
                "--run-id",
                run_id,
                "--delivery-profile",
                "playable-ea",
                "--skip-agent-review",
            ]
            with (
                mock.patch.dict(os.environ, _stable_env(), clear=False),
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(run_review_pipeline_module, "repo_root", return_value=tmp_root),
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir),
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path),
                mock.patch.object(run_review_pipeline_module, "resolve_triplet", return_value=self._triplet()),
                mock.patch.object(run_review_pipeline_module, "_load_latest_task_execution_context", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_derive_change_scope_ceiling_guard", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_derive_rerun_forbidden_payload", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_find_reusable_clean_pipeline_steps", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_find_reusable_deterministic_steps_from_llm_only_failure", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_find_reusable_successful_acceptance_step", return_value=None),
                mock.patch.object(run_review_pipeline_module, "run_review_prerequisite_check", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_run_step", side_effect=fake_run_step),
                mock.patch.object(run_review_pipeline_module, "_run_cli_capability_preflight", return_value=None),
                mock.patch.object(run_review_pipeline_module, "_run_agent_review_post_hook", return_value=(0, {})),
            ):
                rc = run_review_pipeline_module.main()

            self.assertEqual(1, rc)
            self.assertEqual(["sc-acceptance-preflight", "sc-test", "sc-acceptance-check", "sc-llm-review"], calls)
            events = (out_dir / "run-events.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(1, sum(1 for line in events if '"event": "step_failed"' in line and '"step_name": "sc-llm-review"' in line))
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            latest = json.loads(latest_path.read_text(encoding="utf-8"))
            validate_pipeline_latest_index_payload(latest)
            self.assertEqual("fail", summary["status"])
            self.assertEqual("sc-llm-review", summary["dominant_cost_phase"])
            self.assertEqual(
                {
                    "sc-acceptance-check": 7.5,
                    "sc-llm-review": 19.0,
                    "sc-test": 11.0,
                },
                summary["step_duration_totals"],
            )
            self.assertEqual(summary["step_duration_totals"], summary["step_duration_avg"])
            self.assertTrue(latest["deterministic_bundle"]["available"])
            self.assertEqual("none", latest["deterministic_bundle"]["reuse_mode"])
            self.assertIn("sc-test", str(latest["deterministic_bundle"]["test_summary_path"]).replace("\\", "/"))

    def test_main_should_block_full_rerun_when_dirty_worktree_exceeds_change_scope_ceiling(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / "logs" / "ci" / "2026-04-07" / f"sc-review-pipeline-task-56-{run_id}"
            latest_path = tmp_root / "logs" / "ci" / "2026-04-07" / "sc-review-pipeline-task-56" / "latest.json"
            argv = [
                str(SCRIPT),
                "--task-id",
                "56",
                "--run-id",
                run_id,
                "--delivery-profile",
                "fast-ship",
                "--skip-agent-review",
            ]
            with (
                mock.patch.dict(os.environ, _stable_env(), clear=False),
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir),
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path),
                mock.patch.object(run_review_pipeline_module, "repo_root", return_value=tmp_root),
                mock.patch.object(
                    run_review_pipeline_module,
                    "_load_latest_task_execution_context",
                    return_value={
                        "delivery_profile": "fast-ship",
                        "security_profile": "host-safe",
                        "git": {"head": "previous-head", "status_short": []},
                    },
                ),
                mock.patch.object(run_review_pipeline_module, "current_git_fingerprint", return_value={"head": "current-head", "status_short": [" M docs/workflows/workflow.md"]}),
                mock.patch.object(
                    run_review_pipeline_module,
                    "classify_change_scope_between_snapshots",
                    return_value={
                        "deterministic_strategy": "full-rerun",
                        "changed_paths": [f"docs/workflows/file-{idx}.md" for idx in range(1, 25)],
                        "unsafe_paths": [f"Game.Core/Changed{idx}.cs" for idx in range(1, 11)],
                    },
                ),
                mock.patch.object(run_review_pipeline_module, "_derive_chapter6_route_guard", return_value=None),
                mock.patch.object(run_review_pipeline_module, "resolve_triplet", return_value=self._triplet()),
                mock.patch.object(run_review_pipeline_module, "_run_step") as run_step_mock,
            ):
                rc = run_review_pipeline_module.main()

            self.assertEqual(1, rc)
            run_step_mock.assert_not_called()
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            latest = json.loads(latest_path.read_text(encoding="utf-8"))
            self.assertEqual("rerun_blocked:dirty_worktree_unsafe_paths_ceiling", summary["reason"])
            self.assertTrue(summary["diagnostics"]["rerun_guard"]["blocked"])
            self.assertEqual("--allow-large-change-scope-rerun", summary["diagnostics"]["rerun_guard"]["allow_override_flag"])
            self.assertEqual(24, summary["diagnostics"]["rerun_guard"]["changed_paths_count"])
            self.assertEqual(10, summary["diagnostics"]["rerun_guard"]["unsafe_paths_count"])
            self.assertEqual("dirty_worktree_unsafe_paths_ceiling", summary["diagnostics"]["rerun_forbidden"]["kind"])
            self.assertEqual("rerun_blocked:dirty_worktree_unsafe_paths_ceiling", latest["reason"])

    def test_main_should_block_repeated_identical_sc_test_failures_before_third_full_run(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            for suffix in ("older", "latest"):
                previous_out_dir = tmp_root / "logs" / "ci" / "2026-04-06" / f"sc-review-pipeline-task-56-{suffix}"
                previous_out_dir.mkdir(parents=True, exist_ok=True)
                sc_test_dir = previous_out_dir / "sc-test-artifacts"
                sc_test_dir.mkdir(parents=True, exist_ok=True)
                (sc_test_dir / "summary.json").write_text(
                    json.dumps(
                        {
                            "cmd": "sc-test",
                            "run_id": suffix,
                            "task_id": "56",
                            "type": "all",
                            "solution": "Game.sln",
                            "configuration": "Debug",
                            "status": "fail",
                            "steps": [
                                {"name": "unit", "status": "fail", "rc": 2, "reason": "compile_error", "error": "CS0103 name missing", "log": "unit.log"},
                            ],
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                (previous_out_dir / "summary.json").write_text(
                    json.dumps(
                        {
                            "cmd": "sc-review-pipeline",
                            "task_id": "56",
                            "requested_run_id": suffix,
                            "run_id": suffix,
                            "status": "fail",
                            "steps": [
                                {
                                    "name": "sc-test",
                                    "cmd": ["py", "-3", "scripts/sc/test.py", "--task-id", "56"],
                                    "rc": 2,
                                    "status": "fail",
                                    "log": str(previous_out_dir / "sc-test.log"),
                                    "reported_out_dir": str(sc_test_dir),
                                    "summary_file": str(sc_test_dir / "summary.json"),
                                }
                            ],
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                (previous_out_dir / "execution-context.json").write_text(
                    json.dumps(
                        {
                            "run_id": suffix,
                            "delivery_profile": "fast-ship",
                            "security_profile": "host-safe",
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )

            out_dir = tmp_root / "logs" / "ci" / "2026-04-07" / f"sc-review-pipeline-task-56-{run_id}"
            latest_path = tmp_root / "logs" / "ci" / "2026-04-07" / "sc-review-pipeline-task-56" / "latest.json"
            argv = [
                str(SCRIPT),
                "--task-id",
                "56",
                "--run-id",
                run_id,
                "--delivery-profile",
                "fast-ship",
                "--skip-agent-review",
            ]
            with (
                mock.patch.dict(os.environ, _stable_env(), clear=False),
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir),
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path),
                mock.patch.object(run_review_pipeline_module, "repo_root", return_value=tmp_root),
                mock.patch.object(run_review_pipeline_module, "resolve_triplet", return_value=self._triplet()),
                mock.patch.object(run_review_pipeline_module, "_run_step") as run_step_mock,
            ):
                rc = run_review_pipeline_module.main()

            self.assertEqual(1, rc)
            run_step_mock.assert_not_called()
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("rerun_blocked:repeat_deterministic_failure", summary["reason"])
            self.assertEqual("repeat_deterministic_failure", summary["diagnostics"]["rerun_guard"]["kind"])
            self.assertTrue(summary["diagnostics"]["rerun_guard"]["blocked"])
            self.assertTrue(str(summary["diagnostics"]["rerun_guard"]["fingerprint"]).startswith("sc-test|unit|2|compile_error"))

    def test_main_should_block_repeated_review_needs_fix_before_llm_only_rerun(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            for suffix in ("older", "latest"):
                previous_out_dir = tmp_root / "logs" / "ci" / "2026-04-06" / f"sc-review-pipeline-task-56-{suffix}"
                previous_out_dir.mkdir(parents=True, exist_ok=True)
                (previous_out_dir / "summary.json").write_text(
                    json.dumps(
                        {
                            "cmd": "sc-review-pipeline",
                            "task_id": "56",
                            "requested_run_id": suffix,
                            "run_id": suffix,
                            "status": "ok",
                            "reason": "pipeline_clean",
                            "steps": [
                                {"name": "sc-test", "status": "ok", "rc": 0, "log": str(previous_out_dir / "sc-test.log")},
                                {
                                    "name": "sc-acceptance-check",
                                    "status": "ok",
                                    "rc": 0,
                                    "log": str(previous_out_dir / "sc-acceptance-check.log"),
                                },
                                {
                                    "name": "sc-llm-review",
                                    "status": "ok",
                                    "rc": 0,
                                    "log": str(previous_out_dir / "sc-llm-review.log"),
                                },
                            ],
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                (previous_out_dir / "repair-guide.json").write_text(
                    json.dumps({"status": "needs-fix"}, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                (previous_out_dir / "execution-context.json").write_text(
                    json.dumps(
                        {
                            "run_id": suffix,
                            "delivery_profile": "fast-ship",
                            "security_profile": "host-safe",
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )

            out_dir = tmp_root / "logs" / "ci" / "2026-04-07" / f"sc-review-pipeline-task-56-{run_id}"
            latest_path = tmp_root / "logs" / "ci" / "2026-04-07" / "sc-review-pipeline-task-56" / "latest.json"
            argv = [
                str(SCRIPT),
                "--task-id",
                "56",
                "--run-id",
                run_id,
                "--delivery-profile",
                "fast-ship",
                "--skip-test",
                "--skip-acceptance",
            ]
            with (
                mock.patch.dict(os.environ, _stable_env(), clear=False),
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir),
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path),
                mock.patch.object(run_review_pipeline_module, "repo_root", return_value=tmp_root),
                mock.patch.object(run_review_pipeline_module, "resolve_triplet", return_value=self._triplet()),
                mock.patch.object(run_review_pipeline_module, "_run_step") as run_step_mock,
            ):
                rc = run_review_pipeline_module.main()

            self.assertEqual(1, rc)
            run_step_mock.assert_not_called()
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("rerun_blocked:repeat_review_needs_fix", summary["reason"])
            self.assertEqual("needs-fix-fast", summary["recommended_action"])
            self.assertIn("needs fix family", summary["recommended_action_why"].lower())
            self.assertEqual("repeat_review_needs_fix", summary["diagnostics"]["rerun_guard"]["kind"])
            self.assertTrue(summary["diagnostics"]["rerun_guard"]["blocked"])
            self.assertEqual("needs-fix-fast", summary["diagnostics"]["rerun_guard"]["recommended_path"])


if __name__ == "__main__":
    unittest.main()
