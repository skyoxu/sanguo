#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
import uuid
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
sys.path.insert(0, str(SC_DIR))

import run_review_pipeline as run_review_pipeline_module  # noqa: E402


def _stable_env() -> dict[str, str]:
    env = dict(os.environ)
    for key in (
        "DELIVERY_PROFILE",
        "SECURITY_PROFILE",
        "SC_PIPELINE_RUN_ID",
        "SC_TEST_RUN_ID",
        "SC_ACCEPTANCE_RUN_ID",
    ):
        env.pop(key, None)
    return env


class RunReviewPipelineMarathonTests(unittest.TestCase):
    def setUp(self) -> None:
        self._review_preflight_patcher = mock.patch.object(
            run_review_pipeline_module,
            "run_review_prerequisite_check",
            return_value=None,
        )
        self._review_preflight_patcher.start()
        self.addCleanup(self._review_preflight_patcher.stop)

    def test_find_reusable_sc_test_step_should_pick_matching_failed_pipeline_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out_dir = root / "logs" / "ci" / "2026-03-31" / "sc-review-pipeline-task-1-newrun"
            out_dir.mkdir(parents=True, exist_ok=True)
            source_run = root / "logs" / "ci" / "2026-03-30" / "sc-review-pipeline-task-1-oldrun"
            source_run.mkdir(parents=True, exist_ok=True)
            child_sc_test = source_run / "child-artifacts" / "sc-test"
            child_sc_test.mkdir(parents=True, exist_ok=True)
            (child_sc_test / "summary.json").write_text(
                json.dumps(
                    {
                        "cmd": "sc-test",
                        "run_id": "a" * 32,
                        "type": "unit",
                        "solution": "Game.sln",
                        "configuration": "Debug",
                        "status": "ok",
                        "steps": [],
                        "task_id": "1",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (source_run / "summary.json").write_text(
                json.dumps(
                    {
                        "cmd": "sc-review-pipeline",
                        "task_id": "1",
                        "requested_run_id": "oldrun",
                        "run_id": "oldrun",
                        "allow_overwrite": False,
                        "force_new_run_id": False,
                        "status": "fail",
                        "steps": [
                            {
                                "name": "sc-test",
                                "cmd": ["py", "-3", "scripts/sc/test.py", "--type", "unit", "--task-id", "1", "--run-id", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "--delivery-profile", "fast-ship"],
                                "rc": 0,
                                "status": "ok",
                                "log": str(source_run / "sc-test.log"),
                                "reported_out_dir": str(child_sc_test),
                                "summary_file": str(child_sc_test / "summary.json"),
                            },
                            {
                                "name": "sc-acceptance-check",
                                "cmd": ["py", "-3", "scripts/sc/acceptance_check.py"],
                                "rc": 1,
                                "status": "fail",
                                "log": str(source_run / "sc-acceptance-check.log"),
                                "reported_out_dir": "",
                                "summary_file": "",
                            },
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (source_run / "execution-context.json").write_text(
                json.dumps(
                    {
                        "delivery_profile": "fast-ship",
                        "security_profile": "host-safe",
                        "git": {"head": "abc123", "status_short": [" M scripts/sc/run_review_pipeline.py"]},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            with mock.patch.object(run_review_pipeline_module, "repo_root", return_value=root):
                step = run_review_pipeline_module._find_reusable_sc_test_step(
                    out_dir=out_dir,
                    task_id="1",
                    delivery_profile="fast-ship",
                    security_profile="host-safe",
                    planned_cmd=["py", "-3", "scripts/sc/test.py", "--type", "unit", "--task-id", "1", "--run-id", "b" * 32, "--delivery-profile", "fast-ship"],
                    git_fingerprint={"head": "abc123", "status_short": [" M scripts/sc/run_review_pipeline.py"]},
                )

            self.assertIsNotNone(step)
            assert step is not None
            self.assertEqual("ok", step["status"])
            self.assertTrue((out_dir / "child-artifacts" / "sc-test" / "summary.json").exists())
            self.assertIn("reused sc-test", Path(step["log"]).read_text(encoding="utf-8"))

    def test_find_reusable_sc_test_step_should_allow_semantic_only_git_delta(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out_dir = root / "logs" / "ci" / "2026-03-31" / "sc-review-pipeline-task-1-newrun"
            out_dir.mkdir(parents=True, exist_ok=True)
            source_run = root / "logs" / "ci" / "2026-03-30" / "sc-review-pipeline-task-1-oldrun"
            source_run.mkdir(parents=True, exist_ok=True)
            child_sc_test = source_run / "child-artifacts" / "sc-test"
            child_sc_test.mkdir(parents=True, exist_ok=True)
            (child_sc_test / "summary.json").write_text(
                json.dumps(
                    {
                        "cmd": "sc-test",
                        "run_id": "a" * 32,
                        "type": "unit",
                        "solution": "Game.sln",
                        "configuration": "Debug",
                        "status": "ok",
                        "steps": [],
                        "task_id": "1",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (source_run / "summary.json").write_text(
                json.dumps(
                    {
                        "cmd": "sc-review-pipeline",
                        "task_id": "1",
                        "requested_run_id": "oldrun",
                        "run_id": "oldrun",
                        "allow_overwrite": False,
                        "force_new_run_id": False,
                        "status": "fail",
                        "steps": [
                            {
                                "name": "sc-test",
                                "cmd": ["py", "-3", "scripts/sc/test.py", "--type", "unit", "--task-id", "1", "--run-id", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "--delivery-profile", "fast-ship"],
                                "rc": 0,
                                "status": "ok",
                                "log": str(source_run / "sc-test.log"),
                                "reported_out_dir": str(child_sc_test),
                                "summary_file": str(child_sc_test / "summary.json"),
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (source_run / "execution-context.json").write_text(
                json.dumps(
                    {
                        "delivery_profile": "fast-ship",
                        "security_profile": "host-safe",
                        "git": {"head": "abc123", "status_short": []},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            with (
                mock.patch.object(run_review_pipeline_module, "repo_root", return_value=root),
                mock.patch.object(
                    run_review_pipeline_module,
                    "classify_change_scope_between_snapshots",
                    return_value={
                        "sc_test_reuse_allowed": True,
                        "deterministic_strategy": "minimal-acceptance",
                        "changed_paths": [".taskmaster/tasks/tasks_back.json"],
                        "unsafe_paths": [],
                    },
                ),
            ):
                step = run_review_pipeline_module._find_reusable_sc_test_step(
                    out_dir=out_dir,
                    task_id="1",
                    delivery_profile="fast-ship",
                    security_profile="host-safe",
                    planned_cmd=["py", "-3", "scripts/sc/test.py", "--type", "unit", "--task-id", "1", "--run-id", "b" * 32, "--delivery-profile", "fast-ship"],
                    git_fingerprint={"head": "def456", "status_short": []},
                )

            self.assertIsNotNone(step)
            assert step is not None
            self.assertEqual("ok", step["status"])
            self.assertIn("semantic-only", Path(step["log"]).read_text(encoding="utf-8"))

    def test_find_reusable_sc_test_step_should_not_relax_git_delta_in_standard_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out_dir = root / "logs" / "ci" / "2026-03-31" / "sc-review-pipeline-task-1-newrun"
            out_dir.mkdir(parents=True, exist_ok=True)
            source_run = root / "logs" / "ci" / "2026-03-30" / "sc-review-pipeline-task-1-oldrun"
            source_run.mkdir(parents=True, exist_ok=True)
            child_sc_test = source_run / "child-artifacts" / "sc-test"
            child_sc_test.mkdir(parents=True, exist_ok=True)
            (child_sc_test / "summary.json").write_text(
                json.dumps(
                    {
                        "cmd": "sc-test",
                        "run_id": "a" * 32,
                        "type": "unit",
                        "solution": "Game.sln",
                        "configuration": "Debug",
                        "status": "ok",
                        "steps": [],
                        "task_id": "1",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (source_run / "summary.json").write_text(
                json.dumps(
                    {
                        "cmd": "sc-review-pipeline",
                        "task_id": "1",
                        "requested_run_id": "oldrun",
                        "run_id": "oldrun",
                        "allow_overwrite": False,
                        "force_new_run_id": False,
                        "status": "fail",
                        "steps": [
                            {
                                "name": "sc-test",
                                "cmd": ["py", "-3", "scripts/sc/test.py", "--type", "unit", "--task-id", "1", "--run-id", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "--delivery-profile", "standard"],
                                "rc": 0,
                                "status": "ok",
                                "log": str(source_run / "sc-test.log"),
                                "reported_out_dir": str(child_sc_test),
                                "summary_file": str(child_sc_test / "summary.json"),
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (source_run / "execution-context.json").write_text(
                json.dumps(
                    {
                        "delivery_profile": "standard",
                        "security_profile": "strict",
                        "git": {"head": "abc123", "status_short": []},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            with (
                mock.patch.object(run_review_pipeline_module, "repo_root", return_value=root),
                mock.patch.object(
                    run_review_pipeline_module,
                    "classify_change_scope_between_snapshots",
                    return_value={
                        "sc_test_reuse_allowed": True,
                        "deterministic_strategy": "minimal-acceptance",
                        "changed_paths": [".taskmaster/tasks/tasks_back.json"],
                        "unsafe_paths": [],
                    },
                ),
            ):
                step = run_review_pipeline_module._find_reusable_sc_test_step(
                    out_dir=out_dir,
                    task_id="1",
                    delivery_profile="standard",
                    security_profile="strict",
                    planned_cmd=["py", "-3", "scripts/sc/test.py", "--type", "unit", "--task-id", "1", "--run-id", "b" * 32, "--delivery-profile", "standard"],
                    git_fingerprint={"head": "def456", "status_short": []},
                )

            self.assertIsNone(step)

    def test_pipeline_should_reuse_matching_sc_test_before_running_acceptance(self) -> None:
        run_id = uuid.uuid4().hex
        previous_run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-1-{run_id}"
            latest_path = tmp_root / "sc-review-pipeline-task-1" / "latest.json"
            reused_out_dir = tmp_root / f"sc-review-pipeline-task-1-{previous_run_id}"
            reused_out_dir.mkdir(parents=True, exist_ok=True)
            (reused_out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "cmd": "sc-review-pipeline",
                        "task_id": "1",
                        "requested_run_id": previous_run_id,
                        "run_id": previous_run_id,
                        "allow_overwrite": False,
                        "force_new_run_id": False,
                        "status": "fail",
                        "steps": [
                            {
                                "name": "sc-test",
                                "cmd": ["py", "-3", "scripts/sc/test.py", "--type", "unit", "--task-id", "1", "--run-id", previous_run_id, "--delivery-profile", "fast-ship"],
                                "rc": 0,
                                "status": "ok",
                                "log": str(reused_out_dir / "sc-test.log"),
                                "reported_out_dir": str(reused_out_dir / "child-artifacts" / "sc-test"),
                                "summary_file": str(reused_out_dir / "child-artifacts" / "sc-test" / "summary.json"),
                            },
                            {
                                "name": "sc-acceptance-check",
                                "cmd": ["py", "-3", "scripts/sc/acceptance_check.py"],
                                "rc": 1,
                                "status": "fail",
                                "log": str(reused_out_dir / "sc-acceptance-check.log"),
                                "reported_out_dir": "",
                                "summary_file": "",
                            },
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            child_sc_test = reused_out_dir / "child-artifacts" / "sc-test"
            child_sc_test.mkdir(parents=True, exist_ok=True)
            (child_sc_test / "summary.json").write_text(
                json.dumps(
                    {
                        "cmd": "sc-test",
                        "run_id": previous_run_id,
                        "type": "unit",
                        "solution": "Game.sln",
                        "configuration": "Debug",
                        "status": "ok",
                        "steps": [],
                        "task_id": "1",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (reused_out_dir / "execution-context.json").write_text(
                json.dumps(
                    {
                        "security_profile": "host-safe",
                        "delivery_profile": "fast-ship",
                        "git": {"head": "abc123", "status_short": [" M scripts/sc/run_review_pipeline.py"]},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            calls: list[str] = []

            def fake_run_step(*, out_dir: Path, name: str, cmd: list[str], timeout_sec: int) -> dict:
                calls.append(name)
                return {
                    "name": name,
                    "cmd": cmd,
                    "rc": 0,
                    "status": "ok",
                    "log": str(out_dir / f"{name}.log"),
                    "reported_out_dir": "",
                    "summary_file": "",
                }

            argv = [
                str(REPO_ROOT / "scripts" / "sc" / "run_review_pipeline.py"),
                "--task-id",
                "1",
                "--run-id",
                run_id,
                "--delivery-profile",
                "fast-ship",
                "--skip-agent-review",
                "--skip-llm-review",
            ]
            with mock.patch.dict(os.environ, _stable_env(), clear=False), \
                mock.patch.object(sys, "argv", argv), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path), \
                mock.patch.object(run_review_pipeline_module, "_load_latest_task_execution_context", return_value=None), \
                mock.patch.object(run_review_pipeline_module, "_run_step", side_effect=fake_run_step), \
                mock.patch.object(run_review_pipeline_module, "_run_cli_capability_preflight", return_value=None), \
                mock.patch.object(
                    run_review_pipeline_module,
                    "_find_reusable_sc_test_step",
                    return_value={
                        "name": "sc-test",
                        "cmd": ["py", "-3", "scripts/sc/test.py"],
                        "rc": 0,
                        "status": "ok",
                        "log": str(out_dir / "sc-test.log"),
                        "reported_out_dir": str(out_dir / "child-artifacts" / "sc-test"),
                        "summary_file": str(out_dir / "child-artifacts" / "sc-test" / "summary.json"),
                    },
                ), \
                mock.patch.object(
                    run_review_pipeline_module,
                    "current_git_fingerprint",
                    return_value={"head": "abc123", "status_short": [" M scripts/sc/run_review_pipeline.py"]},
                ):
                rc = run_review_pipeline_module.main()

            self.assertEqual(0, rc)
            self.assertNotIn("sc-test", calls)
            self.assertIn("sc-acceptance-preflight", calls)
            self.assertIn("sc-acceptance-check", calls)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            step_names = [item["name"] for item in summary["steps"]]
            self.assertIn("sc-test", step_names)
            self.assertEqual("ok", next(item for item in summary["steps"] if item["name"] == "sc-test")["status"])
    def test_agent_review_post_hook_should_update_marathon_state_and_repair_guide(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-1-{run_id}"
            latest_path = tmp_root / "sc-review-pipeline-task-1" / "latest.json"
            payload = {
                "schema_version": "1.0.0",
                "cmd": "sc-agent-review",
                "date": "2026-03-20",
                "reviewer": "artifact-reviewer",
                "task_id": "1",
                "run_id": run_id,
                "pipeline_out_dir": str(out_dir),
                "pipeline_status": "ok",
                "failed_step": "",
                "review_verdict": "block",
                "findings": [
                    {
                        "finding_id": "sc-test-failed",
                        "severity": "high",
                        "category": "pipeline-step-failed",
                        "owner_step": "sc-test",
                        "evidence_path": str(out_dir / "sc-test.log"),
                        "message": "sc-test failed",
                        "suggested_fix": "Fix sc-test first",
                        "commands": ["py -3 scripts/sc/test.py --task-id 1"],
                    },
                    {
                        "finding_id": "llm-needs-fix",
                        "severity": "medium",
                        "category": "llm-review",
                        "owner_step": "sc-llm-review",
                        "evidence_path": str(out_dir / "llm.json"),
                        "message": "Needs Fix",
                        "suggested_fix": "Resolve llm findings",
                        "commands": [],
                    },
                ],
            }

            def fake_run_step(*, out_dir: Path, name: str, cmd: list[str], timeout_sec: int) -> dict:
                return {
                    "name": name,
                    "cmd": cmd,
                    "rc": 0,
                    "status": "ok",
                    "log": str(out_dir / f"{name}.log"),
                    "reported_out_dir": "",
                    "summary_file": "",
                }

            argv = [
                str(REPO_ROOT / "scripts" / "sc" / "run_review_pipeline.py"),
                "--task-id",
                "1",
                "--run-id",
                run_id,
                "--delivery-profile",
                "standard",
            ]
            with mock.patch.dict(os.environ, _stable_env(), clear=False), \
                mock.patch.object(sys, "argv", argv), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path), \
                mock.patch.object(run_review_pipeline_module, "_load_latest_task_execution_context", return_value=None), \
                mock.patch.object(run_review_pipeline_module, "_find_recent_deterministic_green_llm_not_clean_run", return_value=None), \
                mock.patch.object(run_review_pipeline_module, "_find_repeated_deterministic_failure_guard", return_value=None), \
                mock.patch.object(run_review_pipeline_module, "_derive_chapter6_route_guard", return_value=None), \
                mock.patch.object(run_review_pipeline_module, "_run_step", side_effect=fake_run_step), \
                mock.patch.object(run_review_pipeline_module, "write_agent_review", return_value=(payload, [], [])):
                rc = run_review_pipeline_module.main()

            self.assertEqual(1, rc)
            marathon_state = json.loads((out_dir / "marathon-state.json").read_text(encoding="utf-8"))
            repair_guide = json.loads((out_dir / "repair-guide.json").read_text(encoding="utf-8"))
            execution_context = json.loads((out_dir / "execution-context.json").read_text(encoding="utf-8"))

            self.assertEqual("fork", marathon_state["agent_review"]["recommended_action"])
            self.assertTrue(marathon_state["context_refresh_needed"])
            self.assertIn("agent_review_cross_step_block", marathon_state["context_refresh_reasons"])
            self.assertEqual("fork", execution_context["agent_review"]["recommended_action"])
            ids = {item["id"] for item in repair_guide["recommendations"]}
            self.assertIn("pipeline-context-refresh", ids)
            self.assertIn("approval-fork-pending", ids)
            self.assertNotIn("pipeline-fork", ids)

    def test_warn_mode_fork_recommendation_should_write_soft_approval_request(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-1-{run_id}"
            latest_path = tmp_root / "sc-review-pipeline-task-1" / "latest.json"
            payload = {
                "schema_version": "1.0.0",
                "cmd": "sc-agent-review",
                "date": "2026-03-20",
                "reviewer": "artifact-reviewer",
                "task_id": "1",
                "run_id": run_id,
                "pipeline_out_dir": str(out_dir),
                "pipeline_status": "ok",
                "failed_step": "",
                "review_verdict": "block",
                "findings": [
                    {
                        "finding_id": "summary-integrity",
                        "severity": "medium",
                        "category": "summary-integrity",
                        "owner_step": "producer-pipeline",
                        "evidence_path": str(out_dir / "summary.json"),
                        "message": "Summary contract drift",
                        "suggested_fix": "Fork a clean recovery run",
                        "commands": [],
                    }
                ],
            }

            def fake_run_step(*, out_dir: Path, name: str, cmd: list[str], timeout_sec: int) -> dict:
                return {
                    "name": name,
                    "cmd": cmd,
                    "rc": 0,
                    "status": "ok",
                    "log": str(out_dir / f"{name}.log"),
                    "reported_out_dir": "",
                    "summary_file": "",
                }

            argv = [
                str(REPO_ROOT / "scripts" / "sc" / "run_review_pipeline.py"),
                "--task-id",
                "1",
                "--run-id",
                run_id,
                "--delivery-profile",
                "fast-ship",
            ]
            with mock.patch.dict(os.environ, _stable_env(), clear=False), \
                mock.patch.object(sys, "argv", argv), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path), \
                mock.patch.object(run_review_pipeline_module, "_load_latest_task_execution_context", return_value=None), \
                mock.patch.object(run_review_pipeline_module, "_run_step", side_effect=fake_run_step), \
                mock.patch.object(run_review_pipeline_module, "write_agent_review", return_value=(payload, [], [])):
                rc = run_review_pipeline_module.main()

            self.assertEqual(1, rc)
            request = json.loads((out_dir / "approval-request.json").read_text(encoding="utf-8"))
            latest = json.loads(latest_path.read_text(encoding="utf-8"))
            execution_context = json.loads((out_dir / "execution-context.json").read_text(encoding="utf-8"))
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))

            self.assertEqual("fork", request["action"])
            self.assertEqual("pending", request["status"])
            self.assertIn("run_review_pipeline.py --task-id 1 --fork", " ".join(request["requested_commands"]))
            self.assertEqual(str(out_dir / "approval-request.json"), latest["approval_request_path"])
            self.assertEqual("pending", execution_context["approval"]["status"])
            self.assertEqual("fork", execution_context["approval"]["required_action"])
            self.assertEqual("fail", summary["status"])

    def test_existing_approval_response_should_be_indexed_as_soft_signal(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-1-{run_id}"
            latest_path = tmp_root / "sc-review-pipeline-task-1" / "latest.json"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "cmd": "sc-review-pipeline",
                        "task_id": "1",
                        "requested_run_id": run_id,
                        "run_id": run_id,
                        "allow_overwrite": False,
                        "force_new_run_id": False,
                        "status": "ok",
                        "steps": [],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (out_dir / "marathon-state.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "task_id": "1",
                        "run_id": run_id,
                        "requested_run_id": run_id,
                        "status": "running",
                        "resume_count": 1,
                        "max_step_retries": 0,
                        "max_wall_time_sec": 0,
                        "created_at": "2000-01-01T00:00:00",
                        "updated_at": "2000-01-01T00:00:00",
                        "last_completed_step": "",
                        "last_failed_step": "",
                        "next_step_name": "sc-test",
                        "steps": {},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (out_dir / "approval-response.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "request_id": f"{run_id}:fork",
                        "decision": "approved",
                        "reviewer": "human",
                        "reason": "Fork is acceptable",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            latest_path.parent.mkdir(parents=True, exist_ok=True)
            latest_path.write_text(
                json.dumps(
                    {
                        "task_id": "1",
                        "run_id": run_id,
                        "status": "running",
                        "latest_out_dir": str(out_dir),
                        "summary_path": str(out_dir / "summary.json"),
                        "marathon_state_path": str(out_dir / "marathon-state.json"),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            payload = {
                "schema_version": "1.0.0",
                "cmd": "sc-agent-review",
                "date": "2026-03-20",
                "reviewer": "artifact-reviewer",
                "task_id": "1",
                "run_id": run_id,
                "pipeline_out_dir": str(out_dir),
                "pipeline_status": "ok",
                "failed_step": "",
                "review_verdict": "block",
                "findings": [
                    {
                        "finding_id": "summary-integrity",
                        "severity": "medium",
                        "category": "summary-integrity",
                        "owner_step": "producer-pipeline",
                        "evidence_path": str(out_dir / "summary.json"),
                        "message": "Summary contract drift",
                        "suggested_fix": "Fork a clean recovery run",
                        "commands": [],
                    }
                ],
            }

            def fake_run_step(*, out_dir: Path, name: str, cmd: list[str], timeout_sec: int) -> dict:
                return {
                    "name": name,
                    "cmd": cmd,
                    "rc": 0,
                    "status": "ok",
                    "log": str(out_dir / f"{name}.log"),
                    "reported_out_dir": "",
                    "summary_file": "",
                }

            argv = [
                str(REPO_ROOT / "scripts" / "sc" / "run_review_pipeline.py"),
                "--task-id",
                "1",
                "--resume",
                "--delivery-profile",
                "fast-ship",
            ]
            with mock.patch.dict(os.environ, _stable_env(), clear=False), \
                mock.patch.object(sys, "argv", argv), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path), \
                mock.patch.object(run_review_pipeline_module, "_run_step", side_effect=fake_run_step), \
                mock.patch.object(run_review_pipeline_module, "write_agent_review", return_value=(payload, [], [])):
                rc = run_review_pipeline_module.main()

            self.assertEqual(0, rc)
            latest = json.loads(latest_path.read_text(encoding="utf-8"))
            execution_context = json.loads((out_dir / "execution-context.json").read_text(encoding="utf-8"))

            self.assertEqual(str(out_dir / "approval-response.json"), latest["approval_response_path"])
            self.assertEqual("approved", execution_context["approval"]["status"])
            self.assertEqual("approved", execution_context["approval"]["decision"])

    def test_resume_should_stop_when_fork_approval_is_pending(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-1-{run_id}"
            latest_path = tmp_root / "sc-review-pipeline-task-1" / "latest.json"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "cmd": "sc-review-pipeline",
                        "task_id": "1",
                        "requested_run_id": run_id,
                        "run_id": run_id,
                        "allow_overwrite": False,
                        "force_new_run_id": False,
                        "status": "fail",
                        "steps": [],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (out_dir / "marathon-state.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "task_id": "1",
                        "run_id": run_id,
                        "requested_run_id": run_id,
                        "status": "running",
                        "resume_count": 1,
                        "max_step_retries": 0,
                        "max_wall_time_sec": 0,
                        "created_at": "2000-01-01T00:00:00",
                        "updated_at": "2000-01-01T00:00:00",
                        "last_completed_step": "",
                        "last_failed_step": "",
                        "next_step_name": "sc-test",
                        "steps": {},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (out_dir / "approval-request.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "request_id": f"{run_id}:fork",
                        "task_id": "1",
                        "run_id": run_id,
                        "action": "fork",
                        "reason": "Await approval before forking.",
                        "requested_files": [],
                        "requested_commands": [f"py -3 scripts/sc/run_review_pipeline.py --task-id 1 --fork"],
                        "status": "pending",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            latest_path.parent.mkdir(parents=True, exist_ok=True)
            latest_path.write_text(
                json.dumps(
                    {
                        "task_id": "1",
                        "run_id": run_id,
                        "status": "running",
                        "latest_out_dir": str(out_dir),
                        "summary_path": str(out_dir / "summary.json"),
                        "marathon_state_path": str(out_dir / "marathon-state.json"),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            argv = [
                str(REPO_ROOT / "scripts" / "sc" / "run_review_pipeline.py"),
                "--task-id",
                "1",
                "--resume",
                "--delivery-profile",
                "fast-ship",
            ]
            stdout = io.StringIO()
            with mock.patch.dict(os.environ, _stable_env(), clear=False), \
                mock.patch.object(sys, "argv", argv), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path), \
                redirect_stdout(stdout):
                rc = run_review_pipeline_module.main()

            self.assertEqual(2, rc)
            self.assertIn("fork approval is pending", stdout.getvalue())

    def test_fork_should_stop_when_fork_approval_is_denied(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-1-{run_id}"
            latest_path = tmp_root / "sc-review-pipeline-task-1" / "latest.json"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "cmd": "sc-review-pipeline",
                        "task_id": "1",
                        "requested_run_id": run_id,
                        "run_id": run_id,
                        "allow_overwrite": False,
                        "force_new_run_id": False,
                        "status": "fail",
                        "steps": [],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (out_dir / "marathon-state.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "task_id": "1",
                        "run_id": run_id,
                        "requested_run_id": run_id,
                        "status": "running",
                        "resume_count": 1,
                        "max_step_retries": 0,
                        "max_wall_time_sec": 0,
                        "created_at": "2000-01-01T00:00:00",
                        "updated_at": "2000-01-01T00:00:00",
                        "last_completed_step": "",
                        "last_failed_step": "",
                        "next_step_name": "sc-test",
                        "steps": {},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (out_dir / "approval-request.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "request_id": f"{run_id}:fork",
                        "task_id": "1",
                        "run_id": run_id,
                        "action": "fork",
                        "reason": "Fork approval was requested.",
                        "requested_files": [],
                        "requested_commands": [f"py -3 scripts/sc/run_review_pipeline.py --task-id 1 --fork"],
                        "status": "pending",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (out_dir / "approval-response.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "request_id": f"{run_id}:fork",
                        "decision": "denied",
                        "reviewer": "human",
                        "reason": "Stay on the current run.",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            latest_path.parent.mkdir(parents=True, exist_ok=True)
            latest_path.write_text(
                json.dumps(
                    {
                        "task_id": "1",
                        "run_id": run_id,
                        "status": "running",
                        "latest_out_dir": str(out_dir),
                        "summary_path": str(out_dir / "summary.json"),
                        "marathon_state_path": str(out_dir / "marathon-state.json"),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            argv = [
                str(REPO_ROOT / "scripts" / "sc" / "run_review_pipeline.py"),
                "--task-id",
                "1",
                "--fork",
                "--run-id",
                uuid.uuid4().hex,
                "--delivery-profile",
                "fast-ship",
            ]
            stdout = io.StringIO()
            with mock.patch.dict(os.environ, _stable_env(), clear=False), \
                mock.patch.object(sys, "argv", argv), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path), \
                redirect_stdout(stdout):
                rc = run_review_pipeline_module.main()

            self.assertEqual(2, rc)
            self.assertIn("fork approval was denied", stdout.getvalue())

    def test_resume_should_stop_when_fork_approval_is_mismatched(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-1-{run_id}"
            latest_path = tmp_root / "sc-review-pipeline-task-1" / "latest.json"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "cmd": "sc-review-pipeline",
                        "task_id": "1",
                        "requested_run_id": run_id,
                        "run_id": run_id,
                        "allow_overwrite": False,
                        "force_new_run_id": False,
                        "status": "fail",
                        "steps": [],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (out_dir / "marathon-state.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "task_id": "1",
                        "run_id": run_id,
                        "requested_run_id": run_id,
                        "status": "running",
                        "resume_count": 1,
                        "max_step_retries": 0,
                        "max_wall_time_sec": 0,
                        "created_at": "2000-01-01T00:00:00",
                        "updated_at": "2000-01-01T00:00:00",
                        "last_completed_step": "",
                        "last_failed_step": "",
                        "next_step_name": "sc-test",
                        "steps": {},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (out_dir / "approval-request.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "request_id": f"{run_id}:fork",
                        "task_id": "1",
                        "run_id": run_id,
                        "action": "fork",
                        "reason": "Fork approval was requested.",
                        "requested_files": [],
                        "requested_commands": [f"py -3 scripts/sc/run_review_pipeline.py --task-id 1 --fork"],
                        "status": "pending",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (out_dir / "approval-response.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "request_id": "wrong-run:fork",
                        "decision": "approved",
                        "reviewer": "human",
                        "reason": "Approved the wrong request.",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            latest_path.parent.mkdir(parents=True, exist_ok=True)
            latest_path.write_text(
                json.dumps(
                    {
                        "task_id": "1",
                        "run_id": run_id,
                        "status": "running",
                        "latest_out_dir": str(out_dir),
                        "summary_path": str(out_dir / "summary.json"),
                        "marathon_state_path": str(out_dir / "marathon-state.json"),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            argv = [
                str(REPO_ROOT / "scripts" / "sc" / "run_review_pipeline.py"),
                "--task-id",
                "1",
                "--resume",
                "--delivery-profile",
                "fast-ship",
            ]
            stdout = io.StringIO()
            with mock.patch.dict(os.environ, _stable_env(), clear=False), \
                mock.patch.object(sys, "argv", argv), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path), \
                redirect_stdout(stdout):
                rc = run_review_pipeline_module.main()

            self.assertEqual(2, rc)
            self.assertIn("invalid or mismatched", stdout.getvalue())

    def test_dry_run_should_mark_context_refresh_when_diff_growth_exceeds_threshold(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-1-{run_id}"
            latest_path = tmp_root / "sc-review-pipeline-task-1" / "latest.json"

            def fake_refresh(state: dict) -> dict:
                state["diff_stats"] = {
                    "baseline": {"total_lines": 15, "files_changed": 2, "untracked_files": 0},
                    "current": {"total_lines": 145, "files_changed": 8, "untracked_files": 1},
                    "growth": {"total_lines": 130, "files_changed": 6, "untracked_files": 1},
                }
                return state

            argv = [
                str(REPO_ROOT / "scripts" / "sc" / "run_review_pipeline.py"),
                "--task-id",
                "1",
                "--run-id",
                run_id,
                "--dry-run",
                "--skip-agent-review",
                "--skip-llm-review",
                "--context-refresh-after-diff-lines",
                "100",
            ]
            with mock.patch.dict(os.environ, _stable_env(), clear=False), \
                mock.patch.object(sys, "argv", argv), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path), \
                mock.patch.object(run_review_pipeline_module, "_refresh_diff_stats", side_effect=fake_refresh):
                rc = run_review_pipeline_module.main()

            self.assertEqual(0, rc)
            marathon_state = json.loads((out_dir / "marathon-state.json").read_text(encoding="utf-8"))
            repair_guide = json.loads((out_dir / "repair-guide.json").read_text(encoding="utf-8"))

            self.assertTrue(marathon_state["context_refresh_needed"])
            self.assertIn("diff_lines_growth>=100(15->145)", marathon_state["context_refresh_reasons"])
            ids = {item["id"] for item in repair_guide["recommendations"]}
            self.assertIn("pipeline-context-refresh", ids)

    def test_resume_should_stop_when_max_wall_time_exceeded(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-1-{run_id}"
            latest_path = tmp_root / "sc-review-pipeline-task-1" / "latest.json"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "cmd": "sc-review-pipeline",
                        "task_id": "1",
                        "requested_run_id": run_id,
                        "run_id": run_id,
                        "allow_overwrite": False,
                        "force_new_run_id": False,
                        "status": "ok",
                        "steps": [
                            {"name": "sc-test", "cmd": ["py", "-3", "scripts/sc/test.py"], "rc": 0, "status": "ok", "log": "x.log"}
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (out_dir / "marathon-state.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "task_id": "1",
                        "run_id": run_id,
                        "requested_run_id": run_id,
                        "status": "running",
                        "resume_count": 1,
                        "max_step_retries": 0,
                        "max_wall_time_sec": 1,
                        "created_at": "2000-01-01T00:00:00",
                        "updated_at": "2000-01-01T00:00:00",
                        "last_completed_step": "sc-test",
                        "last_failed_step": "",
                        "next_step_name": "sc-acceptance-check",
                        "steps": {
                            "sc-test": {"attempt_count": 1, "status": "ok", "last_rc": 0},
                            "sc-acceptance-check": {"attempt_count": 0, "status": "pending", "last_rc": 0},
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            latest_path.parent.mkdir(parents=True, exist_ok=True)
            latest_path.write_text(
                json.dumps(
                    {
                        "task_id": "1",
                        "run_id": run_id,
                        "status": "running",
                        "latest_out_dir": str(out_dir),
                        "summary_path": str(out_dir / "summary.json"),
                        "marathon_state_path": str(out_dir / "marathon-state.json"),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            argv = [
                str(REPO_ROOT / "scripts" / "sc" / "run_review_pipeline.py"),
                "--task-id",
                "1",
                "--resume",
                "--max-wall-time-sec",
                "1",
                "--skip-agent-review",
            ]
            with mock.patch.dict(os.environ, _stable_env(), clear=False), \
                mock.patch.object(sys, "argv", argv), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path), \
                mock.patch.object(run_review_pipeline_module, "_run_step") as run_step_mock:
                rc = run_review_pipeline_module.main()

            self.assertEqual(1, rc)
            run_step_mock.assert_not_called()
            marathon_state = json.loads((out_dir / "marathon-state.json").read_text(encoding="utf-8"))
            self.assertEqual("fail", marathon_state["status"])
            self.assertEqual("wall_time_exceeded", marathon_state["stop_reason"])
            self.assertTrue(marathon_state["wall_time_exceeded"])

    def test_max_step_retries_should_rerun_failed_step_until_success(self) -> None:
        run_id = uuid.uuid4().hex
        call_counts: dict[str, int] = {}
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-1-{run_id}"
            latest_path = tmp_root / "sc-review-pipeline-task-1" / "latest.json"

            def fake_run_step(*, out_dir: Path, name: str, cmd: list[str], timeout_sec: int) -> dict:
                call_counts[name] = call_counts.get(name, 0) + 1
                if name == "sc-test" and call_counts[name] == 1:
                    return {
                        "name": name,
                        "cmd": cmd,
                        "rc": 1,
                        "status": "fail",
                        "log": str(out_dir / f"{name}.attempt1.log"),
                        "reported_out_dir": "",
                        "summary_file": "",
                    }
                return {
                    "name": name,
                    "cmd": cmd,
                    "rc": 0,
                    "status": "ok",
                    "log": str(out_dir / f"{name}.log"),
                    "reported_out_dir": "",
                    "summary_file": "",
                }

            argv = [
                str(REPO_ROOT / "scripts" / "sc" / "run_review_pipeline.py"),
                "--task-id",
                "1",
                "--run-id",
                run_id,
                "--max-step-retries",
                "1",
                "--allow-large-change-scope-rerun",
                "--skip-agent-review",
            ]
            with mock.patch.dict(os.environ, _stable_env(), clear=False), \
                mock.patch.object(sys, "argv", argv), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path), \
                mock.patch.object(run_review_pipeline_module, "_find_recent_deterministic_green_llm_not_clean_run", return_value=None), \
                mock.patch.object(run_review_pipeline_module, "_find_repeated_deterministic_failure_guard", return_value=None), \
                mock.patch.object(run_review_pipeline_module, "_derive_chapter6_route_guard", return_value=None), \
                mock.patch.object(run_review_pipeline_module, "_run_step", side_effect=fake_run_step):
                rc = run_review_pipeline_module.main()

            self.assertEqual(0, rc)
            self.assertEqual(2, call_counts["sc-test"])
            self.assertEqual(1, call_counts["sc-acceptance-check"])
            self.assertEqual(1, call_counts["sc-llm-review"])

            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            marathon_state = json.loads((out_dir / "marathon-state.json").read_text(encoding="utf-8"))
            latest = json.loads(latest_path.read_text(encoding="utf-8"))

            self.assertEqual("ok", summary["status"])
            self.assertEqual("ok", marathon_state["status"])
            self.assertEqual("sc-llm-review", marathon_state["last_completed_step"])
            self.assertEqual(2, marathon_state["steps"]["sc-test"]["attempt_count"])
            self.assertEqual("ok", marathon_state["steps"]["sc-test"]["status"])
            self.assertEqual(str(out_dir / "marathon-state.json"), latest["marathon_state_path"])

    def test_sc_test_unit_failure_should_stop_same_run_retry_even_when_retries_allowed(self) -> None:
        run_id = uuid.uuid4().hex
        call_counts: dict[str, int] = {}
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-1-{run_id}"
            latest_path = tmp_root / "sc-review-pipeline-task-1" / "latest.json"

            def fake_run_step(*, out_dir: Path, name: str, cmd: list[str], timeout_sec: int) -> dict:
                call_counts[name] = call_counts.get(name, 0) + 1
                if name == "sc-test":
                    sc_test_summary = out_dir / "child-artifacts" / "sc-test" / "summary.json"
                    sc_test_summary.parent.mkdir(parents=True, exist_ok=True)
                    sc_test_summary.write_text(
                        json.dumps(
                            {
                                "cmd": "sc-test",
                                "status": "fail",
                                "steps": [
                                    {"name": "unit", "status": "fail", "rc": 2},
                                    {"name": "gdunit-hard", "status": "ok", "rc": 0},
                                    {"name": "smoke", "status": "ok", "rc": 0},
                                ],
                            },
                            ensure_ascii=False,
                            indent=2,
                        )
                        + "\n",
                        encoding="utf-8",
                    )
                    return {
                        "name": name,
                        "cmd": cmd,
                        "rc": 1,
                        "status": "fail",
                        "log": str(out_dir / f"{name}.log"),
                        "reported_out_dir": str(sc_test_summary.parent),
                        "summary_file": str(sc_test_summary),
                    }
                return {
                    "name": name,
                    "cmd": cmd,
                    "rc": 0,
                    "status": "ok",
                    "log": str(out_dir / f"{name}.log"),
                    "reported_out_dir": "",
                    "summary_file": "",
                }

            argv = [
                str(REPO_ROOT / "scripts" / "sc" / "run_review_pipeline.py"),
                "--task-id",
                "1",
                "--run-id",
                run_id,
                "--max-step-retries",
                "1",
                "--allow-large-change-scope-rerun",
                "--skip-agent-review",
            ]
            with mock.patch.dict(os.environ, _stable_env(), clear=False), \
                mock.patch.object(sys, "argv", argv), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path), \
                mock.patch.object(run_review_pipeline_module, "_find_recent_deterministic_green_llm_not_clean_run", return_value=None), \
                mock.patch.object(run_review_pipeline_module, "_find_repeated_deterministic_failure_guard", return_value=None), \
                mock.patch.object(run_review_pipeline_module, "_derive_chapter6_route_guard", return_value=None), \
                mock.patch.object(run_review_pipeline_module, "_run_step", side_effect=fake_run_step):
                rc = run_review_pipeline_module.main()

            self.assertEqual(1, rc)
            self.assertEqual(1, call_counts["sc-test"])
            self.assertNotIn("sc-acceptance-check", call_counts)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("fail", summary["status"])
            self.assertEqual("step_failed:sc-test", summary["reason"])
            self.assertEqual(
                {
                    "kind": "unit_failure_known",
                    "blocked": True,
                    "step_name": "sc-test",
                },
                summary["diagnostics"]["sc_test_retry_stop_loss"],
            )

    def test_resume_should_continue_from_failed_step(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-1-{run_id}"
            latest_path = tmp_root / "sc-review-pipeline-task-1" / "latest.json"
            initial_counts: dict[str, int] = {}

            def first_run(*, out_dir: Path, name: str, cmd: list[str], timeout_sec: int) -> dict:
                initial_counts[name] = initial_counts.get(name, 0) + 1
                status = "ok"
                rc = 0
                if name == "sc-acceptance-check":
                    status = "fail"
                    rc = 1
                return {
                    "name": name,
                    "cmd": cmd,
                    "rc": rc,
                    "status": status,
                    "log": str(out_dir / f"{name}.log"),
                    "reported_out_dir": "",
                    "summary_file": "",
                }

            argv1 = [
                str(REPO_ROOT / "scripts" / "sc" / "run_review_pipeline.py"),
                "--task-id",
                "1",
                "--run-id",
                run_id,
                "--max-step-retries",
                "0",
                "--allow-large-change-scope-rerun",
                "--skip-agent-review",
            ]
            with mock.patch.dict(os.environ, _stable_env(), clear=False), \
                mock.patch.object(sys, "argv", argv1), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path), \
                mock.patch.object(run_review_pipeline_module, "_find_recent_deterministic_green_llm_not_clean_run", return_value=None), \
                mock.patch.object(run_review_pipeline_module, "_find_repeated_deterministic_failure_guard", return_value=None), \
                mock.patch.object(run_review_pipeline_module, "_derive_chapter6_route_guard", return_value=None), \
                mock.patch.object(run_review_pipeline_module, "_run_step", side_effect=first_run):
                first_rc = run_review_pipeline_module.main()

            self.assertEqual(1, first_rc)
            self.assertEqual(1, initial_counts["sc-test"])
            self.assertEqual(1, initial_counts["sc-acceptance-check"])
            self.assertNotIn("sc-llm-review", initial_counts)

            resumed_counts: dict[str, int] = {}

            def resumed_run(*, out_dir: Path, name: str, cmd: list[str], timeout_sec: int) -> dict:
                resumed_counts[name] = resumed_counts.get(name, 0) + 1
                return {
                    "name": name,
                    "cmd": cmd,
                    "rc": 0,
                    "status": "ok",
                    "log": str(out_dir / f"{name}.resume.log"),
                    "reported_out_dir": "",
                    "summary_file": "",
                }

            argv2 = [
                str(REPO_ROOT / "scripts" / "sc" / "run_review_pipeline.py"),
                "--task-id",
                "1",
                "--resume",
                "--allow-large-change-scope-rerun",
                "--skip-agent-review",
            ]
            with mock.patch.dict(os.environ, _stable_env(), clear=False), \
                mock.patch.object(sys, "argv", argv2), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path), \
                mock.patch.object(run_review_pipeline_module, "resolve_approval_state", return_value={"required_action": "", "status": "not-needed"}), \
                mock.patch.object(run_review_pipeline_module, "_run_step", side_effect=resumed_run):
                second_rc = run_review_pipeline_module.main()

            self.assertEqual(0, second_rc)
            self.assertNotIn("sc-test", resumed_counts)
            self.assertEqual(1, resumed_counts["sc-acceptance-check"])
            self.assertEqual(1, resumed_counts["sc-llm-review"])

            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            marathon_state = json.loads((out_dir / "marathon-state.json").read_text(encoding="utf-8"))
            events = [
                json.loads(line)
                for line in (out_dir / "run-events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

            self.assertEqual("ok", summary["status"])
            self.assertEqual("ok", marathon_state["status"])
            self.assertEqual(2, marathon_state["resume_count"])
            self.assertEqual("sc-llm-review", marathon_state["last_completed_step"])
            resumed_event = next(item for item in events if item["event"] == "run_resumed")
            self.assertEqual(f"{run_id}:turn-2", resumed_event["turn_id"])
            self.assertEqual(2, resumed_event["turn_seq"])

    def test_abort_should_mark_latest_run_and_skip_execution(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-1-{run_id}"
            latest_path = tmp_root / "sc-review-pipeline-task-1" / "latest.json"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "cmd": "sc-review-pipeline",
                        "task_id": "1",
                        "requested_run_id": run_id,
                        "run_id": run_id,
                        "allow_overwrite": False,
                        "force_new_run_id": False,
                        "status": "fail",
                        "steps": [
                            {"name": "sc-test", "cmd": ["py", "-3", "scripts/sc/test.py"], "rc": 1, "status": "fail", "log": "x.log"}
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (out_dir / "marathon-state.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "task_id": "1",
                        "run_id": run_id,
                        "status": "fail",
                        "resume_count": 1,
                        "max_step_retries": 0,
                        "last_completed_step": "",
                        "last_failed_step": "sc-test",
                        "steps": {"sc-test": {"attempt_count": 1, "status": "fail"}},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            latest_path.parent.mkdir(parents=True, exist_ok=True)
            latest_path.write_text(
                json.dumps(
                    {
                        "task_id": "1",
                        "run_id": run_id,
                        "status": "fail",
                        "latest_out_dir": str(out_dir),
                        "summary_path": str(out_dir / "summary.json"),
                        "marathon_state_path": str(out_dir / "marathon-state.json"),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            argv = [
                str(REPO_ROOT / "scripts" / "sc" / "run_review_pipeline.py"),
                "--task-id",
                "1",
                "--abort",
            ]
            with mock.patch.dict(os.environ, _stable_env(), clear=False), \
                mock.patch.object(sys, "argv", argv), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path), \
                mock.patch.object(run_review_pipeline_module, "_run_step") as run_step_mock:
                rc = run_review_pipeline_module.main()

            self.assertEqual(0, rc)
            run_step_mock.assert_not_called()
            marathon_state = json.loads((out_dir / "marathon-state.json").read_text(encoding="utf-8"))
            latest = json.loads(latest_path.read_text(encoding="utf-8"))
            self.assertEqual("aborted", marathon_state["status"])
            self.assertEqual("aborted", latest["status"])

    def test_fork_should_create_new_run_and_continue_from_failed_step(self) -> None:
        source_run_id = uuid.uuid4().hex
        fork_run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            source_out_dir = tmp_root / f"sc-review-pipeline-task-1-{source_run_id}"
            fork_out_dir = tmp_root / f"sc-review-pipeline-task-1-{fork_run_id}"
            latest_path = tmp_root / "sc-review-pipeline-task-1" / "latest.json"
            source_out_dir.mkdir(parents=True, exist_ok=True)
            (source_out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "cmd": "sc-review-pipeline",
                        "task_id": "1",
                        "requested_run_id": source_run_id,
                        "run_id": source_run_id,
                        "allow_overwrite": False,
                        "force_new_run_id": False,
                        "status": "fail",
                        "steps": [
                            {"name": "sc-test", "cmd": ["py", "-3", "scripts/sc/test.py"], "rc": 0, "status": "ok", "log": "sc-test.log"},
                            {"name": "sc-acceptance-check", "cmd": ["py", "-3", "scripts/sc/acceptance_check.py"], "rc": 1, "status": "fail", "log": "sc-acceptance.log"},
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (source_out_dir / "marathon-state.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "task_id": "1",
                        "run_id": source_run_id,
                        "requested_run_id": source_run_id,
                        "status": "fail",
                        "resume_count": 1,
                        "max_step_retries": 0,
                        "last_completed_step": "sc-test",
                        "last_failed_step": "sc-acceptance-check",
                        "next_step_name": "sc-acceptance-check",
                        "steps": {
                            "sc-test": {"attempt_count": 1, "status": "ok", "last_rc": 0, "log": "sc-test.log"},
                            "sc-acceptance-check": {"attempt_count": 1, "status": "fail", "last_rc": 1, "log": "sc-acceptance.log"},
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            latest_path.parent.mkdir(parents=True, exist_ok=True)
            latest_path.write_text(
                json.dumps(
                    {
                        "task_id": "1",
                        "run_id": source_run_id,
                        "status": "fail",
                        "latest_out_dir": str(source_out_dir),
                        "summary_path": str(source_out_dir / "summary.json"),
                        "marathon_state_path": str(source_out_dir / "marathon-state.json"),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            call_counts: dict[str, int] = {}

            def resumed_run(*, out_dir: Path, name: str, cmd: list[str], timeout_sec: int) -> dict:
                call_counts[name] = call_counts.get(name, 0) + 1
                return {
                    "name": name,
                    "cmd": cmd,
                    "rc": 0,
                    "status": "ok",
                    "log": str(out_dir / f"{name}.fork.log"),
                    "reported_out_dir": "",
                    "summary_file": "",
                }

            argv = [
                str(REPO_ROOT / "scripts" / "sc" / "run_review_pipeline.py"),
                "--task-id",
                "1",
                "--fork",
                "--run-id",
                fork_run_id,
                "--allow-large-change-scope-rerun",
                "--skip-agent-review",
            ]
            with mock.patch.dict(os.environ, _stable_env(), clear=False), \
                mock.patch.object(sys, "argv", argv), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=fork_out_dir), \
                mock.patch.object(run_review_pipeline_module, "_run_step", side_effect=resumed_run):
                rc = run_review_pipeline_module.main()

            self.assertEqual(0, rc)
            self.assertNotIn("sc-test", call_counts)
            self.assertEqual(1, call_counts["sc-acceptance-check"])
            self.assertEqual(1, call_counts["sc-llm-review"])
            self.assertTrue(fork_out_dir.exists())
            self.assertEqual(source_run_id, json.loads((source_out_dir / "summary.json").read_text(encoding="utf-8"))["run_id"])

            fork_summary = json.loads((fork_out_dir / "summary.json").read_text(encoding="utf-8"))
            fork_state = json.loads((fork_out_dir / "marathon-state.json").read_text(encoding="utf-8"))
            latest = json.loads(latest_path.read_text(encoding="utf-8"))

            self.assertEqual(fork_run_id, fork_summary["run_id"])
            self.assertEqual("ok", fork_summary["status"])
            self.assertEqual(source_run_id, fork_state["forked_from_run_id"])
            self.assertEqual(str(source_out_dir), fork_state["forked_from_out_dir"])
            self.assertEqual(str(fork_out_dir / "marathon-state.json"), latest["marathon_state_path"])
            self.assertFalse((fork_out_dir / "approval-request.json").exists())

            fork_execution_context = json.loads((fork_out_dir / "execution-context.json").read_text(encoding="utf-8"))
            self.assertEqual("", fork_execution_context["approval"]["required_action"])
            self.assertEqual("not-needed", fork_execution_context["approval"]["status"])


if __name__ == "__main__":
    unittest.main()
