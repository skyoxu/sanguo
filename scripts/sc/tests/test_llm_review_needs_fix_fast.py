#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

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

import llm_review_needs_fix_fast as needs_fix_fast  # noqa: E402


class NeedsFixFastDeliveryProfileTests(unittest.TestCase):
    def test_apply_delivery_profile_defaults_should_follow_fast_ship_defaults(self) -> None:
        args = needs_fix_fast.apply_delivery_profile_defaults(
            needs_fix_fast.build_parser().parse_args(["--task-id", "7", "--delivery-profile", "fast-ship"])
        )

        self.assertEqual("fast-ship", args.delivery_profile)
        self.assertEqual("host-safe", args.security_profile)
        self.assertEqual("code-reviewer,security-auditor,semantic-equivalence-auditor", args.agents)
        self.assertEqual("summary", args.diff_mode)
        self.assertEqual(2, args.max_rounds)
        self.assertTrue(args.rerun_failing_only)
        self.assertEqual(30, args.time_budget_min)
        self.assertEqual(10, args.min_llm_budget_min)

    def test_apply_delivery_profile_defaults_should_keep_standard_stricter_defaults(self) -> None:
        args = needs_fix_fast.apply_delivery_profile_defaults(
            needs_fix_fast.build_parser().parse_args(["--task-id", "7", "--delivery-profile", "standard"])
        )

        self.assertEqual("standard", args.delivery_profile)
        self.assertEqual("strict", args.security_profile)
        self.assertEqual("all", args.agents)
        self.assertEqual("full", args.diff_mode)
        self.assertEqual(45, args.time_budget_min)
        self.assertEqual(12, args.min_llm_budget_min)

    def test_apply_delivery_profile_defaults_should_force_full_closure_for_final_pass(self) -> None:
        args = needs_fix_fast.apply_delivery_profile_defaults(
            needs_fix_fast.build_parser().parse_args(
                ["--task-id", "7", "--delivery-profile", "fast-ship", "--final-pass", "--skip-sc-test"]
            )
        )

        self.assertTrue(args.final_pass)
        self.assertEqual("all", args.agents)
        self.assertEqual("full", args.diff_mode)
        self.assertFalse(args.skip_sc_test)


class NeedsFixFastDeterministicReuseTests(unittest.TestCase):
    def test_try_reuse_latest_deterministic_step_should_reuse_matching_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-03-31" / "sc-review-pipeline-task-56-run-a"
            out_dir.mkdir(parents=True, exist_ok=True)
            latest_dir = root / "logs" / "ci" / "2026-03-31" / "sc-review-pipeline-task-56"
            latest_dir.mkdir(parents=True, exist_ok=True)
            (latest_dir / "latest.json").write_text(
                json.dumps(
                    {
                        "task_id": "56",
                        "run_id": "run-a",
                        "status": "ok",
                        "latest_out_dir": str(out_dir),
                        "summary_path": str(out_dir / "summary.json"),
                        "execution_context_path": str(out_dir / "execution-context.json"),
                    }
                ),
                encoding="utf-8",
            )
            (out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "task_id": "56",
                        "status": "ok",
                        "steps": [
                            {"name": "sc-test", "status": "ok", "rc": 0},
                            {"name": "sc-acceptance-check", "status": "ok", "rc": 0},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (out_dir / "execution-context.json").write_text(
                json.dumps(
                    {
                        "security_profile": "host-safe",
                        "git": {
                            "head": "abc123",
                            "status_short": [" M scripts/sc/_acceptance_steps.py"],
                        },
                    }
                ),
                encoding="utf-8",
            )

            with (
                mock.patch.object(needs_fix_fast, "repo_root", return_value=root),
                mock.patch.object(
                    needs_fix_fast,
                    "current_git_fingerprint",
                    return_value={"head": "abc123", "status_short": [" M scripts/sc/_acceptance_steps.py"]},
                ),
            ):
                step = needs_fix_fast.try_reuse_latest_deterministic_step(
                    task_id="56",
                    security_profile="host-safe",
                    skip_sc_test=False,
                    planned_cmd=["py", "-3", "scripts/sc/run_review_pipeline.py"],
                    out_dir=root / "logs" / "ci" / "2026-03-31" / "sc-needs-fix-fast-task-56",
                    script_start=0.0,
                    budget_min=20,
                )

            self.assertIsNotNone(step)
            assert step is not None
            self.assertEqual("reused", step["status"])
            self.assertEqual(0, int(step["rc"]))
            self.assertEqual(str(out_dir), step["reported_out_dir"])
            self.assertEqual("run-a", step["reused_run_id"])

    def test_try_reuse_latest_deterministic_step_should_reject_git_snapshot_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-03-31" / "sc-review-pipeline-task-56-run-a"
            out_dir.mkdir(parents=True, exist_ok=True)
            latest_dir = root / "logs" / "ci" / "2026-03-31" / "sc-review-pipeline-task-56"
            latest_dir.mkdir(parents=True, exist_ok=True)
            (latest_dir / "latest.json").write_text(
                json.dumps(
                    {
                        "task_id": "56",
                        "run_id": "run-a",
                        "status": "ok",
                        "latest_out_dir": str(out_dir),
                        "summary_path": str(out_dir / "summary.json"),
                        "execution_context_path": str(out_dir / "execution-context.json"),
                    }
                ),
                encoding="utf-8",
            )
            (out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "task_id": "56",
                        "status": "ok",
                        "steps": [
                            {"name": "sc-test", "status": "ok", "rc": 0},
                            {"name": "sc-acceptance-check", "status": "ok", "rc": 0},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (out_dir / "execution-context.json").write_text(
                json.dumps(
                    {
                        "security_profile": "host-safe",
                        "git": {"head": "abc123", "status_short": [" M scripts/sc/_acceptance_steps.py"]},
                    }
                ),
                encoding="utf-8",
            )

            with (
                mock.patch.object(needs_fix_fast, "repo_root", return_value=root),
                mock.patch.object(
                    needs_fix_fast,
                    "current_git_fingerprint",
                    return_value={"head": "def456", "status_short": [" M scripts/sc/_acceptance_steps.py"]},
                ),
            ):
                step = needs_fix_fast.try_reuse_latest_deterministic_step(
                    task_id="56",
                    security_profile="host-safe",
                    skip_sc_test=False,
                    planned_cmd=["py", "-3", "scripts/sc/run_review_pipeline.py"],
                    out_dir=root / "logs" / "ci" / "2026-03-31" / "sc-needs-fix-fast-task-56",
                    script_start=0.0,
                    budget_min=20,
                )

            self.assertIsNone(step)

    def test_try_reuse_latest_deterministic_step_should_scan_previous_day_latest_indices(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-03-30" / "sc-review-pipeline-task-56-run-a"
            out_dir.mkdir(parents=True, exist_ok=True)
            latest_dir = root / "logs" / "ci" / "2026-03-30" / "sc-review-pipeline-task-56"
            latest_dir.mkdir(parents=True, exist_ok=True)
            (latest_dir / "latest.json").write_text(
                json.dumps(
                    {
                        "task_id": "56",
                        "run_id": "run-a",
                        "status": "ok",
                        "latest_out_dir": str(out_dir),
                        "summary_path": str(out_dir / "summary.json"),
                        "execution_context_path": str(out_dir / "execution-context.json"),
                    }
                ),
                encoding="utf-8",
            )
            (out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "task_id": "56",
                        "status": "ok",
                        "steps": [
                            {"name": "sc-test", "status": "ok", "rc": 0},
                            {"name": "sc-acceptance-check", "status": "ok", "rc": 0},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (out_dir / "execution-context.json").write_text(
                json.dumps(
                    {
                        "security_profile": "host-safe",
                        "git": {"head": "abc123", "status_short": []},
                    }
                ),
                encoding="utf-8",
            )

            with (
                mock.patch.object(needs_fix_fast, "repo_root", return_value=root),
                mock.patch.object(
                    needs_fix_fast,
                    "current_git_fingerprint",
                    return_value={"head": "abc123", "status_short": []},
                ),
            ):
                step = needs_fix_fast.try_reuse_latest_deterministic_step(
                    task_id="56",
                    security_profile="host-safe",
                    skip_sc_test=False,
                    planned_cmd=["py", "-3", "scripts/sc/run_review_pipeline.py"],
                    out_dir=root / "logs" / "ci" / "2026-03-31" / "sc-needs-fix-fast-task-56",
                    script_start=0.0,
                    budget_min=20,
                )

            self.assertIsNotNone(step)
            assert step is not None
            self.assertEqual("run-a", step["reused_run_id"])


class NeedsFixFastReviewerSelectionTests(unittest.TestCase):
    def test_infer_initial_run_agents_should_prefer_previous_agent_review_hits(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-03-31" / "sc-review-pipeline-task-56-run-a"
            out_dir.mkdir(parents=True, exist_ok=True)
            latest_dir = root / "logs" / "ci" / "2026-03-31" / "sc-review-pipeline-task-56"
            latest_dir.mkdir(parents=True, exist_ok=True)
            (latest_dir / "latest.json").write_text(
                json.dumps(
                    {
                        "task_id": "56",
                        "run_id": "run-a",
                        "status": "ok",
                        "latest_out_dir": str(out_dir),
                        "summary_path": str(out_dir / "summary.json"),
                        "execution_context_path": str(out_dir / "execution-context.json"),
                    }
                ),
                encoding="utf-8",
            )
            (out_dir / "summary.json").write_text(
                json.dumps({"task_id": "56", "status": "ok", "steps": []}),
                encoding="utf-8",
            )
            (out_dir / "execution-context.json").write_text(json.dumps({"security_profile": "host-safe"}), encoding="utf-8")
            (out_dir / "agent-review.json").write_text(
                json.dumps(
                    {
                        "review_verdict": "needs-fix",
                        "findings": [
                            {
                                "finding_id": "llm-security-auditor-needs-fix",
                                "category": "llm-review",
                                "owner_step": "sc-llm-review",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch.object(needs_fix_fast, "repo_root", return_value=root):
                agents, source = needs_fix_fast.infer_initial_run_agents(
                    "56",
                    ["code-reviewer", "security-auditor", "semantic-equivalence-auditor"],
                )

            self.assertEqual(["security-auditor"], agents)
            self.assertEqual("previous-agent-review", source)

    def test_infer_initial_run_agents_should_fallback_to_previous_llm_summary_hits(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-03-31" / "sc-review-pipeline-task-56-run-a"
            llm_dir = root / "logs" / "ci" / "2026-03-31" / "sc-llm-review-task-56"
            out_dir.mkdir(parents=True, exist_ok=True)
            llm_dir.mkdir(parents=True, exist_ok=True)
            latest_dir = root / "logs" / "ci" / "2026-03-31" / "sc-review-pipeline-task-56"
            latest_dir.mkdir(parents=True, exist_ok=True)
            (latest_dir / "latest.json").write_text(
                json.dumps(
                    {
                        "task_id": "56",
                        "run_id": "run-a",
                        "status": "ok",
                        "latest_out_dir": str(out_dir),
                        "summary_path": str(out_dir / "summary.json"),
                        "execution_context_path": str(out_dir / "execution-context.json"),
                    }
                ),
                encoding="utf-8",
            )
            (out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "task_id": "56",
                        "status": "ok",
                        "steps": [
                            {
                                "name": "sc-llm-review",
                                "status": "fail",
                                "summary_file": str(llm_dir / "summary.json"),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (out_dir / "execution-context.json").write_text(json.dumps({"security_profile": "host-safe"}), encoding="utf-8")
            (llm_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "status": "warn",
                        "results": [
                            {"agent": "code-reviewer", "status": "ok", "rc": 0, "details": {"verdict": "OK"}},
                            {"agent": "semantic-equivalence-auditor", "status": "fail", "rc": 124, "details": {"verdict": ""}},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch.object(needs_fix_fast, "repo_root", return_value=root):
                agents, source = needs_fix_fast.infer_initial_run_agents(
                    "56",
                    ["code-reviewer", "security-auditor", "semantic-equivalence-auditor"],
                )

            self.assertEqual(["semantic-equivalence-auditor"], agents)
            self.assertEqual("previous-llm-summary", source)


class NeedsFixFastBudgetGuardTests(unittest.TestCase):
    def test_main_should_fail_fast_when_remaining_budget_is_below_profile_floor(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-03-31" / "sc-needs-fix-fast-task-56"

            argv = [
                "llm_review_needs_fix_fast.py",
                "--task-id",
                "56",
                "--delivery-profile",
                "fast-ship",
                "--time-budget-min",
                "5",
            ]
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(needs_fix_fast, "repo_root", return_value=root),
                mock.patch.object(needs_fix_fast, "ci_dir", return_value=out_dir),
                mock.patch.object(
                    needs_fix_fast,
                    "try_reuse_latest_deterministic_step",
                    return_value={
                        "name": "pipeline-deterministic",
                        "status": "reused",
                        "rc": 0,
                        "duration_sec": 0.0,
                        "remaining_before_sec": 300,
                        "remaining_after_sec": 300,
                        "cmd": ["py", "-3", "scripts/sc/run_review_pipeline.py"],
                        "log_file": str(out_dir / "pipeline-deterministic.log"),
                        "reported_out_dir": str(root / "logs" / "ci" / "2026-03-31" / "sc-review-pipeline-task-56-run-a"),
                        "summary_file": str(root / "logs" / "ci" / "2026-03-31" / "sc-review-pipeline-task-56-run-a" / "summary.json"),
                        "reused_run_id": "run-a",
                        "reuse_reason": "latest_successful_deterministic_pipeline",
                    },
                ),
            ):
                rc = needs_fix_fast.main()

            self.assertEqual(1, rc)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("fail", summary["status"])
            self.assertEqual("insufficient_llm_budget_before_llm", summary["reason"])
            self.assertEqual("fast-ship", summary["delivery_profile"])


class NeedsFixFastMinimalAcceptanceTests(unittest.TestCase):
    def test_main_should_switch_to_minimal_acceptance_plan_for_semantic_only_changes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-03-31" / "sc-needs-fix-fast-task-56"

            argv = [
                "llm_review_needs_fix_fast.py",
                "--task-id",
                "56",
                "--delivery-profile",
                "fast-ship",
            ]
            deterministic_cmds: list[list[str]] = []

            def _run_step(*, name: str, cmd: list[str], out_dir: Path, timeout_sec: int, script_start: float, budget_min: int) -> dict[str, object]:
                deterministic_cmds.append(list(cmd))
                return {
                    "name": name,
                    "status": "ok",
                    "rc": 0,
                    "duration_sec": 1.0,
                    "remaining_before_sec": 1000,
                    "remaining_after_sec": 999,
                    "cmd": list(cmd),
                    "log_file": str(out_dir / f"{name}.log"),
                    "reported_out_dir": str(out_dir / "acceptance-minimal"),
                    "summary_file": str(out_dir / "acceptance-minimal" / "summary.json"),
                }

            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(needs_fix_fast, "repo_root", return_value=root),
                mock.patch.object(needs_fix_fast, "ci_dir", return_value=out_dir),
                mock.patch.object(needs_fix_fast, "try_reuse_latest_deterministic_step", return_value=None),
                mock.patch.object(
                    needs_fix_fast,
                    "resolve_deterministic_execution_plan",
                    return_value={
                        "mode": "minimal-acceptance",
                        "cmd": [
                            "py",
                            "-3",
                            "scripts/sc/acceptance_check.py",
                            "--task-id",
                            "56",
                            "--out-per-task",
                            "--only",
                            "adr,links,overlay,subtasks",
                        ],
                        "change_scope": {
                            "deterministic_strategy": "minimal-acceptance",
                            "change_fingerprint": "fp-semantic-only",
                            "changed_paths": [".taskmaster/tasks/tasks_back.json"],
                            "acceptance_only_steps": ["adr", "links", "overlay", "subtasks"],
                        },
                    },
                ),
                mock.patch.object(needs_fix_fast, "try_reuse_matching_minimal_acceptance_step", return_value=None),
                mock.patch.object(needs_fix_fast, "infer_initial_run_agents", return_value=([], "configured-defaults")),
                mock.patch.object(needs_fix_fast, "run_step", side_effect=_run_step),
            ):
                rc = needs_fix_fast.main()

            self.assertEqual(0, rc)
            self.assertEqual("scripts/sc/acceptance_check.py", deterministic_cmds[0][2])
            self.assertIn("--only", deterministic_cmds[0])
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("minimal-acceptance", summary["deterministic_plan"]["mode"])
            self.assertEqual("fp-semantic-only", summary["deterministic_plan"]["change_scope"]["change_fingerprint"])


class NeedsFixFastFinalPassTests(unittest.TestCase):
    def test_main_should_force_full_pipeline_and_full_agents_for_final_pass(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-03-31" / "sc-needs-fix-fast-task-56"

            argv = [
                "llm_review_needs_fix_fast.py",
                "--task-id",
                "56",
                "--delivery-profile",
                "fast-ship",
                "--final-pass",
                "--skip-sc-test",
                "--max-rounds",
                "1",
            ]
            calls: list[tuple[str, list[str]]] = []

            def _run_step(*, name: str, cmd: list[str], out_dir: Path, timeout_sec: int, script_start: float, budget_min: int) -> dict[str, object]:
                calls.append((name, list(cmd)))
                return {
                    "name": name,
                    "status": "ok",
                    "rc": 0,
                    "duration_sec": 1.0,
                    "remaining_before_sec": 1000,
                    "remaining_after_sec": 999,
                    "cmd": list(cmd),
                    "log_file": str(out_dir / f"{name}.log"),
                    "reported_out_dir": str(out_dir / name),
                    "summary_file": "",
                }

            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(needs_fix_fast, "repo_root", return_value=root),
                mock.patch.object(needs_fix_fast, "ci_dir", return_value=out_dir),
                mock.patch.object(needs_fix_fast, "try_reuse_latest_deterministic_step") as reuse_mock,
                mock.patch.object(needs_fix_fast, "resolve_deterministic_execution_plan") as plan_mock,
                mock.patch.object(needs_fix_fast, "try_reuse_matching_minimal_acceptance_step") as min_reuse_mock,
                mock.patch.object(needs_fix_fast, "infer_initial_run_agents") as infer_mock,
                mock.patch.object(needs_fix_fast, "run_step", side_effect=_run_step),
            ):
                rc = needs_fix_fast.main()

            self.assertEqual(0, rc)
            reuse_mock.assert_not_called()
            plan_mock.assert_not_called()
            min_reuse_mock.assert_not_called()
            infer_mock.assert_not_called()
            self.assertEqual("pipeline-deterministic", calls[0][0])
            self.assertEqual("scripts/sc/run_review_pipeline.py", calls[0][1][2])
            self.assertNotIn("--skip-test", calls[0][1])
            self.assertEqual("pipeline-llm-round-1", calls[1][0])
            llm_cmd = calls[1][1]
            self.assertEqual("all", llm_cmd[llm_cmd.index("--llm-agents") + 1])
            self.assertEqual("full", llm_cmd[llm_cmd.index("--llm-diff-mode") + 1])

            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertTrue(summary["args"]["final_pass"])
            self.assertEqual("full-pipeline", summary["deterministic_plan"]["mode"])
            self.assertEqual(["all"], summary["args"]["agents"])
            self.assertEqual("final-pass", summary["args"]["initial_run_agents_source"])


if __name__ == "__main__":
    unittest.main()
