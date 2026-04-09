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


resume_task = _load_module("resume_task_module", "scripts/python/resume_task.py")


class ResumeTaskTests(unittest.TestCase):
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
                "inspect": "py -3 scripts/python/inspect_run.py --kind pipeline --task-id 14",
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
        self.assertIn("- Recent same-family count: 2", text)
        self.assertIn("- Recent stop-full-rerun: yes", text)

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


if __name__ == "__main__":
    unittest.main()
