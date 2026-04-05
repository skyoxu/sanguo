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
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir),
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path),
                mock.patch.object(run_review_pipeline_module, "run_review_prerequisite_check", return_value=None),
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
            self.assertEqual("adr,links,overlay,contracts,arch,build", cmd[cmd.index("--only") + 1])

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
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir),
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path),
                mock.patch.object(run_review_pipeline_module, "run_review_prerequisite_check", return_value=None),
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
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir),
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path),
                mock.patch.object(run_review_pipeline_module, "resolve_triplet", return_value=self._triplet()),
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
                (child_dir / "summary.json").write_text(
                    json.dumps({"step": step_name, "status": "ok"}, ensure_ascii=False, indent=2) + "\n",
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
            self.assertEqual(
                ["sc-test", "sc-acceptance-check", "sc-llm-review"],
                [item["name"] for item in summary["steps"]],
            )
            self.assertTrue(all(item["status"] == "ok" for item in summary["steps"]))
            self.assertIn("decision-logs/active-task.md", (out_dir / "sc-llm-review.log").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
