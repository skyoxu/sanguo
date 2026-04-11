#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
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


resume_task = _load_module("resume_task_module", "scripts/python/resume_task.py")


def _resume_task_recommendation_payload() -> dict:
    return {
        "task_id": "15",
        "run_id": "run-15",
        "recommended_action": "needs-fix-fast",
        "recommended_command": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 15 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
        "forbidden_commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 15"],
        "inspection": {
            "paths": {
                "latest": "logs/ci/2026-04-10/sc-review-pipeline-task-15/latest.json",
            }
        },
        "latest_summary_signals": {
            "reason": "rerun_blocked:repeat_review_needs_fix",
        },
        "chapter6_hints": {
            "next_action": "needs-fix-fast",
            "blocked_by": "rerun_guard",
        },
        "approval": {
            "status": "pending",
            "recommended_action": "pause",
            "allowed_actions": ["inspect", "pause"],
            "blocked_actions": ["fork", "resume", "rerun"],
        },
        "run_event_summary": {
            "latest_turn_id": "run-15:turn-2",
            "turn_count": 2,
        },
        "active_task": {},
    }


class ResumeTaskTests(unittest.TestCase):
    def test_resume_task_compact_example_should_match_renderer(self) -> None:
        example_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-resume-task-compact.example.json"
        stdout_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-resume-task-compact.stdout.example.txt"

        payload = _resume_task_recommendation_payload()
        expected = json.loads(example_path.read_text(encoding="utf-8"))
        expected_stdout = stdout_path.read_text(encoding="utf-8")

        actual_payload = resume_task._compact_recommendation_payload(payload)
        actual_stdout = resume_task._render_recommendation_only(payload)

        self.assertEqual(expected, actual_payload)
        self.assertEqual(expected_stdout, actual_stdout)
        self.assertEqual("unknown", actual_payload["failure_code"])
        self.assertEqual("pause", actual_payload["approval_recommended_action"])
        self.assertEqual("run-15:turn-2", actual_payload["latest_turn"])

    def test_resume_task_main_recommendation_only_should_match_compact_stdout_example(self) -> None:
        example_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-resume-task-compact.example.json"
        stdout_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-resume-task-compact.stdout.example.txt"
        payload = _resume_task_recommendation_payload()
        expected_stdout = stdout_path.read_text(encoding="utf-8")

        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            stdout = io.StringIO()
            with (
                mock.patch.object(resume_task, "build_resume_payload", return_value=(1, payload)),
                mock.patch.object(resume_task, "_repair_active_task_latest_pointer", return_value={"repaired": False}),
                redirect_stdout(stdout),
            ):
                rc = resume_task.main(
                    [
                        "--repo-root",
                        str(repo_root),
                        "--task-id",
                        "15",
                        "--recommendation-only",
                    ]
                )

        self.assertEqual(0, rc)
        self.assertEqual(expected_stdout, stdout.getvalue())

    def test_resume_task_main_recommendation_only_json_should_match_compact_example(self) -> None:
        example_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-resume-task-compact.example.json"
        payload = _resume_task_recommendation_payload()
        expected = json.loads(example_path.read_text(encoding="utf-8"))

        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            stdout = io.StringIO()
            with (
                mock.patch.object(resume_task, "build_resume_payload", return_value=(1, payload)),
                mock.patch.object(resume_task, "_repair_active_task_latest_pointer", return_value={"repaired": False}),
                redirect_stdout(stdout),
            ):
                rc = resume_task.main(
                    [
                        "--repo-root",
                        str(repo_root),
                        "--task-id",
                        "15",
                        "--recommendation-only",
                        "--recommendation-format",
                        "json",
                    ]
                )

        self.assertEqual(0, rc)
        self.assertEqual(expected, json.loads(stdout.getvalue()))

    def test_approval_route_should_override_stale_recommended_command_and_forbidden_commands(self) -> None:
        commands = {
            "inspect": "py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id 15",
            "resume": "py -3 scripts/sc/run_review_pipeline.py --task-id 15 --resume",
            "fork": "py -3 scripts/sc/run_review_pipeline.py --task-id 15 --fork",
            "rerun": "py -3 scripts/sc/run_review_pipeline.py --task-id 15",
            "needs_fix_fast": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 15 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
        }
        chapter6_hints = {
            "next_action": "resume",
            "blocked_by": "approval_pending",
            "rerun_forbidden": True,
            "rerun_override_flag": "",
        }
        approval = {
            "required_action": "fork",
            "status": "pending",
            "recommended_action": "pause",
            "allowed_actions": ["inspect", "pause"],
            "blocked_actions": ["fork", "resume", "rerun"],
        }

        recommended = resume_task._recommended_command("resume", commands, chapter6_hints, approval)
        forbidden = resume_task._forbidden_commands(
            recommended_action="resume",
            commands=commands,
            chapter6_hints=chapter6_hints,
            approval=approval,
        )

        self.assertEqual("", recommended)
        self.assertIn(commands["resume"], forbidden)
        self.assertIn(commands["fork"], forbidden)
        self.assertIn(commands["rerun"], forbidden)
        self.assertIn(commands["needs_fix_fast"], forbidden)

    def test_repair_active_task_latest_pointer_should_rebuild_sidecar_from_canonical_latest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            latest_run_id = "1601f1321a2a45d5ac11fff0b718aa14"
            latest_out_dir = repo_root / "logs" / "ci" / "2026-04-06" / f"sc-review-pipeline-task-14-{latest_run_id}"
            latest_out_dir.mkdir(parents=True, exist_ok=True)
            (latest_out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "cmd": "sc-review-pipeline",
                        "task_id": "14",
                        "run_id": latest_run_id,
                        "status": "ok",
                        "reason": "pipeline_clean",
                        "run_type": "full",
                        "reuse_mode": "none",
                        "steps": [
                            {"name": "sc-test", "status": "ok"},
                            {"name": "sc-acceptance-check", "status": "ok"},
                            {"name": "sc-llm-review", "status": "ok"},
                        ],
                        "started_at_utc": "2026-04-06T00:00:00+00:00",
                        "finished_at_utc": "2026-04-06T00:02:00+00:00",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (latest_out_dir / "execution-context.json").write_text(
                json.dumps(
                    {
                        "cmd": "sc-review-pipeline",
                        "task_id": "14",
                        "run_id": latest_run_id,
                        "status": "ok",
                        "delivery_profile": "fast-ship",
                        "security_profile": "host-safe",
                        "diagnostics": {},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (latest_out_dir / "repair-guide.json").write_text(
                json.dumps(
                    {
                        "status": "not-needed",
                        "task_id": "14",
                        "summary_status": "ok",
                        "failed_step": "",
                        "recommendations": [],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (latest_out_dir / "repair-guide.md").write_text("# repair\n", encoding="utf-8")
            (latest_out_dir / "run-events.jsonl").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "ts": "2026-04-06T00:02:00Z",
                        "event": "run_completed",
                        "task_id": "14",
                        "run_id": latest_run_id,
                        "delivery_profile": "fast-ship",
                        "security_profile": "host-safe",
                        "step_name": None,
                        "status": "ok",
                        "details": {},
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            latest_path = repo_root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-14" / "latest.json"
            latest_path.parent.mkdir(parents=True, exist_ok=True)
            latest_path.write_text(
                json.dumps(
                    {
                        "task_id": "14",
                        "run_id": latest_run_id,
                        "status": "ok",
                        "latest_out_dir": str(latest_out_dir),
                        "summary_path": str(latest_out_dir / "summary.json"),
                        "execution_context_path": str(latest_out_dir / "execution-context.json"),
                        "repair_guide_json_path": str(latest_out_dir / "repair-guide.json"),
                        "repair_guide_md_path": str(latest_out_dir / "repair-guide.md"),
                        "run_events_path": str(latest_out_dir / "run-events.jsonl"),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            active_task_json = repo_root / "logs" / "ci" / "active-tasks" / "task-14.active.json"
            active_task_json.parent.mkdir(parents=True, exist_ok=True)
            active_task_json.write_text(
                json.dumps(
                    {
                        "task_id": "14",
                        "run_id": "stale-run",
                        "status": "ok",
                        "recommended_action": "continue",
                        "recommended_action_why": "Pipeline is green; continue the task or start the next task.",
                        "paths": {
                            "latest_json": "logs/ci/2026-04-07/sc-review-pipeline-task-14/latest.json",
                            "out_dir": "logs/ci/2026-04-07/sc-review-pipeline-task-14-stale-run",
                            "summary_json": "logs/ci/2026-04-07/sc-review-pipeline-task-14-stale-run/summary.json",
                        },
                        "latest_summary_signals": {
                            "reason": "in_progress",
                            "reuse_mode": "none",
                            "diagnostics_keys": ["profile_floor"],
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            active_task_md = active_task_json.with_suffix(".md")
            active_task_md.write_text("- Latest pointer: `logs/ci/2026-04-07/sc-review-pipeline-task-14/latest.json`\n", encoding="utf-8")

            repair = resume_task._repair_active_task_latest_pointer(
                repo_root,
                task_id="14",
                resolved_latest="logs/ci/2026-04-06/sc-review-pipeline-task-14/latest.json",
            )

            self.assertTrue(repair["repaired"])
            repaired_payload = json.loads(active_task_json.read_text(encoding="utf-8"))
            self.assertEqual(latest_run_id, repaired_payload["run_id"])
            self.assertTrue(repaired_payload["latest_json_repaired"])
            self.assertFalse(repaired_payload["latest_json_mismatch"])
            self.assertEqual(
                "logs/ci/2026-04-07/sc-review-pipeline-task-14/latest.json",
                repaired_payload["reported_latest_json"],
            )
            self.assertEqual("logs/ci/2026-04-06/sc-review-pipeline-task-14/latest.json", repaired_payload["paths"]["latest_json"])
            self.assertEqual("pipeline_clean", repaired_payload["latest_summary_signals"]["reason"])
            self.assertEqual("continue", repaired_payload["recommended_action"])
            self.assertIn("logs/ci/2026-04-06/sc-review-pipeline-task-14/latest.json", active_task_md.read_text(encoding="utf-8"))

    def test_build_resume_payload_should_prefer_inspection_latest_summary_signals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            latest_path = repo_root / "logs" / "ci" / "2026-04-07" / "sc-review-pipeline-task-14" / "latest.json"
            latest_path.parent.mkdir(parents=True, exist_ok=True)
            latest_path.write_text(
                json.dumps(
                    {
                        "reason": "from-latest-json",
                        "run_type": "deterministic-only",
                        "reuse_mode": "latest-json-reuse",
                        "diagnostics": {
                            "from_latest_json": True,
                            "artifact_integrity": {"kind": "planned_only_incomplete", "blocked": True},
                        },
                    }
                ),
                encoding="utf-8",
            )
            inspection = {
                "task_id": "14",
                "run_id": "run-14",
                "failure": {"code": "review-needs-fix"},
                "paths": {
                    "latest": "logs/ci/2026-04-07/sc-review-pipeline-task-14/latest.json",
                    "out_dir": "",
                },
                "latest_summary_signals": {
                    "reason": "from-inspection",
                    "run_type": "deterministic-only",
                    "reuse_mode": "inspection-reuse",
                    "diagnostics_keys": ["from_inspection"],
                },
                "chapter6_hints": {
                    "next_action": "needs-fix-fast",
                    "can_skip_6_7": True,
                    "can_go_to_6_8": True,
                    "blocked_by": "rerun_guard",
                    "rerun_forbidden": True,
                    "rerun_override_flag": "--allow-full-rerun",
                },
            }
            with mock.patch.object(resume_task, "inspect_run_artifacts", return_value=(0, inspection)):
                _, payload = resume_task.build_resume_payload(
                    repo_root=repo_root,
                    task_id="14",
                    latest="",
                    run_id="",
                )

        self.assertEqual(
            payload["latest_summary_signals"],
            {
                "reason": "from-inspection",
                "run_type": "deterministic-only",
                "reuse_mode": "inspection-reuse",
                "artifact_integrity_kind": "planned_only_incomplete",
                "diagnostics_keys": ["from_inspection"],
            },
        )
        self.assertEqual(
            payload["chapter6_hints"],
            {
                "next_action": "needs-fix-fast",
                "can_skip_6_7": True,
                "can_go_to_6_8": True,
                "blocked_by": "rerun_guard",
                "rerun_forbidden": True,
                "rerun_override_flag": "--allow-full-rerun",
            },
        )
        self.assertEqual(
            "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 14 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
            payload["recommended_command"],
        )
        self.assertIn(
            "py -3 scripts/sc/run_review_pipeline.py --task-id 14",
            payload["forbidden_commands"],
        )


    def test_build_resume_payload_should_prefer_pipeline_summary_recommendation_over_active_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            summary_path = repo_root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-14-run-14" / "summary.json"
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            summary_path.write_text(
                json.dumps(
                    {
                        "cmd": "sc-review-pipeline",
                        "task_id": "14",
                        "requested_run_id": "run-14",
                        "run_id": "run-14",
                        "allow_overwrite": False,
                        "force_new_run_id": False,
                        "status": "fail",
                        "steps": [
                            {
                                "name": "sc-test",
                                "cmd": ["py", "-3", "scripts/sc/test.py"],
                                "rc": 0,
                                "status": "ok",
                                "log": "logs/ci/2026-04-10/sc-review-pipeline-task-14-run-14/sc-test.log",
                            }
                        ],
                        "started_at_utc": "2026-04-10T00:00:00+00:00",
                        "finished_at_utc": "2026-04-10T00:00:05+00:00",
                        "elapsed_sec": 5,
                        "run_type": "full",
                        "reason": "rerun_blocked:repeat_review_needs_fix",
                        "reuse_mode": "deterministic-only-reuse",
                        "latest_summary_signals": {
                            "reason": "rerun_blocked:repeat_review_needs_fix",
                            "run_type": "full",
                            "reuse_mode": "deterministic-only-reuse",
                            "artifact_integrity_kind": "",
                            "diagnostics_keys": ["rerun_guard"],
                        },
                        "chapter6_hints": {
                            "next_action": "needs-fix-fast",
                            "can_skip_6_7": True,
                            "can_go_to_6_8": True,
                            "blocked_by": "rerun_guard",
                            "rerun_forbidden": True,
                            "rerun_override_flag": "--allow-full-rerun",
                        },
                        "recommended_action": "needs-fix-fast",
                        "recommended_action_why": "repeat reviewer family",
                        "candidate_commands": {
                            "needs_fix_fast": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 14 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
                            "rerun": "py -3 scripts/sc/run_review_pipeline.py --task-id 14",
                        },
                        "recommended_command": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 14 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
                        "forbidden_commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 14"],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            active_task_path = repo_root / "logs" / "ci" / "active-tasks" / "task-14.active.json"
            active_task_path.parent.mkdir(parents=True, exist_ok=True)
            active_task_path.write_text(
                json.dumps(
                    {
                        "task_id": "14",
                        "run_id": "stale-run",
                        "status": "ok",
                        "recommended_action": "continue",
                        "recommended_action_why": "stale active task recommendation",
                        "paths": {
                            "latest_json": "logs/ci/2026-04-09/sc-review-pipeline-task-14/latest.json",
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            inspection = {
                "task_id": "14",
                "run_id": "run-14",
                "failure": {"code": "review-needs-fix"},
                "paths": {
                    "latest": "logs/ci/2026-04-10/sc-review-pipeline-task-14/latest.json",
                    "out_dir": "logs/ci/2026-04-10/sc-review-pipeline-task-14-run-14",
                    "summary": "logs/ci/2026-04-10/sc-review-pipeline-task-14-run-14/summary.json",
                },
                "latest_summary_signals": {
                    "reason": "from-inspection",
                    "run_type": "deterministic-only",
                    "reuse_mode": "inspection-reuse",
                    "diagnostics_keys": ["from_inspection"],
                },
                "chapter6_hints": {
                    "next_action": "continue",
                    "can_skip_6_7": False,
                    "can_go_to_6_8": False,
                    "blocked_by": "",
                    "rerun_forbidden": False,
                    "rerun_override_flag": "",
                },
            }
            with mock.patch.object(resume_task, "inspect_run_artifacts", return_value=(1, inspection)):
                _, payload = resume_task.build_resume_payload(
                    repo_root=repo_root,
                    task_id="14",
                    latest="",
                    run_id="",
                )

        self.assertEqual("pipeline-summary", payload["decision_basis"])
        self.assertEqual("pipeline-summary", payload["recommendation_source"])
        self.assertEqual("needs-fix-fast", payload["recommended_action"])
        self.assertEqual("repeat reviewer family", payload["recommended_action_why"])
        self.assertEqual(
            "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 14 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
            payload["recommended_command"],
        )
        self.assertEqual(
            ["py -3 scripts/sc/run_review_pipeline.py --task-id 14"],
            payload["forbidden_commands"],
        )
        self.assertEqual(
            "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 14 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
            payload["candidate_commands"]["needs_fix_fast"],
        )
        self.assertIn("pipeline_summary.recommended_action=needs-fix-fast", payload["blocking_signals"])

    def test_build_resume_payload_should_prefer_inspection_recommendation_fields_over_summary_reload(self) -> None:
        inspection = {
            "task_id": "14",
            "run_id": "run-14",
            "failure": {"code": "review-needs-fix"},
            "paths": {
                "latest": "logs/ci/2026-04-10/sc-review-pipeline-task-14/latest.json",
                "out_dir": "logs/ci/2026-04-10/sc-review-pipeline-task-14-run-14",
                "summary": "logs/ci/2026-04-10/sc-review-pipeline-task-14-run-14/summary.json",
            },
            "latest_summary_signals": {
                "reason": "rerun_blocked:repeat_review_needs_fix",
                "run_type": "full",
                "reuse_mode": "deterministic-only-reuse",
                "artifact_integrity_kind": "",
                "diagnostics_keys": ["rerun_guard"],
            },
            "chapter6_hints": {
                "next_action": "needs-fix-fast",
                "can_skip_6_7": True,
                "can_go_to_6_8": True,
                "blocked_by": "rerun_guard",
                "rerun_forbidden": True,
                "rerun_override_flag": "--allow-full-rerun",
            },
            "recommended_action": "needs-fix-fast",
            "recommended_action_why": "inspection already knows the recommendation",
            "candidate_commands": {
                "needs_fix_fast": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 14 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
                "rerun": "py -3 scripts/sc/run_review_pipeline.py --task-id 14",
            },
            "recommended_command": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 14 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
            "forbidden_commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 14"],
        }
        with tempfile.TemporaryDirectory() as tmp_dir, mock.patch.object(resume_task, "inspect_run_artifacts", return_value=(1, inspection)):
            _, payload = resume_task.build_resume_payload(
                repo_root=Path(tmp_dir),
                task_id="14",
                latest="",
                run_id="",
            )

        self.assertEqual("inspection", payload["decision_basis"])
        self.assertEqual("inspection", payload["recommendation_source"])
        self.assertEqual("needs-fix-fast", payload["recommended_action"])
        self.assertEqual("inspection already knows the recommendation", payload["recommended_action_why"])
        self.assertEqual(
            "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 14 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
            payload["recommended_command"],
        )
        self.assertEqual(
            ["py -3 scripts/sc/run_review_pipeline.py --task-id 14"],
            payload["forbidden_commands"],
        )
        self.assertIn("inspection.recommended_action=needs-fix-fast", payload["blocking_signals"])


    def test_render_markdown_should_surface_latest_reason_and_diagnostics_first(self) -> None:
        payload = {
            "task_id": "14",
            "run_id": "run-14",
            "recommended_action": "needs_fix_fast",
            "recommended_action_why": "Deterministic already passed; rerun only llm review.",
            "decision_basis": "active-task",
            "recommendation_source": "active-task",
            "recommendation_reason": "latest diagnostics say deterministic_ok_llm_not_clean",
            "blocking_signals": ["active_task.clean_state=deterministic_ok_llm_not_clean"],
            "candidate_commands": {
                "inspect": "py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id 14",
                "resume": "py -3 scripts/sc/run_review_pipeline.py --task-id 14 --resume",
                "fork": "py -3 scripts/sc/run_review_pipeline.py --task-id 14 --fork",
                "rerun": "py -3 scripts/sc/run_review_pipeline.py --task-id 14",
                "needs_fix_fast": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 14 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
            },
            "inspection": {
                "status": "fail",
                "failure": {"code": "review-needs-fix"},
                "paths": {
                    "latest": "logs/ci/2026-04-06/sc-review-pipeline-task-14/latest.json",
                    "out_dir": "logs/ci/2026-04-06/sc-review-pipeline-task-14-run-14",
                },
            },
            "recent_failure_summary": {
                "latest_failure_family": "step-failed:sc-test|sc-test|unit|2|compile_error",
                "same_family_count": 2,
                "stop_full_rerun_recommended": True,
            },
            "chapter6_hints": {
                "next_action": "needs-fix-fast",
                "can_skip_6_7": True,
                "can_go_to_6_8": True,
                "blocked_by": "rerun_guard",
                "rerun_forbidden": True,
                "rerun_override_flag": "--allow-full-rerun",
            },
            "latest_summary_signals": {
                "reason": "rerun_blocked:deterministic_green_llm_not_clean",
                "run_type": "deterministic-only",
                "reuse_mode": "deterministic-only-reuse",
                "artifact_integrity_kind": "planned_only_incomplete",
                "diagnostics_keys": [
                    "rerun_guard",
                    "reuse_decision",
                    "acceptance_preflight",
                    "llm_timeout_memory",
                ],
            },
            "related_execution_plans": [],
            "latest_execution_plan": "",
            "related_decision_logs": [],
            "latest_decision_log": "",
            "agent_review": {},
            "active_task": {},
        }

        text = resume_task._render_markdown(payload)

        self.assertIn("- Latest reason: rerun_blocked:deterministic_green_llm_not_clean", text)
        self.assertIn("- Latest run type: deterministic-only", text)
        self.assertIn("- Latest reuse mode: deterministic-only-reuse", text)
        self.assertIn("- Latest artifact integrity: planned_only_incomplete", text)
        self.assertIn("- Latest diagnostics keys: `rerun_guard`, `reuse_decision`, `acceptance_preflight`, `llm_timeout_memory`", text)
        self.assertIn("- Chapter6 rerun forbidden: yes", text)
        self.assertIn("- Chapter6 rerun override: --allow-full-rerun", text)
        self.assertIn("- Chapter6 stop-loss note: Deterministic evidence is already green; do not pay for another full 6.7. Continue with 6.8 or needs-fix-fast.", text)
        self.assertIn("- Recommended command: `py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 14 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1`", text)
        self.assertIn("- Forbidden commands: `py -3 scripts/sc/run_review_pipeline.py --task-id 14`", text)
        self.assertIn("- Recent same-family count: 2", text)
        self.assertIn("- Recent stop-full-rerun: yes", text)

    def test_render_markdown_should_include_approval_contract_fields(self) -> None:
        payload = {
            "task_id": "15",
            "run_id": "run-15",
            "recommended_action": "pause",
            "recommended_action_why": "Await fork approval before continuing recovery.",
            "decision_basis": "inspection",
            "recommendation_source": "inspection",
            "recommendation_reason": "Await fork approval before continuing recovery.",
            "blocking_signals": ["inspection.blocked_by=approval_pending"],
            "candidate_commands": {
                "inspect": "py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id 15",
                "resume": "py -3 scripts/sc/run_review_pipeline.py --task-id 15 --resume",
                "fork": "py -3 scripts/sc/run_review_pipeline.py --task-id 15 --fork",
                "rerun": "py -3 scripts/sc/run_review_pipeline.py --task-id 15",
                "needs_fix_fast": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 15 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
            },
            "inspection": {
                "status": "fail",
                "failure": {"code": "review-needs-fix"},
                "paths": {
                    "latest": "logs/ci/2026-04-10/sc-review-pipeline-task-15/latest.json",
                    "out_dir": "logs/ci/2026-04-10/sc-review-pipeline-task-15-run-15",
                },
            },
            "approval": {
                "required_action": "fork",
                "status": "pending",
                "decision": "",
                "recommended_action": "pause",
                "allowed_actions": ["inspect", "pause"],
                "blocked_actions": ["fork", "resume", "rerun"],
                "reason": "Await fork approval before continuing recovery.",
            },
            "recent_failure_summary": {},
            "chapter6_hints": {
                "next_action": "pause",
                "can_skip_6_7": False,
                "can_go_to_6_8": False,
                "blocked_by": "approval_pending",
                "rerun_forbidden": True,
                "rerun_override_flag": "",
            },
            "latest_summary_signals": {
                "reason": "review_pending",
                "run_type": "full",
                "reuse_mode": "none",
                "artifact_integrity_kind": "",
                "diagnostics_keys": [],
            },
            "related_execution_plans": [],
            "latest_execution_plan": "",
            "related_decision_logs": [],
            "latest_decision_log": "",
            "agent_review": {},
            "active_task": {},
            "recommended_command": "",
            "forbidden_commands": [
                "py -3 scripts/sc/run_review_pipeline.py --task-id 15 --resume",
                "py -3 scripts/sc/run_review_pipeline.py --task-id 15 --fork",
            ],
        }

        text = resume_task._render_markdown(payload)

        self.assertIn("- Approval required action: fork", text)
        self.assertIn("- Approval status: pending", text)
        self.assertIn("- Approval decision: n/a", text)
        self.assertIn("- Approval recommended action: pause", text)
        self.assertIn("- Approval allowed actions: inspect, pause", text)
        self.assertIn("- Approval blocked actions: fork, resume, rerun", text)
        self.assertIn("- Approval reason: Await fork approval before continuing recovery.", text)

    def test_build_resume_payload_should_append_recent_failure_signals(self) -> None:
        inspection = {
            "task_id": "14",
            "run_id": "run-14",
            "failure": {"code": "step-failed"},
            "paths": {
                "latest": "logs/ci/2026-04-06/sc-review-pipeline-task-14/latest.json",
                "out_dir": "logs/ci/2026-04-06/sc-review-pipeline-task-14-run-14",
            },
            "latest_summary_signals": {
                "reason": "step_failed:sc-test",
                "run_type": "deterministic-only",
                "reuse_mode": "none",
                "artifact_integrity_kind": "",
                "diagnostics_keys": [],
            },
            "recent_failure_summary": {
                "latest_failure_family": "step-failed:sc-test|sc-test|unit|2|compile_error",
                "same_family_count": 2,
                "stop_full_rerun_recommended": True,
            },
            "chapter6_hints": {
                "next_action": "inspect",
                "can_skip_6_7": False,
                "can_go_to_6_8": False,
                "blocked_by": "recent_failure_summary",
                "rerun_forbidden": True,
                "rerun_override_flag": "",
            },
        }
        with tempfile.TemporaryDirectory() as tmp_dir, mock.patch.object(resume_task, "inspect_run_artifacts", return_value=(1, inspection)):
            _, payload = resume_task.build_resume_payload(
                repo_root=Path(tmp_dir),
                task_id="14",
                latest="",
                run_id="",
            )

        self.assertIn("recent_failure.same_family_count=2", payload["blocking_signals"])
        self.assertIn("recent_failure.stop_full_rerun_recommended=true", payload["blocking_signals"])

    def test_chapter6_stop_loss_note_should_explain_llm_retry_stop_loss(self) -> None:
        text = resume_task._chapter6_stop_loss_note(
            {"blocked_by": "llm_retry_stop_loss"},
            {"reason": "step_failed:sc-llm-review"},
        )
        self.assertEqual(
            "This run already stopped after the first costly llm timeout; continue with the narrow llm-only closure path instead of reopening deterministic steps.",
            text,
        )

    def test_chapter6_stop_loss_note_should_explain_sc_test_retry_stop_loss(self) -> None:
        text = resume_task._chapter6_stop_loss_note(
            {"blocked_by": "sc_test_retry_stop_loss"},
            {"reason": "step_failed:sc-test"},
        )
        self.assertEqual(
            "The pipeline already proved the unit root cause and stopped the same-run retry; fix the unit issue first, then start a fresh run.",
            text,
        )

    def test_chapter6_stop_loss_note_should_explain_waste_signals(self) -> None:
        text = resume_task._chapter6_stop_loss_note(
            {"blocked_by": "waste_signals"},
            {"reason": "step_failed:sc-test"},
        )
        self.assertEqual(
            "Unit failure was already known before more expensive engine-lane work continued; fix the unit/root cause before paying that cost again.",
            text,
        )

    def test_chapter6_stop_loss_note_should_explain_dirty_worktree_ceiling(self) -> None:
        text = resume_task._chapter6_stop_loss_note(
            {"blocked_by": "rerun_guard"},
            {"reason": "rerun_blocked:dirty_worktree_unsafe_paths_ceiling"},
        )
        self.assertEqual(
            "Current changes exceed the standard Chapter 6 safe scope; shrink the dirty worktree or inspect/reset the drift before paying for another full 6.7.",
            text,
        )

    def test_chapter6_stop_loss_note_should_explain_recent_failure_summary(self) -> None:
        text = resume_task._chapter6_stop_loss_note(
            {"blocked_by": "recent_failure_summary"},
            {"reason": "step_failed:sc-test"},
        )
        self.assertEqual(
            "Recent runs already repeat the same failure family; inspect the repeated fingerprint and fix the root cause before rerunning 6.7.",
            text,
        )

    def test_chapter6_stop_loss_note_should_explain_planned_only_artifact_integrity(self) -> None:
        text = resume_task._chapter6_stop_loss_note(
            {"blocked_by": "artifact_integrity"},
            {"reason": "planned_only_incomplete"},
        )
        self.assertEqual(
            "The latest bundle is a planned-only terminal run, not a real completed producer run; inspect it only for evidence and start a fresh real run before reopening Chapter 6.",
            text,
        )

    def test_build_resume_payload_should_not_force_active_task_latest_or_run_id_into_inspection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            active_task_path = repo_root / "logs" / "ci" / "active-tasks" / "task-14.active.json"
            active_task_path.parent.mkdir(parents=True, exist_ok=True)
            active_task_path.write_text(
                json.dumps(
                    {
                        "task_id": "14",
                        "run_id": "stale-run",
                        "paths": {
                            "latest_json": "logs/ci/2026-04-07/sc-review-pipeline-task-14/latest.json",
                        },
                    }
                ),
                encoding="utf-8",
            )
            calls: list[dict[str, str]] = []

            def _fake_inspect_run_artifacts(*, repo_root: Path, latest: str, kind: str, task_id: str, run_id: str):
                calls.append(
                    {
                        "latest": latest,
                        "kind": kind,
                        "task_id": task_id,
                        "run_id": run_id,
                    }
                )
                return (
                    0,
                    {
                        "task_id": "14",
                        "run_id": "fresh-run",
                        "failure": {"code": "ok"},
                        "paths": {
                            "latest": "logs/ci/2026-04-06/sc-review-pipeline-task-14/latest.json",
                            "out_dir": "logs/ci/2026-04-06/sc-review-pipeline-task-14-fresh-run",
                        },
                        "latest_summary_signals": {
                            "reason": "pipeline_clean",
                            "reuse_mode": "none",
                            "diagnostics_keys": [],
                        },
                        "chapter6_hints": {
                            "next_action": "continue",
                            "can_skip_6_7": True,
                            "can_go_to_6_8": False,
                            "blocked_by": "",
                            "rerun_forbidden": False,
                            "rerun_override_flag": "",
                        },
                    },
                )

            with mock.patch.object(resume_task, "inspect_run_artifacts", side_effect=_fake_inspect_run_artifacts):
                _, payload = resume_task.build_resume_payload(
                    repo_root=repo_root,
                    task_id="14",
                    latest="",
                    run_id="",
                )

        self.assertEqual(
            [{"latest": "", "kind": "pipeline", "task_id": "14", "run_id": ""}],
            calls,
        )
        self.assertEqual("fresh-run", payload["run_id"])
        self.assertEqual("logs/ci/2026-04-06/sc-review-pipeline-task-14/latest.json", payload["inspection"]["paths"]["latest"])
        self.assertEqual(
            "logs/ci/2026-04-06/sc-review-pipeline-task-14/latest.json",
            payload["active_task"]["latest_json"],
        )
        self.assertEqual(
            "logs/ci/2026-04-07/sc-review-pipeline-task-14/latest.json",
            payload["active_task"]["reported_latest_json"],
        )
        self.assertTrue(payload["active_task"]["latest_json_mismatch"])

    def test_render_markdown_should_surface_active_task_reported_latest_when_it_differs(self) -> None:
        payload = {
            "task_id": "14",
            "run_id": "fresh-run",
            "recommended_action": "none",
            "recommended_action_why": "Inspection reported status=ok.",
            "decision_basis": "inspection",
            "recommendation_source": "inspection",
            "recommendation_reason": "Inspection reported status=ok.",
            "blocking_signals": [],
            "candidate_commands": {},
            "inspection": {
                "status": "ok",
                "failure": {"code": "ok"},
                "paths": {
                    "latest": "logs/ci/2026-04-06/sc-review-pipeline-task-14/latest.json",
                    "out_dir": "logs/ci/2026-04-06/sc-review-pipeline-task-14-fresh-run",
                },
            },
            "latest_summary_signals": {"reason": "pipeline_clean", "reuse_mode": "none", "diagnostics_keys": []},
            "chapter6_hints": {
                "next_action": "continue",
                "can_skip_6_7": True,
                "can_go_to_6_8": False,
                "blocked_by": "",
                "rerun_forbidden": False,
                "rerun_override_flag": "",
            },
            "related_execution_plans": [],
            "latest_execution_plan": "",
            "related_decision_logs": [],
            "latest_decision_log": "",
            "agent_review": {},
            "active_task": {
                "path": "logs/ci/active-tasks/task-14.active.json",
                "status": "ok",
                "recommended_action": "continue",
                "recommended_action_why": "Pipeline is green.",
                "latest_json": "logs/ci/2026-04-06/sc-review-pipeline-task-14/latest.json",
                "reported_latest_json": "logs/ci/2026-04-07/sc-review-pipeline-task-14/latest.json",
                "latest_json_mismatch": True,
            },
        }

        text = resume_task._render_markdown(payload)

        self.assertIn("- Active task latest pointer: `logs/ci/2026-04-06/sc-review-pipeline-task-14/latest.json`", text)
        self.assertIn(
            "- Active task reported latest pointer: `logs/ci/2026-04-07/sc-review-pipeline-task-14/latest.json`",
            text,
        )

    def test_repair_active_task_latest_pointer_should_update_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            active_json = repo_root / "logs" / "ci" / "active-tasks" / "task-14.active.json"
            active_md = repo_root / "logs" / "ci" / "active-tasks" / "task-14.active.md"
            active_json.parent.mkdir(parents=True, exist_ok=True)
            active_json.write_text(
                json.dumps(
                    {
                        "task_id": "14",
                        "paths": {
                            "latest_json": "logs/ci/2026-04-07/sc-review-pipeline-task-14/latest.json",
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            active_md.write_text(
                "# Active Task Summary\n\n"
                "- Task id: `14`\n"
                "- Latest pointer: `logs/ci/2026-04-07/sc-review-pipeline-task-14/latest.json`\n",
                encoding="utf-8",
            )

            repair = resume_task._repair_active_task_latest_pointer(
                repo_root,
                task_id="14",
                resolved_latest="logs/ci/2026-04-06/sc-review-pipeline-task-14/latest.json",
            )

            repaired_json = json.loads(active_json.read_text(encoding="utf-8"))
            repaired_md = active_md.read_text(encoding="utf-8")

        self.assertTrue(repair["repaired"])
        self.assertEqual(
            "logs/ci/2026-04-07/sc-review-pipeline-task-14/latest.json",
            repair["reported_latest_json"],
        )
        self.assertEqual(
            "logs/ci/2026-04-06/sc-review-pipeline-task-14/latest.json",
            repaired_json["paths"]["latest_json"],
        )
        self.assertIn(
            "- Latest pointer: `logs/ci/2026-04-06/sc-review-pipeline-task-14/latest.json`",
            repaired_md,
        )

    def test_render_recommendation_only_should_surface_core_recovery_fields(self) -> None:
        payload = {
            "task_id": "15",
            "run_id": "run-15",
            "recommended_action": "needs-fix-fast",
            "recommended_command": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 15 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
            "forbidden_commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 15"],
            "latest_summary_signals": {
                "reason": "rerun_blocked:repeat_review_needs_fix",
            },
            "chapter6_hints": {
                "next_action": "needs-fix-fast",
                "blocked_by": "rerun_guard",
            },
            "approval": {
                "status": "pending",
                "recommended_action": "pause",
                "allowed_actions": ["inspect", "pause"],
                "blocked_actions": ["fork", "resume", "rerun"],
            },
            "run_event_summary": {
                "latest_turn_id": "run-15:turn-2",
                "turn_count": 2,
            },
        }

        text = resume_task._render_recommendation_only(payload)

        self.assertIn("task_id=15", text)
        self.assertIn("run_id=run-15", text)
        self.assertIn("recommended_action=needs-fix-fast", text)
        self.assertIn(
            "recommended_command=py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 15 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
            text,
        )
        self.assertIn("forbidden_commands=py -3 scripts/sc/run_review_pipeline.py --task-id 15", text)
        self.assertIn("latest_reason=rerun_blocked:repeat_review_needs_fix", text)
        self.assertIn("chapter6_next_action=needs-fix-fast", text)
        self.assertIn("blocked_by=rerun_guard", text)
        self.assertIn("approval_status=pending", text)
        self.assertIn("approval_recommended_action=pause", text)
        self.assertIn("approval_allowed_actions=inspect | pause", text)
        self.assertIn("approval_blocked_actions=fork | resume | rerun", text)
        self.assertIn("latest_turn=run-15:turn-2", text)
        self.assertIn("turn_count=2", text)

    def test_main_recommendation_only_should_print_compact_text_without_default_outputs(self) -> None:
        payload = {
            "task_id": "15",
            "run_id": "run-15",
            "recommended_action": "needs-fix-fast",
            "recommended_command": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 15 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
            "forbidden_commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 15"],
            "inspection": {
                "paths": {
                    "latest": "logs/ci/2026-04-10/sc-review-pipeline-task-15/latest.json",
                }
            },
            "latest_summary_signals": {
                "reason": "rerun_blocked:repeat_review_needs_fix",
            },
            "chapter6_hints": {
                "next_action": "needs-fix-fast",
                "blocked_by": "rerun_guard",
            },
            "approval": {
                "status": "pending",
                "recommended_action": "pause",
                "allowed_actions": ["inspect", "pause"],
                "blocked_actions": ["fork", "resume", "rerun"],
            },
            "run_event_summary": {
                "latest_turn_id": "run-15:turn-2",
                "turn_count": 2,
            },
            "active_task": {},
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            stdout = io.StringIO()
            with (
                mock.patch.object(resume_task, "build_resume_payload", return_value=(1, payload)),
                mock.patch.object(resume_task, "_repair_active_task_latest_pointer", return_value={"repaired": False}),
                redirect_stdout(stdout),
            ):
                rc = resume_task.main(
                    [
                        "--repo-root",
                        str(repo_root),
                        "--task-id",
                        "15",
                        "--recommendation-only",
                    ]
                )

            default_json, default_md = resume_task._default_output_paths(repo_root, "15")

        self.assertEqual(0, rc)
        output = stdout.getvalue()
        self.assertIn("task_id=15", output)
        self.assertIn("recommended_action=needs-fix-fast", output)
        self.assertIn("approval_recommended_action=pause", output)
        self.assertIn("latest_turn=run-15:turn-2", output)
        self.assertFalse(default_json.exists())
        self.assertFalse(default_md.exists())

    def test_main_recommendation_only_json_should_print_compact_json_without_default_outputs(self) -> None:
        payload = {
            "task_id": "15",
            "run_id": "run-15",
            "recommended_action": "needs-fix-fast",
            "recommended_command": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 15 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
            "forbidden_commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 15"],
            "inspection": {
                "paths": {
                    "latest": "logs/ci/2026-04-10/sc-review-pipeline-task-15/latest.json",
                }
            },
            "latest_summary_signals": {
                "reason": "rerun_blocked:repeat_review_needs_fix",
            },
            "chapter6_hints": {
                "next_action": "needs-fix-fast",
                "blocked_by": "rerun_guard",
            },
            "approval": {
                "status": "pending",
                "recommended_action": "pause",
                "allowed_actions": ["inspect", "pause"],
                "blocked_actions": ["fork", "resume", "rerun"],
            },
            "run_event_summary": {
                "latest_turn_id": "run-15:turn-2",
                "turn_count": 2,
            },
            "active_task": {},
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            stdout = io.StringIO()
            with (
                mock.patch.object(resume_task, "build_resume_payload", return_value=(1, payload)),
                mock.patch.object(resume_task, "_repair_active_task_latest_pointer", return_value={"repaired": False}),
                redirect_stdout(stdout),
            ):
                rc = resume_task.main(
                    [
                        "--repo-root",
                        str(repo_root),
                        "--task-id",
                        "15",
                        "--recommendation-only",
                        "--recommendation-format",
                        "json",
                    ]
                )

            default_json, default_md = resume_task._default_output_paths(repo_root, "15")

        self.assertEqual(0, rc)
        compact = json.loads(stdout.getvalue())
        self.assertEqual("15", compact["task_id"])
        self.assertEqual("needs-fix-fast", compact["recommended_action"])
        self.assertEqual("rerun_blocked:repeat_review_needs_fix", compact["latest_reason"])
        self.assertEqual("pause", compact["approval_recommended_action"])
        self.assertEqual("run-15:turn-2", compact["latest_turn"])
        self.assertFalse(default_json.exists())
        self.assertFalse(default_md.exists())


if __name__ == "__main__":
    unittest.main()
