#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
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


project_health = _load_module("project_health_support_test_module", "scripts/python/_project_health_support.py")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class ProjectHealthSupportTests(unittest.TestCase):
    def test_detect_project_stage_should_flag_examples_only_triplet(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write(root / "project.godot", "[application]\nconfig/name=\"Demo\"\n")
            _write(root / "README.md", "# Demo\n")
            _write(root / "AGENTS.md", "# Demo\n")
            _write(root / "examples" / "taskmaster" / "tasks.json", "{}\n")
            _write(root / "examples" / "taskmaster" / "tasks_back.json", "{}\n")
            _write(root / "examples" / "taskmaster" / "tasks_gameplay.json", "{}\n")

            payload = project_health.detect_project_stage(root)

            self.assertEqual("triplet-missing", payload["stage"])
            self.assertEqual("warn", payload["status"])
            self.assertFalse(payload["signals"]["real_task_triplet"])
            self.assertTrue(payload["signals"]["example_task_triplet"])

    def test_doctor_project_should_report_missing_real_triplet_as_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write(root / "project.godot", "[application]\nconfig/name=\"Demo\"\n")
            _write(root / "README.md", "# Demo\n")
            _write(root / "AGENTS.md", "# Demo\n")
            _write(root / "Game.sln", "Microsoft Visual Studio Solution File, Format Version 12.00\n")
            _write(root / "Game.Core.Tests" / "Game.Core.Tests.csproj", "<Project />\n")
            _write(root / "workflow.md", "# Workflow\n")
            _write(root / "DELIVERY_PROFILE.md", "# Delivery\n")
            _write(root / "examples" / "taskmaster" / "tasks.json", "{}\n")
            _write(root / "examples" / "taskmaster" / "tasks_back.json", "{}\n")
            _write(root / "examples" / "taskmaster" / "tasks_gameplay.json", "{}\n")

            payload = project_health.doctor_project(root)

            self.assertEqual("warn", payload["status"])
            checks = {item["id"]: item for item in payload["checks"]}
            self.assertEqual("warn", checks["task-triplet-real"]["status"])
            self.assertEqual("ok", checks["task-triplet-example"]["status"])
            self.assertIn("create", checks["task-triplet-real"]["recommendation"])

    def test_doctor_project_should_accept_repo_named_solution(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write(root / "project.godot", "[application]\nconfig/name=\"Demo\"\n")
            _write(root / "README.md", "# Demo\n")
            _write(root / "AGENTS.md", "# Demo\n")
            _write(root / f"{root.name}.sln", "Microsoft Visual Studio Solution File, Format Version 12.00\n")
            _write(root / "Game.Core.Tests" / "Game.Core.Tests.csproj", "<Project />\n")
            _write(root / "workflow.md", "# Workflow\n")
            _write(root / "DELIVERY_PROFILE.md", "# Delivery\n")

            payload = project_health.doctor_project(root)

            checks = {item["id"]: item for item in payload["checks"]}
            self.assertEqual("ok", checks["solution"]["status"])
            self.assertEqual(f"{root.name}.sln", checks["solution"]["path"])

    def test_check_directory_boundaries_should_detect_core_and_base_violations(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write(root / "Game.Core" / "Foo.cs", "using Godot;\npublic sealed class Foo {}\n")
            _write(root / "Game.Core" / "Contracts" / "Bar.cs", "public sealed class Bar { public Godot.Node? Node { get; set; } }\n")
            _write(root / "docs" / "architecture" / "base" / "01-introduction.md", "This file leaked PRD-demo.\n")

            payload = project_health.check_directory_boundaries(root)

            self.assertEqual("fail", payload["status"])
            violations = {item["rule_id"]: item for item in payload["violations"]}
            self.assertIn("game-core-no-godot", violations)
            self.assertIn("contracts-no-godot", violations)
            self.assertIn("base-docs-no-prd-leak", violations)

    def test_write_project_health_record_should_refresh_dashboard_and_latest_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write(
                root / "logs" / "ci" / "2026-03-29" / "single-task-light-lane-v2-batch" / "summary.json",
                json.dumps(
                    {
                        "cmd": "run_single_task_light_lane_batch",
                        "status": "fail",
                        "covered_count": 8,
                        "failed_count": 6,
                        "extract_family_recommended_actions": [
                            {
                                "family": "stdout:sc_llm_obligations_status_fail",
                                "count": 5,
                                "task_ids": [67, 68, 69],
                                "recommended_action": "repair_obligations_or_task_context_before_downstream",
                                "downstream_policy_hint": "skip-all",
                                "reason": "extract already reported obligations failure",
                            }
                        ],
                        "family_hotspots": [
                            {
                                "family": "stdout:sc_llm_obligations_status_fail",
                                "task_id_start": 67,
                                "task_id_end": 72,
                                "count": 6,
                            }
                        ],
                        "quarantine_ranges": [
                            {
                                "family": "stdout:sc_llm_obligations_status_fail",
                                "task_id_start": 67,
                                "task_id_end": 72,
                                "reason": "family_streak>=5",
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
            )
            _write(
                root / "logs" / "ci" / "active-tasks" / "task-14.active.json",
                json.dumps(
                    {
                        "cmd": "active-task-sidecar",
                        "task_id": "14",
                        "run_id": "run-a",
                        "status": "ok",
                        "updated_at_utc": "2026-04-06T09:18:04+00:00",
                        "recommended_action": "needs-fix-fast",
                        "recommended_action_why": "Deterministic steps are green but llm_review is not clean.",
                        "latest_summary_signals": {
                            "reason": "rerun_blocked:deterministic_green_llm_not_clean",
                            "run_type": "deterministic-only",
                            "artifact_integrity_kind": "planned_only_incomplete",
                            "reuse_mode": "deterministic-only-reuse",
                            "diagnostics_keys": ["rerun_guard", "reuse_decision", "llm_timeout_memory"],
                        },
                        "chapter6_hints": {
                            "next_action": "needs-fix-fast",
                            "can_skip_6_7": True,
                            "can_go_to_6_8": True,
                            "blocked_by": "rerun_guard",
                            "rerun_forbidden": True,
                            "rerun_override_flag": "--allow-full-rerun",
                        },
                        "clean_state": {
                            "state": "deterministic_ok_llm_not_clean",
                            "deterministic_ok": True,
                            "llm_status": "fail",
                            "needs_fix_agents": [],
                            "unknown_agents": ["code-reviewer"],
                            "timeout_agents": ["code-reviewer"],
                        },
                        "paths": {
                            "latest_json": "logs/ci/2026-04-06/sc-review-pipeline-task-14/latest.json",
                            "summary_json": "logs/ci/2026-04-06/sc-review-pipeline-task-14-run-a/summary.json",
                        },
                        "reported_latest_json": "logs/ci/2026-04-07/sc-review-pipeline-task-14/latest.json",
                        "latest_json_mismatch": False,
                        "latest_json_repaired": True,
                        "diagnostics": {
                            "profile_drift": {
                                "previous_delivery_profile": "standard",
                                "previous_security_profile": "strict",
                                "current_delivery_profile": "fast-ship",
                                "current_security_profile": "host-safe",
                            },
                            "waste_signals": {
                                "unit_failed_but_engine_lane_ran": True,
                            },
                            "rerun_guard": {
                                "kind": "deterministic_green_llm_not_clean",
                                "blocked": True,
                                "recommended_path": "llm-only",
                            },
                            "reuse_decision": {
                                "mode": "deterministic-only-reuse",
                                "blocked": False,
                            },
                            "llm_timeout_memory": {
                                "overrides": {
                                    "code-reviewer": 480,
                                },
                            },
                            "llm_retry_stop_loss": {
                                "blocked": True,
                                "step_name": "sc-llm-review",
                                "kind": "deterministic_green_llm_not_clean",
                            },
                            "sc_test_retry_stop_loss": {
                                "blocked": True,
                                "step_name": "sc-test",
                                "kind": "same_run_retry_waste",
                            },
                            "artifact_integrity": {
                                "blocked": True,
                                "kind": "artifact_incomplete",
                            },
                            "recent_failure_summary": {
                                "latest_failure_family": "step-failed:sc-test",
                                "same_family_count": 3,
                                "stop_full_rerun_recommended": True,
                            },
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
            )
            _write(
                root / "logs" / "ci" / "active-tasks" / "task-88.active.json",
                json.dumps(
                    {
                        "cmd": "active-task-sidecar",
                        "task_id": "88",
                        "run_id": "run-stale",
                        "status": "ok",
                        "updated_at_utc": "2026-03-30T09:18:04+00:00",
                        "recommended_action": "continue",
                        "recommended_action_why": "Already clean.",
                        "clean_state": {
                            "state": "clean",
                            "deterministic_ok": True,
                            "llm_status": "ok",
                        },
                        "chapter6_hints": {
                            "next_action": "continue",
                            "can_skip_6_7": True,
                            "can_go_to_6_8": False,
                            "blocked_by": "",
                            "rerun_forbidden": False,
                            "rerun_override_flag": "",
                        },
                        "paths": {
                            "latest_json": "logs/ci/2026-03-30/sc-review-pipeline-task-88/latest.json",
                            "summary_json": "logs/ci/2026-03-30/sc-review-pipeline-task-88-run-stale/summary.json",
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
            )
            _write(
                root / "logs" / "ci" / "active-tasks" / "task-89.active.json",
                json.dumps(
                    {
                        "cmd": "active-task-sidecar",
                        "task_id": "89",
                        "run_id": "run-weird",
                        "status": "ok",
                        "updated_at_utc": "2026-04-06T09:18:04+00:00",
                        "recommended_action": "continue",
                        "recommended_action_why": "Weird pointer.",
                        "clean_state": {
                            "state": "clean",
                            "deterministic_ok": True,
                            "llm_status": "ok",
                        },
                        "chapter6_hints": {
                            "next_action": "continue",
                            "can_skip_6_7": True,
                            "can_go_to_6_8": False,
                            "blocked_by": "",
                            "rerun_forbidden": False,
                            "rerun_override_flag": "",
                        },
                        "paths": {
                            "latest_json": "logs/ci/2026-04-07/repro-preflight-schema2-latest.json",
                            "summary_json": "logs/ci/2026-04-07/sc-review-pipeline-task-89-run-weird/summary.json",
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
            )
            _write(
                root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-14-run-a" / "summary.json",
                json.dumps(
                    {
                        "cmd": "sc-review-pipeline",
                        "status": "fail",
                        "reuse_mode": "deterministic-only-reuse",
                        "steps": [
                            {
                                "name": "sc-test",
                                "status": "ok",
                                "summary_file": str(root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-14-run-a" / "child-artifacts" / "sc-test" / "summary.json"),
                                "reported_out_dir": str(root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-14-run-a" / "child-artifacts" / "sc-test"),
                            },
                            {
                                "name": "sc-acceptance-check",
                                "status": "ok",
                                "summary_file": str(root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-14-run-a" / "child-artifacts" / "sc-acceptance-check" / "summary.json"),
                                "reported_out_dir": str(root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-14-run-a" / "child-artifacts" / "sc-acceptance-check"),
                            },
                            {
                                "name": "sc-llm-review",
                                "status": "fail",
                                "summary_file": str(root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-14-run-a" / "child-artifacts" / "sc-llm-review" / "summary.json"),
                            },
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
            )
            _write(
                root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-14" / "latest.json",
                json.dumps(
                    {
                        "task_id": "14",
                        "run_id": "run-a",
                        "status": "fail",
                        "date": "2026-04-06",
                        "latest_out_dir": str(root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-14-run-a"),
                        "summary_path": str(root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-14-run-a" / "summary.json"),
                        "execution_context_path": str(root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-14-run-a" / "execution-context.json"),
                        "repair_guide_json_path": str(root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-14-run-a" / "repair-guide.json"),
                        "repair_guide_md_path": str(root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-14-run-a" / "repair-guide.md"),
                        "marathon_state_path": str(root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-14-run-a" / "marathon-state.json"),
                        "run_events_path": str(root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-14-run-a" / "run-events.jsonl"),
                        "harness_capabilities_path": str(root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-14-run-a" / "harness-capabilities.json"),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
            )
            _write(root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-14-run-a" / "child-artifacts" / "sc-test" / "summary.json", json.dumps({"cmd": "sc-test", "status": "ok"}, ensure_ascii=False, indent=2) + "\n")
            _write(root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-14-run-a" / "child-artifacts" / "sc-acceptance-check" / "summary.json", json.dumps({"cmd": "sc-acceptance-check", "status": "ok"}, ensure_ascii=False, indent=2) + "\n")
            _write(root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-14-run-a" / "child-artifacts" / "sc-llm-review" / "summary.json", json.dumps({"status": "fail", "results": []}, ensure_ascii=False, indent=2) + "\n")
            project_health.write_project_health_record(
                root=root,
                kind="detect-project-stage",
                payload={"kind": "detect-project-stage", "status": "warn", "summary": "triplet missing"},
            )
            project_health.write_project_health_record(
                root=root,
                kind="doctor-project",
                payload={"kind": "doctor-project", "status": "ok", "summary": "doctor ok"},
            )
            project_health.write_project_health_record(
                root=root,
                kind="check-directory-boundaries",
                payload={"kind": "check-directory-boundaries", "status": "fail", "summary": "boundary fail"},
            )

            latest_index = json.loads(
                (root / "logs" / "ci" / "project-health" / "latest.json").read_text(encoding="utf-8")
            )
            latest_html = (root / "logs" / "ci" / "project-health" / "latest.html").read_text(encoding="utf-8")
            report_catalog = json.loads(
                (root / "logs" / "ci" / "project-health" / "report-catalog.latest.json").read_text(encoding="utf-8")
            )

            self.assertEqual(3, len(latest_index["records"]))
            self.assertIn("report_catalog_summary", latest_index)
            self.assertIn("active_task_summary", latest_index)
            self.assertEqual(1, latest_index["active_task_summary"]["total"])
            self.assertEqual(report_catalog["total_json"], latest_index["report_catalog_summary"]["total_json"])
            self.assertEqual(1, latest_index["active_task_summary"]["llm_retry_stop_loss_blocked"])
            self.assertEqual(1, latest_index["active_task_summary"]["sc_test_retry_stop_loss_blocked"])
            self.assertEqual(1, latest_index["active_task_summary"]["artifact_integrity_blocked"])
            self.assertEqual(1, latest_index["active_task_summary"]["recent_failure_summary_blocked"])
            self.assertEqual(1, latest_index["active_task_summary"]["artifact_integrity_planned_only_incomplete"])
            self.assertEqual(0, latest_index["active_task_summary"]["latest_json_mismatch"])
            self.assertEqual(1, latest_index["active_task_summary"]["latest_json_repaired"])
            self.assertEqual(1, latest_index["active_task_summary"]["rerun_guard_blocked"])
            self.assertEqual(1, latest_index["active_task_summary"]["rerun_forbidden"])
            self.assertEqual(1, latest_index["active_task_summary"]["deterministic_bundle_available"])
            self.assertEqual(1, latest_index["active_task_summary"]["run_type_deterministic_only"])
            self.assertEqual(1, latest_index["active_task_summary"]["next_action_needs_fix_fast"])
            self.assertIn("triplet missing", latest_html)
            self.assertIn("doctor ok", latest_html)
            self.assertIn("boundary fail", latest_html)
            self.assertIn("批量任务诊断摘录", latest_html)
            self.assertIn("Active task clean state", latest_html)
            self.assertIn("deterministic_ok_llm_not_clean", latest_html)
            self.assertIn("needs-fix-fast", latest_html)
            self.assertIn("repair_obligations_or_task_context_before_downstream", latest_html)
            self.assertIn("stdout:sc_llm_obligations_status_fail", latest_html)
            self.assertIn("family_streak&gt;=5", latest_html)
            self.assertIn("profile_drift", latest_html)
            self.assertIn("unit_failed_but_engine_lane_ran", latest_html)
            self.assertIn("rerun_guard", latest_html)
            self.assertIn("reuse_decision", latest_html)
            self.assertIn("llm_timeout_memory", latest_html)
            self.assertIn("llm_retry_stop_loss", latest_html)
            self.assertIn("sc_test_retry_stop_loss", latest_html)
            self.assertIn("artifact_integrity", latest_html)
            self.assertIn("artifact_integrity_planned_only_incomplete", latest_html)
            self.assertIn("latest_json_mismatch", latest_html)
            self.assertIn("latest_json_repaired", latest_html)
            self.assertIn("llm_retry_stop_loss: blocked=true step_name=sc-llm-review kind=deterministic_green_llm_not_clean", latest_html)
            self.assertIn("sc_test_retry_stop_loss: blocked=true step_name=sc-test kind=same_run_retry_waste", latest_html)
            self.assertIn("recent_failure_summary: family=step-failed:sc-test same_family_count=3 stop_full_rerun_recommended=True", latest_html)
            self.assertIn("latest_reason", latest_html)
            self.assertIn("latest_run_type", latest_html)
            self.assertIn("latest_artifact_integrity", latest_html)
            self.assertIn("latest_artifact_integrity: planned_only_incomplete", latest_html)
            self.assertIn("planned_only_terminal_bundle", latest_html)
            self.assertIn("rerun_blocked:deterministic_green_llm_not_clean", latest_html)
            self.assertIn("deterministic-only", latest_html)
            self.assertIn("chapter6_next_action", latest_html)
            self.assertIn("chapter6_can_go_to_6_8", latest_html)
            self.assertIn("chapter6_rerun_forbidden", latest_html)
            self.assertIn("chapter6_rerun_override", latest_html)
            self.assertIn("latest_json_repaired: true", latest_html)
            self.assertIn("reported_latest_json: logs/ci/2026-04-07/sc-review-pipeline-task-14/latest.json", latest_html)
            self.assertIn(
                "chapter6_stop_loss_note: Deterministic evidence is already green; do not pay for another full 6.7. Continue with 6.8 or needs-fix-fast.",
                latest_html,
            )
            self.assertIn("deterministic_bundle", latest_html)
            self.assertIn("recommended_action_why", latest_html)
            self.assertIn("llm_retry_stop_loss_blocked", latest_html)
            self.assertIn("sc_test_retry_stop_loss_blocked", latest_html)
            self.assertIn("artifact_integrity_blocked", latest_html)
            self.assertIn("recent_failure_summary_blocked", latest_html)
            self.assertIn("run_type_deterministic_only", latest_html)
            self.assertNotIn("Task 88", latest_html)
            self.assertNotIn("Task 89", latest_html)
            self.assertIn("Auto-refresh is disabled", latest_html)
            self.assertNotIn('meta http-equiv="refresh"', latest_html.lower())

    def test_write_project_health_record_should_honor_active_task_limit_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for task_id in ("11", "12", "13"):
                _write(
                    root / "logs" / "ci" / "active-tasks" / f"task-{task_id}.active.json",
                    json.dumps(
                        {
                            "cmd": "active-task-sidecar",
                            "task_id": task_id,
                            "run_id": f"run-{task_id}",
                            "status": "fail",
                            "updated_at_utc": "2026-04-08T09:18:04+00:00",
                            "recommended_action": "inspect",
                            "recommended_action_why": "Needs attention.",
                            "clean_state": {
                                "state": "not_clean",
                                "deterministic_ok": False,
                                "llm_status": "fail",
                            },
                            "chapter6_hints": {
                                "next_action": "inspect",
                                "can_skip_6_7": False,
                                "can_go_to_6_8": False,
                                "blocked_by": "",
                                "rerun_forbidden": False,
                                "rerun_override_flag": "",
                            },
                            "paths": {
                                "latest_json": f"logs/ci/2026-04-08/sc-review-pipeline-task-{task_id}/latest.json",
                                "summary_json": f"logs/ci/2026-04-08/sc-review-pipeline-task-{task_id}-run-{task_id}/summary.json",
                            },
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                )
                _write(
                    root / "logs" / "ci" / "2026-04-08" / f"sc-review-pipeline-task-{task_id}" / "latest.json",
                    json.dumps({"task_id": task_id, "run_id": f"run-{task_id}"}, ensure_ascii=False, indent=2) + "\n",
                )

            with mock.patch.dict(
                os.environ,
                {
                    "PROJECT_HEALTH_ACTIVE_TASK_LIMIT": "2",
                    "PROJECT_HEALTH_ACTIVE_TASK_TOP_RECORDS": "1",
                },
                clear=False,
            ):
                project_health.write_project_health_record(
                    root=root,
                    kind="detect-project-stage",
                    payload={"kind": "detect-project-stage", "status": "ok", "summary": "stage ok"},
                )

            latest_index = json.loads((root / "logs" / "ci" / "project-health" / "latest.json").read_text(encoding="utf-8"))
            self.assertEqual(2, latest_index["active_task_summary"]["total"])
            self.assertEqual(1, len(latest_index["active_task_summary"]["top_records"]))


if __name__ == "__main__":
    unittest.main()
