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


def _write_llm_pipeline_artifacts(
    out_dir: Path,
    step_name: str,
    *,
    results: list[dict[str, object]],
    step_status: str = "ok",
    step_rc: int = 0,
) -> tuple[str, str]:
    pipeline_dir = out_dir / step_name
    llm_dir = pipeline_dir / "sc-llm-review-artifacts"
    llm_dir.mkdir(parents=True, exist_ok=True)
    llm_summary_path = llm_dir / "summary.json"
    llm_summary_path.write_text(
        json.dumps({"status": step_status, "results": results}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    pipeline_summary_path = pipeline_dir / "summary.json"
    pipeline_summary_path.write_text(
        json.dumps(
            {
                "status": step_status,
                "steps": [
                    {
                        "name": "sc-llm-review",
                        "status": step_status,
                        "rc": step_rc,
                        "reported_out_dir": str(llm_dir),
                        "summary_file": str(llm_summary_path),
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return str(pipeline_dir), str(pipeline_summary_path)


class NeedsFixFastDeliveryProfileTests(unittest.TestCase):
    def test_apply_delivery_profile_defaults_should_follow_fast_ship_defaults(self) -> None:
        args = needs_fix_fast.apply_delivery_profile_defaults(
            needs_fix_fast.build_parser().parse_args(["--task-id", "7", "--delivery-profile", "fast-ship"])
        )

        self.assertEqual("fast-ship", args.delivery_profile)
        self.assertEqual("codex-cli", args.llm_backend)
        self.assertEqual("host-safe", args.security_profile)
        self.assertEqual("code-reviewer,security-auditor,semantic-equivalence-auditor", args.agents)
        self.assertEqual("summary", args.diff_mode)
        self.assertEqual(2, args.max_rounds)
        self.assertTrue(args.rerun_failing_only)
        self.assertEqual(30, args.time_budget_min)
        self.assertEqual(10, args.min_llm_budget_min)

    def test_cap_targeted_single_agent_timeouts_should_shrink_default_budget(self) -> None:
        llm_timeout, agent_timeout = needs_fix_fast.cap_targeted_single_agent_timeouts(
            run_agents=["semantic-equivalence-auditor"],
            current_source="change-scope-targeted",
            llm_timeout_sec=900,
            agent_timeout_sec=240,
            explicit_llm_timeout=False,
            explicit_agent_timeout=False,
            final_pass=False,
        )

        self.assertEqual(480, llm_timeout)
        self.assertEqual(180, agent_timeout)

    def test_cap_targeted_single_agent_timeouts_should_respect_explicit_flags(self) -> None:
        llm_timeout, agent_timeout = needs_fix_fast.cap_targeted_single_agent_timeouts(
            run_agents=["semantic-equivalence-auditor"],
            current_source="change-scope-targeted",
            llm_timeout_sec=720,
            agent_timeout_sec=300,
            explicit_llm_timeout=True,
            explicit_agent_timeout=True,
            final_pass=False,
        )

        self.assertEqual(720, llm_timeout)
        self.assertEqual(300, agent_timeout)

    def test_apply_delivery_profile_defaults_should_keep_standard_stricter_defaults(self) -> None:
        args = needs_fix_fast.apply_delivery_profile_defaults(
            needs_fix_fast.build_parser().parse_args(["--task-id", "7", "--delivery-profile", "standard"])
        )

        self.assertEqual("standard", args.delivery_profile)
        self.assertEqual("codex-cli", args.llm_backend)
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

    def test_apply_risky_change_profile_floor_should_raise_playable_ea_to_fast_ship_defaults(self) -> None:
        raw_args = needs_fix_fast.build_parser().parse_args(["--task-id", "7", "--delivery-profile", "playable-ea"])
        explicit_flags = {
            "security_profile": False,
            "agents": False,
            "diff_mode": False,
            "max_rounds": False,
            "rerun_failing_only": False,
            "time_budget_min": False,
            "llm_timeout_sec": False,
            "agent_timeout_sec": False,
            "step_timeout_sec": False,
            "min_llm_budget_min": False,
        }
        args = needs_fix_fast.apply_delivery_profile_defaults(raw_args)

        decision = needs_fix_fast._apply_risky_change_profile_floor(
            args,
            explicit_flags=explicit_flags,
            change_scope={
                "changed_paths": [
                    "scripts/sc/run_review_pipeline.py",
                    "Game.Core/Combat/AttackResolver.cs",
                ],
                "unsafe_paths": [
                    "scripts/sc/run_review_pipeline.py",
                    "Game.Core/Combat/AttackResolver.cs",
                ],
            },
        )

        self.assertTrue(decision["applied"])
        self.assertEqual("fast-ship", args.delivery_profile)
        self.assertEqual("host-safe", args.security_profile)
        self.assertEqual("code-reviewer,security-auditor,semantic-equivalence-auditor", args.agents)
        self.assertEqual("summary", args.diff_mode)
        self.assertEqual(2, args.max_rounds)
        self.assertTrue(args.rerun_failing_only)
        self.assertEqual(30, args.time_budget_min)
        self.assertEqual(10, args.min_llm_budget_min)


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

    def test_prefer_precise_llm_summary_agents_should_shrink_agent_review_hits_for_fast_ship(self) -> None:
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
                            {"agent": "code-reviewer", "status": "fail", "rc": 124, "details": {"verdict": ""}},
                            {"agent": "security-auditor", "status": "ok", "rc": 0, "details": {"verdict": "OK"}},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch.object(needs_fix_fast, "repo_root", return_value=root):
                agents, source = needs_fix_fast.prefer_precise_llm_summary_agents(
                    task_id="56",
                    delivery_profile="fast-ship",
                    diff_mode="summary",
                    configured_agents=["code-reviewer", "security-auditor", "semantic-equivalence-auditor"],
                    current_agents=["code-reviewer", "security-auditor"],
                    current_source="previous-agent-review",
                )

            self.assertEqual(["code-reviewer"], agents)
            self.assertEqual("previous-llm-summary-precise", source)


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

    def test_main_should_mark_timeout_unknown_round_as_indeterminate_not_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-03-31" / "sc-needs-fix-fast-task-56"

            argv = [
                "llm_review_needs_fix_fast.py",
                "--task-id",
                "56",
                "--delivery-profile",
                "playable-ea",
                "--max-rounds",
                "1",
                "--agents",
                "code-reviewer,semantic-equivalence-auditor",
            ]

            def _run_step(*, name: str, cmd: list[str], out_dir: Path, timeout_sec: int, script_start: float, budget_min: int) -> dict[str, object]:
                if name == "pipeline-deterministic":
                    return {
                        "name": name,
                        "status": "ok",
                        "rc": 0,
                        "duration_sec": 1.0,
                        "remaining_before_sec": 1000,
                        "remaining_after_sec": 999,
                        "cmd": list(cmd),
                        "log_file": str(out_dir / f"{name}.log"),
                        "reported_out_dir": str(out_dir / "deterministic"),
                        "summary_file": str(out_dir / "deterministic" / "summary.json"),
                    }
                return {
                    "name": name,
                    "status": "fail",
                    "rc": 124,
                    "duration_sec": 5.0,
                    "remaining_before_sec": 999,
                    "remaining_after_sec": 994,
                    "cmd": list(cmd),
                    "log_file": str(out_dir / f"{name}.log"),
                    "reported_out_dir": "",
                    "summary_file": "",
                }

            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(needs_fix_fast, "repo_root", return_value=root),
                mock.patch.object(needs_fix_fast, "ci_dir", return_value=out_dir),
                mock.patch.object(needs_fix_fast, "try_skip_when_latest_pipeline_already_clean", return_value=None),
                mock.patch.object(needs_fix_fast, "try_stop_when_latest_llm_unknown_without_anchor_fix", return_value=None),
                mock.patch.object(needs_fix_fast, "try_reuse_latest_deterministic_step", return_value=None),
                mock.patch.object(
                    needs_fix_fast,
                    "resolve_deterministic_execution_plan",
                    return_value={"mode": "full-pipeline", "cmd": ["py", "-3", "scripts/sc/run_review_pipeline.py"], "change_scope": {}},
                ),
                mock.patch.object(needs_fix_fast, "infer_initial_run_agents", return_value=(["code-reviewer", "semantic-equivalence-auditor"], "configured-defaults")),
                mock.patch.object(needs_fix_fast, "run_step", side_effect=_run_step),
            ):
                rc = needs_fix_fast.main()

            self.assertEqual(1, rc)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("indeterminate", summary["status"])
            self.assertEqual("llm_review_verdict_unknown", summary["reason"])
            self.assertEqual(["code-reviewer", "semantic-equivalence-auditor"], summary["final_unknown_agents"])
            self.assertEqual(["code-reviewer", "semantic-equivalence-auditor"], summary["rounds"][0]["timeout_agents"])
            self.assertEqual("timeout-no-summary", summary["rounds"][0]["failure_kind"])


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
                "--agents",
                "code-reviewer",
            ]
            deterministic_cmds: list[list[str]] = []

            def _run_step(*, name: str, cmd: list[str], out_dir: Path, timeout_sec: int, script_start: float, budget_min: int) -> dict[str, object]:
                deterministic_cmds.append(list(cmd))
                reported_out_dir = str(out_dir / "acceptance-minimal")
                summary_file = str(out_dir / "acceptance-minimal" / "summary.json")
                if name == "pipeline-llm-round-1":
                    reported_out_dir, summary_file = _write_llm_pipeline_artifacts(
                        out_dir,
                        name,
                        results=[
                            {"agent": "code-reviewer", "status": "ok", "rc": 0, "details": {"verdict": "OK"}},
                        ],
                    )
                return {
                    "name": name,
                    "status": "ok",
                    "rc": 0,
                    "duration_sec": 1.0,
                    "remaining_before_sec": 1000,
                    "remaining_after_sec": 999,
                    "cmd": list(cmd),
                    "log_file": str(out_dir / f"{name}.log"),
                    "reported_out_dir": reported_out_dir,
                    "summary_file": summary_file,
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
                mock.patch.object(needs_fix_fast, "infer_initial_run_agents", return_value=(["code-reviewer"], "configured-defaults")),
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
            resolved_agents = needs_fix_fast.resolve_configured_agents("all")

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
                reported_out_dir = str(out_dir / name)
                summary_file = ""
                if name == "pipeline-llm-round-1":
                    reported_out_dir, summary_file = _write_llm_pipeline_artifacts(
                        out_dir,
                        name,
                        results=[{"agent": agent, "status": "ok", "rc": 0, "details": {"verdict": "OK"}} for agent in resolved_agents],
                    )
                return {
                    "name": name,
                    "status": "ok",
                    "rc": 0,
                    "duration_sec": 1.0,
                    "remaining_before_sec": 1000,
                    "remaining_after_sec": 999,
                    "cmd": list(cmd),
                    "log_file": str(out_dir / f"{name}.log"),
                    "reported_out_dir": reported_out_dir,
                    "summary_file": summary_file,
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
            self.assertEqual(",".join(resolved_agents), llm_cmd[llm_cmd.index("--llm-agents") + 1])
            self.assertEqual("full", llm_cmd[llm_cmd.index("--llm-diff-mode") + 1])

            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertTrue(summary["args"]["final_pass"])
            self.assertEqual("full-pipeline", summary["deterministic_plan"]["mode"])
            self.assertEqual(resolved_agents, summary["args"]["agents"])
            self.assertEqual(resolved_agents, summary["args"]["initial_run_agents"])
            self.assertEqual("final-pass", summary["args"]["initial_run_agents_source"])
            self.assertEqual([], summary["final_unknown_agents"])


class NeedsFixFastTargetedTimeoutTests(unittest.TestCase):
    def test_main_should_add_code_reviewer_only_timeout_override_for_fast_ship_small_diff(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            latest_out_dir = root / "logs" / "ci" / "2026-04-05" / "sc-review-pipeline-task-56-run-timeout"
            latest_dir = root / "logs" / "ci" / "2026-04-05" / "sc-review-pipeline-task-56"
            llm_dir = latest_out_dir / "sc-llm-review-artifacts"
            latest_out_dir.mkdir(parents=True, exist_ok=True)
            latest_dir.mkdir(parents=True, exist_ok=True)
            llm_dir.mkdir(parents=True, exist_ok=True)
            (latest_dir / "latest.json").write_text(
                json.dumps(
                    {
                        "task_id": "56",
                        "run_id": "run-timeout",
                        "status": "ok",
                        "latest_out_dir": str(latest_out_dir),
                        "summary_path": str(latest_out_dir / "summary.json"),
                        "execution_context_path": str(latest_out_dir / "execution-context.json"),
                    }
                ),
                encoding="utf-8",
            )
            (latest_out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "task_id": "56",
                        "status": "ok",
                        "steps": [
                            {"name": "sc-test", "status": "ok", "rc": 0},
                            {"name": "sc-acceptance-check", "status": "ok", "rc": 0},
                            {
                                "name": "sc-llm-review",
                                "status": "fail",
                                "rc": 1,
                                "summary_file": str(llm_dir / "summary.json"),
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (latest_out_dir / "execution-context.json").write_text(
                json.dumps(
                    {
                        "delivery_profile": "fast-ship",
                        "security_profile": "host-safe",
                        "git": {"head": "prev-head", "status_short": []},
                    }
                ),
                encoding="utf-8",
            )
            (llm_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "status": "warn",
                        "results": [
                            {"agent": "code-reviewer", "status": "fail", "rc": 124, "details": {"verdict": ""}},
                            {"agent": "security-auditor", "status": "ok", "rc": 0, "details": {"verdict": "OK"}},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            out_dir = root / "logs" / "ci" / "2026-04-06" / "sc-needs-fix-fast-task-56"
            argv = [
                "llm_review_needs_fix_fast.py",
                "--task-id",
                "56",
                "--delivery-profile",
                "fast-ship",
                "--max-rounds",
                "1",
                "--agents",
                "code-reviewer",
            ]
            calls: list[tuple[str, list[str]]] = []

            def _run_step(*, name: str, cmd: list[str], out_dir: Path, timeout_sec: int, script_start: float, budget_min: int) -> dict[str, object]:
                calls.append((name, list(cmd)))
                reported_out_dir = str(out_dir / name)
                summary_file = ""
                if name == "pipeline-llm-round-1":
                    reported_out_dir, summary_file = _write_llm_pipeline_artifacts(
                        out_dir,
                        name,
                        results=[
                            {"agent": "code-reviewer", "status": "ok", "rc": 0, "details": {"verdict": "OK"}},
                            {"agent": "security-auditor", "status": "ok", "rc": 0, "details": {"verdict": "OK"}},
                        ],
                    )
                return {
                    "name": name,
                    "status": "ok",
                    "rc": 0,
                    "duration_sec": 1.0,
                    "remaining_before_sec": 1000,
                    "remaining_after_sec": 999,
                    "cmd": list(cmd),
                    "log_file": str(out_dir / f"{name}.log"),
                    "reported_out_dir": reported_out_dir,
                    "summary_file": summary_file,
                }

            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(needs_fix_fast, "repo_root", return_value=root),
                mock.patch.object(needs_fix_fast, "ci_dir", return_value=out_dir),
                mock.patch.object(needs_fix_fast, "current_git_fingerprint", return_value={"head": "new-head", "status_short": []}),
                mock.patch.object(
                    needs_fix_fast,
                    "classify_change_scope_between_snapshots",
                    return_value={
                        "deterministic_strategy": "reuse-latest",
                        "doc_only_delta": True,
                        "changed_paths": ["docs/architecture/overlays/PRD-NEWROUGE-GAME-0001/08/feature-slice.md"],
                        "unsafe_paths": [],
                    },
                ),
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
                        "reported_out_dir": str(latest_out_dir),
                        "summary_file": str(latest_out_dir / "summary.json"),
                        "reused_run_id": "run-timeout",
                        "reuse_reason": "latest_successful_deterministic_pipeline",
                    },
                ),
                mock.patch.object(needs_fix_fast, "infer_initial_run_agents", return_value=(["code-reviewer"], "previous-llm-summary")),
                mock.patch.object(needs_fix_fast, "run_step", side_effect=_run_step),
            ):
                rc = needs_fix_fast.main()

            self.assertEqual(0, rc)
            self.assertEqual("pipeline-llm-round-1", calls[0][0])
            llm_cmd = calls[0][1]
            self.assertIn("--llm-agent-timeouts", llm_cmd)
            self.assertEqual("code-reviewer=480", llm_cmd[llm_cmd.index("--llm-agent-timeouts") + 1])
            self.assertNotIn("security-auditor=480", llm_cmd)

    def test_main_should_forward_llm_backend_to_run_review_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-04-06" / "sc-needs-fix-fast-task-56"
            argv = [
                "llm_review_needs_fix_fast.py",
                "--task-id",
                "56",
                "--delivery-profile",
                "fast-ship",
                "--llm-backend",
                "openai-api",
                "--max-rounds",
                "1",
                "--agents",
                "code-reviewer",
            ]
            calls: list[tuple[str, list[str]]] = []

            def _run_step(*, name: str, cmd: list[str], out_dir: Path, timeout_sec: int, script_start: float, budget_min: int) -> dict[str, object]:
                calls.append((name, list(cmd)))
                reported_out_dir = str(out_dir / name)
                summary_file = ""
                if name == "pipeline-llm-round-1":
                    reported_out_dir, summary_file = _write_llm_pipeline_artifacts(
                        out_dir,
                        name,
                        results=[{"agent": "code-reviewer", "status": "ok", "rc": 0, "details": {"verdict": "OK"}}],
                    )
                return {
                    "name": name,
                    "status": "ok",
                    "rc": 0,
                    "duration_sec": 1.0,
                    "remaining_before_sec": 1000,
                    "remaining_after_sec": 999,
                    "cmd": list(cmd),
                    "log_file": str(out_dir / f"{name}.log"),
                    "reported_out_dir": reported_out_dir,
                    "summary_file": summary_file,
                }

            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(needs_fix_fast, "repo_root", return_value=root),
                mock.patch.object(needs_fix_fast, "ci_dir", return_value=out_dir),
                mock.patch.object(needs_fix_fast, "try_reuse_latest_deterministic_step", return_value=None),
                mock.patch.object(
                    needs_fix_fast,
                    "resolve_deterministic_execution_plan",
                    return_value={"mode": "full-pipeline", "cmd": ["py", "-3", "scripts/sc/run_review_pipeline.py"], "change_scope": {}},
                ),
                mock.patch.object(needs_fix_fast, "try_reuse_matching_minimal_acceptance_step", return_value=None),
                mock.patch.object(needs_fix_fast, "infer_initial_run_agents", return_value=(["code-reviewer"], "configured-defaults")),
                mock.patch.object(needs_fix_fast, "run_step", side_effect=_run_step),
            ):
                rc = needs_fix_fast.main()

            self.assertEqual(0, rc)
            llm_cmd = next(cmd for name, cmd in calls if name == "pipeline-llm-round-1")
            self.assertIn("--llm-backend", llm_cmd)
            self.assertEqual("openai-api", llm_cmd[llm_cmd.index("--llm-backend") + 1])

    def test_main_should_mark_timeout_only_round_as_indeterminate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-04-06" / "sc-needs-fix-fast-task-56"
            argv = [
                "llm_review_needs_fix_fast.py",
                "--task-id",
                "56",
                "--delivery-profile",
                "fast-ship",
                "--max-rounds",
                "1",
                "--agents",
                "code-reviewer",
            ]
            calls: list[tuple[str, list[str]]] = []

            def _run_step(*, name: str, cmd: list[str], out_dir: Path, timeout_sec: int, script_start: float, budget_min: int) -> dict[str, object]:
                calls.append((name, list(cmd)))
                if name == "pipeline-llm-round-1":
                    return {
                        "name": name,
                        "status": "fail",
                        "rc": 124,
                        "duration_sec": 10.0,
                        "remaining_before_sec": 1000,
                        "remaining_after_sec": 990,
                        "cmd": list(cmd),
                        "log_file": str(out_dir / f"{name}.log"),
                        "reported_out_dir": "",
                        "summary_file": "",
                    }
                return {
                    "name": name,
                    "status": "reused",
                    "rc": 0,
                    "duration_sec": 0.0,
                    "remaining_before_sec": 1000,
                    "remaining_after_sec": 1000,
                    "cmd": list(cmd),
                    "log_file": str(out_dir / f"{name}.log"),
                    "reported_out_dir": str(out_dir / "deterministic"),
                    "summary_file": str(out_dir / "deterministic" / "summary.json"),
                    "reused_run_id": "run-a",
                }

            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(needs_fix_fast, "repo_root", return_value=root),
                mock.patch.object(needs_fix_fast, "ci_dir", return_value=out_dir),
                mock.patch.object(needs_fix_fast, "try_skip_when_latest_pipeline_already_clean", return_value=None),
                mock.patch.object(needs_fix_fast, "try_reuse_latest_deterministic_step", return_value=None),
                mock.patch.object(
                    needs_fix_fast,
                    "resolve_deterministic_execution_plan",
                    return_value={"mode": "full-pipeline", "cmd": ["py", "-3", "scripts/sc/run_review_pipeline.py"], "change_scope": {}},
                ),
                mock.patch.object(needs_fix_fast, "infer_initial_run_agents", return_value=(["code-reviewer"], "configured-defaults")),
                mock.patch.object(needs_fix_fast, "run_step", side_effect=_run_step),
            ):
                rc = needs_fix_fast.main()

            self.assertEqual(1, rc)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("indeterminate", summary["status"])
            self.assertEqual("llm_review_verdict_unknown", summary["reason"])
            self.assertEqual(["code-reviewer"], summary["final_unknown_agents"])
            self.assertEqual(1, len(summary["rounds"]))
            round0 = summary["rounds"][0]
            self.assertEqual(1, round0["round"])
            self.assertEqual(1, round0["round_index"])
            self.assertEqual("fail", round0["status"])
            self.assertEqual(["code-reviewer"], round0["agents"])
            self.assertEqual(["code-reviewer"], round0["run_agents"])
            self.assertEqual("configured-defaults", round0["agent_source"])
            self.assertEqual(124, round0["rc"])
            self.assertEqual(1000, round0["remaining_before_sec"])
            self.assertEqual(990, round0["remaining_after_sec"])
            self.assertEqual("", round0["reported_out_dir"])
            self.assertTrue(str(round0["log_file"]).endswith("pipeline-llm-round-1.log"))
            self.assertEqual("", round0["summary_file"])
            self.assertEqual({"code-reviewer": "Unknown"}, round0["verdicts"])
            self.assertEqual("Unknown", round0["verdict"])
            self.assertEqual([], round0["needs_fix_agents"])
            self.assertEqual(["code-reviewer"], round0["timeout_agents"])
            self.assertEqual("timeout-no-summary", round0["failure_kind"])


class NeedsFixFastAlreadyCleanTests(unittest.TestCase):
    def test_main_should_noop_when_latest_pipeline_is_already_clean_and_only_docs_changed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            latest_out_dir = root / "logs" / "ci" / "2026-04-05" / "sc-review-pipeline-task-56-run-ok"
            latest_dir = root / "logs" / "ci" / "2026-04-05" / "sc-review-pipeline-task-56"
            llm_dir = latest_out_dir / "sc-llm-review-artifacts"
            latest_out_dir.mkdir(parents=True, exist_ok=True)
            latest_dir.mkdir(parents=True, exist_ok=True)
            llm_dir.mkdir(parents=True, exist_ok=True)
            (latest_dir / "latest.json").write_text(
                json.dumps(
                    {
                        "task_id": "56",
                        "run_id": "run-ok",
                        "status": "ok",
                        "latest_out_dir": str(latest_out_dir),
                        "summary_path": str(latest_out_dir / "summary.json"),
                        "execution_context_path": str(latest_out_dir / "execution-context.json"),
                    }
                ),
                encoding="utf-8",
            )
            (latest_out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "task_id": "56",
                        "status": "ok",
                        "steps": [
                            {"name": "sc-test", "status": "ok", "rc": 0},
                            {"name": "sc-acceptance-check", "status": "ok", "rc": 0},
                            {
                                "name": "sc-llm-review",
                                "status": "ok",
                                "rc": 0,
                                "reported_out_dir": str(llm_dir),
                                "summary_file": str(llm_dir / "summary.json"),
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (llm_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "status": "ok",
                        "results": [
                            {"agent": "code-reviewer", "status": "ok", "rc": 0, "details": {"verdict": "OK"}},
                            {"agent": "security-auditor", "status": "ok", "rc": 0, "details": {"verdict": "OK"}},
                            {"agent": "semantic-equivalence-auditor", "status": "ok", "rc": 0, "details": {"verdict": "OK"}},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (latest_out_dir / "execution-context.json").write_text(
                json.dumps(
                    {
                        "delivery_profile": "fast-ship",
                        "security_profile": "host-safe",
                        "git": {"head": "prev-head", "status_short": []},
                    }
                ),
                encoding="utf-8",
            )
            (latest_out_dir / "agent-review.json").write_text(
                json.dumps({"review_verdict": "pass", "findings": []}),
                encoding="utf-8",
            )

            out_dir = root / "logs" / "ci" / "2026-04-06" / "sc-needs-fix-fast-task-56"
            argv = [
                "llm_review_needs_fix_fast.py",
                "--task-id",
                "56",
                "--delivery-profile",
                "fast-ship",
            ]
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(needs_fix_fast, "repo_root", return_value=root),
                mock.patch.object(needs_fix_fast, "ci_dir", return_value=out_dir),
                mock.patch.object(
                    needs_fix_fast,
                    "current_git_fingerprint",
                    return_value={"head": "current-head", "status_short": []},
                ),
                mock.patch.object(
                    needs_fix_fast,
                    "classify_change_scope_between_snapshots",
                    return_value={
                        "deterministic_strategy": "reuse-latest",
                        "changed_paths": ["decision-logs/task-56.md"],
                        "unsafe_paths": [],
                    },
                ),
                mock.patch.object(needs_fix_fast, "run_step") as run_step_mock,
            ):
                rc = needs_fix_fast.main()

            self.assertEqual(0, rc)
            run_step_mock.assert_not_called()
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("ok", summary["status"])
            self.assertEqual("latest_pipeline_already_clean", summary["reason"])
            self.assertEqual("continue", summary["recommended_action"])
            self.assertIn("already clean", summary["recommended_action_why"].lower())
            self.assertEqual("reuse-latest", summary["change_scope"]["deterministic_strategy"])
            self.assertEqual("pipeline-clean-skip", summary["timeline"][0]["name"])

    def test_main_should_noop_for_final_pass_when_latest_pipeline_is_already_clean(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            latest_out_dir = root / "logs" / "ci" / "2026-04-05" / "sc-review-pipeline-task-56-run-ok"
            latest_dir = root / "logs" / "ci" / "2026-04-05" / "sc-review-pipeline-task-56"
            llm_dir = latest_out_dir / "sc-llm-review-artifacts"
            latest_out_dir.mkdir(parents=True, exist_ok=True)
            latest_dir.mkdir(parents=True, exist_ok=True)
            llm_dir.mkdir(parents=True, exist_ok=True)
            (latest_dir / "latest.json").write_text(
                json.dumps(
                    {
                        "task_id": "56",
                        "run_id": "run-ok",
                        "status": "ok",
                        "latest_out_dir": str(latest_out_dir),
                        "summary_path": str(latest_out_dir / "summary.json"),
                        "execution_context_path": str(latest_out_dir / "execution-context.json"),
                    }
                ),
                encoding="utf-8",
            )
            (latest_out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "task_id": "56",
                        "status": "ok",
                        "steps": [
                            {"name": "sc-test", "status": "ok", "rc": 0},
                            {"name": "sc-acceptance-check", "status": "ok", "rc": 0},
                            {
                                "name": "sc-llm-review",
                                "status": "ok",
                                "rc": 0,
                                "reported_out_dir": str(llm_dir),
                                "summary_file": str(llm_dir / "summary.json"),
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (llm_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "status": "ok",
                        "results": [
                            {"agent": "architect-reviewer", "status": "ok", "rc": 0, "details": {"verdict": "OK"}},
                            {"agent": "code-reviewer", "status": "ok", "rc": 0, "details": {"verdict": "OK"}},
                            {"agent": "security-auditor", "status": "ok", "rc": 0, "details": {"verdict": "OK"}},
                            {"agent": "test-automator", "status": "ok", "rc": 0, "details": {"verdict": "OK"}},
                            {"agent": "semantic-equivalence-auditor", "status": "ok", "rc": 0, "details": {"verdict": "OK"}},
                            {"agent": "adr-compliance-checker", "status": "ok", "rc": 0, "details": {"verdict": "OK"}},
                            {"agent": "performance-slo-validator", "status": "ok", "rc": 0, "details": {"verdict": "OK"}},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (latest_out_dir / "execution-context.json").write_text(
                json.dumps(
                    {
                        "delivery_profile": "standard",
                        "security_profile": "strict",
                        "git": {"head": "same-head", "status_short": []},
                    }
                ),
                encoding="utf-8",
            )
            (latest_out_dir / "agent-review.json").write_text(
                json.dumps({"review_verdict": "pass", "findings": []}),
                encoding="utf-8",
            )

            out_dir = root / "logs" / "ci" / "2026-04-06" / "sc-needs-fix-fast-task-56"
            argv = [
                "llm_review_needs_fix_fast.py",
                "--task-id",
                "56",
                "--delivery-profile",
                "standard",
                "--final-pass",
            ]
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(needs_fix_fast, "repo_root", return_value=root),
                mock.patch.object(needs_fix_fast, "ci_dir", return_value=out_dir),
                mock.patch.object(needs_fix_fast, "current_git_fingerprint", return_value={"head": "same-head", "status_short": []}),
                mock.patch.object(needs_fix_fast, "run_step") as run_step_mock,
            ):
                rc = needs_fix_fast.main()

            self.assertEqual(0, rc)
            run_step_mock.assert_not_called()
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("ok", summary["status"])
            self.assertEqual("latest_pipeline_already_clean", summary["reason"])
            self.assertEqual("pipeline-clean-skip", summary["timeline"][0]["name"])


class NeedsFixFastUnknownStopLossTests(unittest.TestCase):
    def test_main_should_stop_when_previous_llm_was_unknown_and_current_changes_do_not_hit_reviewer_anchors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            latest_out_dir = root / "logs" / "ci" / "2026-04-05" / "sc-review-pipeline-task-56-run-timeout"
            latest_dir = root / "logs" / "ci" / "2026-04-05" / "sc-review-pipeline-task-56"
            latest_out_dir.mkdir(parents=True, exist_ok=True)
            latest_dir.mkdir(parents=True, exist_ok=True)
            (latest_dir / "latest.json").write_text(
                json.dumps(
                    {
                        "task_id": "56",
                        "run_id": "run-timeout",
                        "status": "fail",
                        "latest_out_dir": str(latest_out_dir),
                        "summary_path": str(latest_out_dir / "summary.json"),
                        "execution_context_path": str(latest_out_dir / "execution-context.json"),
                    }
                ),
                encoding="utf-8",
            )
            (latest_out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "task_id": "56",
                        "status": "fail",
                        "steps": [
                            {"name": "sc-test", "status": "ok", "rc": 0},
                            {"name": "sc-acceptance-check", "status": "ok", "rc": 0},
                            {"name": "sc-llm-review", "status": "fail", "rc": 124, "summary_file": ""},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (latest_out_dir / "execution-context.json").write_text(
                json.dumps(
                    {
                        "delivery_profile": "fast-ship",
                        "security_profile": "host-safe",
                        "git": {"head": "same-head", "status_short": []},
                    }
                ),
                encoding="utf-8",
            )
            out_dir = root / "logs" / "ci" / "2026-04-06" / "sc-needs-fix-fast-task-56"
            argv = [
                "llm_review_needs_fix_fast.py",
                "--task-id",
                "56",
                "--delivery-profile",
                "fast-ship",
                "--agents",
                "code-reviewer",
            ]
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(needs_fix_fast, "repo_root", return_value=root),
                mock.patch.object(needs_fix_fast, "ci_dir", return_value=out_dir),
                mock.patch.object(needs_fix_fast, "current_git_fingerprint", return_value={"head": "same-head", "status_short": []}),
                mock.patch.object(
                    needs_fix_fast,
                    "classify_change_scope_between_snapshots",
                    return_value={
                        "deterministic_strategy": "reuse-latest",
                        "changed_paths": ["docs/workflows/project-health-dashboard.md"],
                        "unsafe_paths": [],
                    },
                ),
                mock.patch.object(needs_fix_fast, "run_step") as run_step_mock,
            ):
                rc = needs_fix_fast.main()

            self.assertEqual(1, rc)
            run_step_mock.assert_not_called()
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("indeterminate", summary["status"])
            self.assertEqual("no_anchor_fix_for_previous_llm_unknown", summary["reason"])
            self.assertEqual("inspect", summary["recommended_action"])
            self.assertIn("anchor", summary["recommended_action_why"].lower())
            self.assertEqual(["code-reviewer"], summary["final_unknown_agents"])
            self.assertEqual("pipeline-llm-unknown-stop-loss", summary["timeline"][0]["name"])


class NeedsFixFastChapter6RouteTests(unittest.TestCase):
    def test_main_should_stop_before_deterministic_when_chapter6_route_requests_inspect_first(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-04-10" / "sc-needs-fix-fast-task-56"
            argv = [
                "llm_review_needs_fix_fast.py",
                "--task-id",
                "56",
                "--delivery-profile",
                "fast-ship",
            ]

            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(needs_fix_fast, "repo_root", return_value=root),
                mock.patch.object(needs_fix_fast, "ci_dir", return_value=out_dir),
                mock.patch.object(needs_fix_fast, "try_skip_when_latest_pipeline_already_clean", return_value=None),
                mock.patch.object(needs_fix_fast, "try_stop_when_latest_llm_unknown_without_anchor_fix", return_value=None),
                mock.patch.object(
                    needs_fix_fast,
                    "_run_chapter6_route_preflight",
                    return_value={
                        "task_id": "56",
                        "run_id": "route-run",
                        "preferred_lane": "inspect-first",
                        "recommended_command": "py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id 56",
                        "blocked_by": "recent_failure_summary",
                        "repo_noise_classification": "task-issue",
                    },
                ),
                mock.patch.object(needs_fix_fast, "run_step") as run_step_mock,
            ):
                rc = needs_fix_fast.main()

            self.assertEqual(1, rc)
            run_step_mock.assert_not_called()
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("indeterminate", summary["status"])
            self.assertEqual("chapter6_route_inspect_first", summary["reason"])
            self.assertEqual("inspect", summary["recommended_action"])
            self.assertIn("inspect first", summary["recommended_action_why"].lower())
            self.assertEqual("inspect-first", summary["route_preflight"]["preferred_lane"])
            self.assertEqual("chapter6-route-preflight", summary["timeline"][0]["name"])

    def test_main_should_continue_when_chapter6_route_requests_run_6_8(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-04-10" / "sc-needs-fix-fast-task-56"
            argv = [
                "llm_review_needs_fix_fast.py",
                "--task-id",
                "56",
                "--delivery-profile",
                "fast-ship",
                "--agents",
                "code-reviewer",
                "--max-rounds",
                "1",
            ]
            calls: list[str] = []

            def _run_step(*, name: str, cmd: list[str], out_dir: Path, timeout_sec: int, script_start: float, budget_min: int) -> dict[str, object]:
                calls.append(name)
                reported_out_dir, summary_file = _write_llm_pipeline_artifacts(
                    out_dir,
                    name,
                    results=[{"agent": "code-reviewer", "status": "ok", "rc": 0, "details": {"verdict": "OK"}}],
                )
                return {
                    "name": name,
                    "status": "ok",
                    "rc": 0,
                    "duration_sec": 1.0,
                    "remaining_before_sec": 1000,
                    "remaining_after_sec": 999,
                    "cmd": list(cmd),
                    "log_file": str(out_dir / f"{name}.log"),
                    "reported_out_dir": reported_out_dir,
                    "summary_file": summary_file,
                }

            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(needs_fix_fast, "repo_root", return_value=root),
                mock.patch.object(needs_fix_fast, "ci_dir", return_value=out_dir),
                mock.patch.object(needs_fix_fast, "try_skip_when_latest_pipeline_already_clean", return_value=None),
                mock.patch.object(needs_fix_fast, "try_stop_when_latest_llm_unknown_without_anchor_fix", return_value=None),
                mock.patch.object(
                    needs_fix_fast,
                    "_run_chapter6_route_preflight",
                    return_value={
                        "task_id": "56",
                        "run_id": "route-run",
                        "preferred_lane": "run-6.8",
                        "recommended_command": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 56",
                        "repo_noise_classification": "task-issue",
                    },
                ),
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
                        "reported_out_dir": str(out_dir / "deterministic"),
                        "summary_file": str(out_dir / "deterministic" / "summary.json"),
                        "reused_run_id": "run-ok",
                        "reuse_reason": "latest_successful_deterministic_pipeline",
                    },
                ),
                mock.patch.object(needs_fix_fast, "infer_initial_run_agents", return_value=(["code-reviewer"], "configured-defaults")),
                mock.patch.object(needs_fix_fast, "run_step", side_effect=_run_step),
            ):
                rc = needs_fix_fast.main()

            self.assertEqual(0, rc)
            self.assertEqual(["pipeline-llm-round-1"], calls)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("run-6.8", summary["route_preflight"]["preferred_lane"])
            self.assertEqual("ok", summary["status"])
            self.assertEqual("pipeline-llm-round", summary["dominant_cost_phase"])
            self.assertEqual(
                {
                    "chapter6-route-preflight": 0.0,
                    "pipeline-deterministic": 0.0,
                    "pipeline-llm-round": 1.0,
                },
                summary["step_duration_totals"],
            )
            self.assertEqual(
                {
                    "chapter6-route-preflight": 1,
                    "pipeline-deterministic": 1,
                    "pipeline-llm-round": 1,
                },
                summary["step_duration_counts"],
            )
            self.assertEqual({}, summary["round_failure_kind_counts"])

    def test_main_should_record_residual_and_stop_without_running_llm(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-04-10" / "sc-needs-fix-fast-task-56"
            argv = [
                "llm_review_needs_fix_fast.py",
                "--task-id",
                "56",
                "--delivery-profile",
                "fast-ship",
            ]

            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(needs_fix_fast, "repo_root", return_value=root),
                mock.patch.object(needs_fix_fast, "ci_dir", return_value=out_dir),
                mock.patch.object(needs_fix_fast, "try_skip_when_latest_pipeline_already_clean", return_value=None),
                mock.patch.object(needs_fix_fast, "try_stop_when_latest_llm_unknown_without_anchor_fix", return_value=None),
                mock.patch.object(
                    needs_fix_fast,
                    "_run_chapter6_route_preflight",
                    return_value={
                        "task_id": "56",
                        "run_id": "route-run",
                        "preferred_lane": "record-residual",
                        "recommended_command": "py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id 56",
                        "repo_noise_classification": "task-issue",
                        "residual_recording": {
                            "eligible": True,
                            "performed": True,
                            "decision_log_path": "decision-logs/task-56-chapter6-residual-needs-fix.md",
                            "execution_plan_path": "execution-plans/task-56-chapter6-residual-followup.md",
                        },
                    },
                ),
                mock.patch.object(needs_fix_fast, "run_step") as run_step_mock,
            ):
                rc = needs_fix_fast.main()

            self.assertEqual(0, rc)
            run_step_mock.assert_not_called()
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("ok", summary["status"])
            self.assertEqual("chapter6_route_recorded_residual", summary["reason"])
            self.assertTrue(summary["residual_recording"]["performed"])


class NeedsFixFastBudgetPredictionTests(unittest.TestCase):
    def test_main_should_stop_before_llm_when_recent_timeout_history_exceeds_remaining_budget(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            previous_out_dir = root / "logs" / "ci" / "2026-04-05" / "sc-needs-fix-fast-task-56"
            previous_out_dir.mkdir(parents=True, exist_ok=True)
            (previous_out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "task_id": "56",
                        "status": "indeterminate",
                        "args": {
                            "delivery_profile": "fast-ship",
                            "security_profile": "host-safe",
                            "diff_mode": "summary",
                            "llm_timeout_sec": 600,
                        },
                        "timeline": [
                            {
                                "name": "pipeline-llm-round-1",
                                "duration_sec": 660.0,
                            }
                        ],
                        "rounds": [
                            {
                                "round": 1,
                                "agents": ["code-reviewer"],
                                "timeout_agents": ["code-reviewer"],
                                "failure_kind": "timeout-no-summary",
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            out_dir = root / "logs" / "ci" / "2026-04-06" / "sc-needs-fix-fast-task-56"
            argv = [
                "llm_review_needs_fix_fast.py",
                "--task-id",
                "56",
                "--delivery-profile",
                "fast-ship",
                "--agents",
                "code-reviewer",
                "--diff-mode",
                "summary",
                "--time-budget-min",
                "10",
                "--llm-timeout-sec",
                "600",
                "--agent-timeout-sec",
                "300",
            ]
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(needs_fix_fast, "repo_root", return_value=root),
                mock.patch.object(needs_fix_fast, "ci_dir", return_value=out_dir),
                mock.patch.object(needs_fix_fast, "try_skip_when_latest_pipeline_already_clean", return_value=None),
                mock.patch.object(needs_fix_fast, "try_stop_when_latest_llm_unknown_without_anchor_fix", return_value=None),
                mock.patch.object(
                    needs_fix_fast,
                    "try_reuse_latest_deterministic_step",
                    return_value={
                        "name": "pipeline-deterministic",
                        "status": "reused",
                        "rc": 0,
                        "duration_sec": 0.0,
                        "remaining_before_sec": 600,
                        "remaining_after_sec": 600,
                        "cmd": ["py", "-3", "scripts/sc/run_review_pipeline.py"],
                        "log_file": str(out_dir / "pipeline-deterministic.log"),
                        "reported_out_dir": str(out_dir / "deterministic"),
                        "summary_file": str(out_dir / "deterministic" / "summary.json"),
                        "reused_run_id": "prev",
                    },
                ),
                mock.patch.object(
                    needs_fix_fast,
                    "resolve_deterministic_execution_plan",
                    return_value={"mode": "full-pipeline", "cmd": ["py", "-3", "scripts/sc/run_review_pipeline.py"], "change_scope": {}},
                ),
                mock.patch.object(needs_fix_fast, "infer_initial_run_agents", return_value=(["code-reviewer"], "configured-defaults")),
                mock.patch.object(needs_fix_fast, "run_step") as run_step_mock,
            ):
                rc = needs_fix_fast.main()

            self.assertEqual(1, rc)
            run_step_mock.assert_not_called()
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("insufficient_llm_budget_before_llm", summary["reason"])
            self.assertEqual("predicted_insufficient_llm_budget", summary["timeline"][-1]["error"])
            self.assertEqual(1, summary["llm_budget_prediction_history"][0]["matched_timeout_rounds"])
            self.assertGreaterEqual(summary["llm_budget_prediction_history"][0]["predicted_budget_sec"], 720)


class NeedsFixFastTargetedReviewerSelectionTests(unittest.TestCase):
    def test_prefer_targeted_agents_by_change_scope_should_keep_security_for_game_core_changes(self) -> None:
        agents, source = needs_fix_fast.prefer_targeted_agents_by_change_scope(
            configured_agents=["code-reviewer", "security-auditor", "semantic-equivalence-auditor"],
            current_agents=["code-reviewer", "security-auditor", "semantic-equivalence-auditor"],
            current_source="configured-defaults",
            change_scope={
                "changed_paths": ["Game.Core/Combat/AttackResolver.cs"],
                "unsafe_paths": ["Game.Core/Combat/AttackResolver.cs"],
            },
        )

        self.assertEqual(["code-reviewer", "security-auditor"], agents)
        self.assertEqual("change-scope-targeted", source)

    def test_main_should_target_semantic_reviewer_when_change_scope_is_task_semantics_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-04-06" / "sc-needs-fix-fast-task-56"
            argv = [
                "llm_review_needs_fix_fast.py",
                "--task-id",
                "56",
                "--delivery-profile",
                "fast-ship",
            ]
            calls: list[tuple[str, list[str]]] = []

            def _run_step(*, name: str, cmd: list[str], out_dir: Path, timeout_sec: int, script_start: float, budget_min: int) -> dict[str, object]:
                calls.append((name, list(cmd)))
                if name == "pipeline-deterministic-minimal-acceptance":
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
                reported_out_dir, summary_file = _write_llm_pipeline_artifacts(
                    out_dir,
                    name,
                    results=[
                        {"agent": "semantic-equivalence-auditor", "status": "ok", "rc": 0, "details": {"verdict": "OK"}},
                    ],
                )
                return {
                    "name": name,
                    "status": "ok",
                    "rc": 0,
                    "duration_sec": 1.0,
                    "remaining_before_sec": 999,
                    "remaining_after_sec": 998,
                    "cmd": list(cmd),
                    "log_file": str(out_dir / f"{name}.log"),
                    "reported_out_dir": reported_out_dir,
                    "summary_file": summary_file,
                }

            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(needs_fix_fast, "repo_root", return_value=root),
                mock.patch.object(needs_fix_fast, "ci_dir", return_value=out_dir),
                mock.patch.object(needs_fix_fast, "try_skip_when_latest_pipeline_already_clean", return_value=None),
                mock.patch.object(needs_fix_fast, "try_stop_when_latest_llm_unknown_without_anchor_fix", return_value=None),
                mock.patch.object(needs_fix_fast, "try_reuse_latest_deterministic_step", return_value=None),
                mock.patch.object(
                    needs_fix_fast,
                    "resolve_deterministic_execution_plan",
                    return_value={
                        "mode": "minimal-acceptance",
                        "cmd": ["py", "-3", "scripts/sc/acceptance_check.py", "--task-id", "56", "--only", "adr,links,overlay"],
                        "change_scope": {
                            "deterministic_strategy": "minimal-acceptance",
                            "changed_paths": ["docs/architecture/overlays/PRD-NEWROUGE-GAME-0001/08/feature.md"],
                            "task_semantic_paths": ["docs/architecture/overlays/PRD-NEWROUGE-GAME-0001/08/feature.md"],
                        },
                    },
                ),
                mock.patch.object(needs_fix_fast, "try_reuse_matching_minimal_acceptance_step", return_value=None),
                mock.patch.object(needs_fix_fast, "infer_initial_run_agents", return_value=(["code-reviewer", "security-auditor", "semantic-equivalence-auditor"], "configured-defaults")),
                mock.patch.object(needs_fix_fast, "run_step", side_effect=_run_step),
            ):
                rc = needs_fix_fast.main()

            self.assertEqual(0, rc)
            llm_cmd = calls[1][1]
            self.assertEqual("pipeline-llm-round-1", calls[1][0])
            self.assertIn("--llm-agents", llm_cmd)
            self.assertEqual("semantic-equivalence-auditor", llm_cmd[llm_cmd.index("--llm-agents") + 1])
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(["semantic-equivalence-auditor"], summary["args"]["initial_run_agents"])
            self.assertEqual("change-scope-targeted", summary["args"]["initial_run_agents_source"])


class NeedsFixFastRepeatedNeedsFixStopLossTests(unittest.TestCase):
    def test_main_should_stop_after_second_identical_needs_fix_round(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-04-06" / "sc-needs-fix-fast-task-56"
            argv = [
                "llm_review_needs_fix_fast.py",
                "--task-id",
                "56",
                "--delivery-profile",
                "fast-ship",
                "--max-rounds",
                "3",
                "--agents",
                "code-reviewer,security-auditor,semantic-equivalence-auditor",
            ]
            calls: list[str] = []

            def _run_step(*, name: str, cmd: list[str], out_dir: Path, timeout_sec: int, script_start: float, budget_min: int) -> dict[str, object]:
                calls.append(name)
                if name == "pipeline-deterministic":
                    return {
                        "name": name,
                        "status": "ok",
                        "rc": 0,
                        "duration_sec": 1.0,
                        "remaining_before_sec": 1000,
                        "remaining_after_sec": 999,
                        "cmd": list(cmd),
                        "log_file": str(out_dir / f"{name}.log"),
                        "reported_out_dir": str(out_dir / "deterministic"),
                        "summary_file": str(out_dir / "deterministic" / "summary.json"),
                    }
                reported_out_dir, summary_file = _write_llm_pipeline_artifacts(
                    out_dir,
                    name,
                    results=[
                        {"agent": "code-reviewer", "status": "ok", "rc": 0, "details": {"verdict": "Needs Fix"}},
                    ],
                )
                return {
                    "name": name,
                    "status": "ok",
                    "rc": 0,
                    "duration_sec": 1.0,
                    "remaining_before_sec": 999,
                    "remaining_after_sec": 998,
                    "cmd": list(cmd),
                    "log_file": str(out_dir / f"{name}.log"),
                    "reported_out_dir": reported_out_dir,
                    "summary_file": summary_file,
                }

            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(needs_fix_fast, "repo_root", return_value=root),
                mock.patch.object(needs_fix_fast, "ci_dir", return_value=out_dir),
                mock.patch.object(needs_fix_fast, "try_skip_when_latest_pipeline_already_clean", return_value=None),
                mock.patch.object(needs_fix_fast, "try_stop_when_latest_llm_unknown_without_anchor_fix", return_value=None),
                mock.patch.object(needs_fix_fast, "try_reuse_latest_deterministic_step", return_value=None),
                mock.patch.object(
                    needs_fix_fast,
                    "resolve_deterministic_execution_plan",
                    return_value={"mode": "full-pipeline", "cmd": ["py", "-3", "scripts/sc/run_review_pipeline.py"], "change_scope": {}},
                ),
                mock.patch.object(needs_fix_fast, "infer_initial_run_agents", return_value=(["code-reviewer"], "previous-llm-summary")),
                mock.patch.object(needs_fix_fast, "run_step", side_effect=_run_step),
            ):
                rc = needs_fix_fast.main()

            self.assertEqual(1, rc)
            self.assertEqual(["pipeline-deterministic", "pipeline-llm-round-1", "pipeline-llm-round-2"], calls)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("needs-fix", summary["status"])
            self.assertEqual("repeated_needs_fix_no_progress", summary["reason"])
            self.assertEqual("record-residual", summary["recommended_action"])
            self.assertIn("no progress", summary["recommended_action_why"].lower())
            self.assertTrue(summary["stop_loss"]["triggered"])
            self.assertEqual("repeated-needs-fix-signature", summary["stop_loss"]["kind"])
            self.assertEqual(2, summary["stop_loss"]["round"])
            self.assertEqual("pipeline-llm-round", summary["dominant_cost_phase"])
            self.assertEqual({"pipeline-deterministic": 1.0, "pipeline-llm-round": 2.0}, summary["step_duration_totals"])
            self.assertEqual({}, summary["round_failure_kind_counts"])

if __name__ == "__main__":
    unittest.main()
