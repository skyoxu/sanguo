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
project_health_schema = _load_module("project_health_schema_test_module", "scripts/python/_project_health_schema.py")
project_health_common = _load_module("project_health_common_test_module", "scripts/python/_project_health_common.py")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class ProjectHealthSupportTests(unittest.TestCase):
    def _detect_record_payload(self, *, status: str = "ok", summary: str = "stage ok", stage: str = "daily-task-loop-ready") -> dict[str, object]:
        return {
            "kind": "detect-project-stage",
            "status": status,
            "stage": stage,
            "summary": summary,
            "exit_code": 1 if status == "fail" else 0,
            "signals": {
                "project_godot": True,
                "readme": True,
                "agents": True,
                "real_task_triplet": True,
                "example_task_triplet": True,
                "overlay_indexes": 1,
                "contract_files": 1,
                "unit_test_files": 1,
            },
            "paths": {
                "real_task_triplet": {
                    "tasks.json": ".taskmaster/tasks/tasks.json",
                    "tasks_back.json": ".taskmaster/tasks/tasks_back.json",
                    "tasks_gameplay.json": ".taskmaster/tasks/tasks_gameplay.json",
                },
                "example_task_triplet": {
                    "tasks.json": "examples/taskmaster/tasks.json",
                    "tasks_back.json": "examples/taskmaster/tasks_back.json",
                    "tasks_gameplay.json": "examples/taskmaster/tasks_gameplay.json",
                },
            },
        }

    def _doctor_record_payload(self, *, status: str = "ok", summary: str = "doctor ok") -> dict[str, object]:
        return {
            "kind": "doctor-project",
            "status": status,
            "summary": summary,
            "exit_code": 1 if status == "fail" else 0,
            "counts": {
                "fail": 0 if status != "fail" else 1,
                "warn": 0 if status == "ok" else 1,
                "ok": 1,
            },
            "checks": [
                {
                    "id": "project-godot",
                    "status": "ok",
                    "path": "project.godot",
                    "summary": "Godot project entry exists",
                    "recommendation": "keep current entry",
                }
            ],
        }

    def _boundary_record_payload(self, *, status: str = "fail", summary: str = "boundary fail") -> dict[str, object]:
        return {
            "kind": "check-directory-boundaries",
            "status": status,
            "summary": summary,
            "exit_code": 1 if status == "fail" else 0,
            "violations": [
                {
                    "rule_id": "game-core-no-godot",
                    "path": "Game.Core/Foo.cs",
                    "summary": "Godot API reference crossed a pure-code boundary",
                }
            ]
            if status == "fail"
            else [],
            "warnings": [],
            "rules_checked": [
                "game-core-no-godot",
                "contracts-no-godot",
                "scripts-core-no-godot",
                "base-docs-no-prd-leak",
                "base-08-template-only",
                "root-taskdoc-not-tracked",
            ],
        }

    def test_record_markdown_should_match_golden_output(self) -> None:
        payload = {
            "kind": "detect-project-stage",
            "status": "warn",
            "summary": "triplet missing",
            "generated_at": "2026-04-11T10:00:00+08:00",
            "stage": "bootstrap",
            "history_json": "logs/ci/2026-04-11/project-health/detect-project-stage-100000000000.json",
        }

        actual = project_health_common.record_markdown(payload)
        expected = (REPO_ROOT / "docs" / "workflows" / "examples" / "sc-project-health-record.example.md").read_text(encoding="utf-8")

        self.assertEqual(expected, actual)
        self.assertTrue(actual.endswith("\n"))

    def test_dashboard_html_example_should_match_golden_output(self) -> None:
        records = [
            {
                "kind": "detect-project-stage",
                "status": "warn",
                "summary": "triplet missing",
                "stage": "bootstrap",
                "history_json": "logs/ci/project-health/detect-project-stage-20260411T100000.json",
            }
        ]
        report_catalog = json.loads(
            (REPO_ROOT / "docs" / "workflows" / "examples" / "sc-project-health-report-catalog.example.json").read_text(encoding="utf-8")
        )
        active_task_summary = {
            "total": 1,
            "clean": 0,
            "llm_retry_stop_loss_blocked": 1,
            "sc_test_retry_stop_loss_blocked": 0,
            "artifact_integrity_blocked": 0,
            "recent_failure_summary_blocked": 1,
            "latest_json_mismatch": 0,
            "latest_json_repaired": 0,
            "rerun_guard_blocked": 1,
            "rerun_forbidden": 1,
            "deterministic_bundle_available": 1,
            "run_events_available": 1,
            "multi_turn_runs": 1,
            "turn_diff_available": 1,
            "turn_diff_reviewer_change": 1,
            "turn_diff_sidecar_change": 1,
            "turn_diff_approval_change": 1,
            "reviewer_activity_present": 1,
            "sidecar_activity_present": 1,
            "approval_activity_present": 1,
            "approval_contract_present": 1,
            "approval_pause_required": 1,
            "approval_fork_ready": 0,
            "approval_resume_ready": 0,
            "approval_inspect_required": 0,
            "run_type_planned_only": 0,
            "run_type_deterministic_only": 1,
            "run_type_full": 0,
            "run_type_llm_only": 0,
            "run_type_preflight_only": 0,
            "next_action_needs_fix_fast": 1,
            "next_action_inspect": 0,
            "next_action_resume": 0,
            "next_action_continue": 0,
            "chapter6_can_skip_6_7": 1,
            "chapter6_can_go_to_6_8": 1,
            "top_records": [
                {
                    "task_id": "15",
                    "status": "fail",
                    "clean_state": "deterministic_ok_llm_not_clean",
                    "recommended_action": "needs-fix-fast",
                    "recommended_action_why": "Repeat reviewer family is already deterministic.",
                    "recommended_command": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 15 --max-rounds 1",
                    "forbidden_commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 15"],
                    "latest_reason": "rerun_blocked:repeat_review_needs_fix",
                    "latest_run_type": "deterministic-only",
                    "latest_reuse_mode": "deterministic-only-reuse",
                    "latest_artifact_integrity": "",
                    "latest_diagnostics_keys": ["recent_failure_summary"],
                    "chapter6_next_action": "needs-fix-fast",
                    "chapter6_can_skip_6_7": True,
                    "chapter6_can_go_to_6_8": True,
                    "chapter6_blocked_by": "rerun_guard",
                    "chapter6_rerun_forbidden": True,
                    "chapter6_rerun_override": "--allow-rerun",
                    "chapter6_stop_loss_note": "Recent reviewer-only reruns already repeated the same Needs Fix family; switch to needs-fix-fast or record the remaining findings instead of reopening 6.7.",
                    "latest_json": "logs/ci/2026-04-10/sc-review-pipeline-task-15/latest.json",
                    "reported_latest_json": "",
                    "latest_json_mismatch": False,
                    "latest_json_repaired": False,
                    "paths": {
                        "summary_json": "logs/ci/2026-04-10/sc-review-pipeline-task-15-run-15/summary.json",
                        "execution_context_json": "logs/ci/2026-04-10/sc-review-pipeline-task-15-run-15/execution-context.json",
                    },
                    "deterministic_bundle": {
                        "sc_test": {"status": "ok"},
                        "sc_acceptance_check": {"status": "ok"},
                    },
                    "candidate_commands": {
                        "resume_summary": "py -3 scripts/python/dev_cli.py resume-task --task-id 15",
                        "inspect": "py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id 15",
                        "resume": "py -3 scripts/sc/run_review_pipeline.py --task-id 15 --resume",
                        "fork": "py -3 scripts/sc/run_review_pipeline.py --task-id 15 --fork",
                        "rerun": "py -3 scripts/sc/run_review_pipeline.py --task-id 15",
                        "needs_fix_fast": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 15 --max-rounds 1",
                    },
                    "diagnostics": {
                        "recent_failure_summary": {
                            "latest_failure_family": "review-needs-fix",
                            "same_family_count": 2,
                            "stop_full_rerun_recommended": True,
                        }
                    },
                    "run_event_summary": {
                        "path": "logs/ci/2026-04-10/sc-review-pipeline-task-15-run-15/run-events.jsonl",
                        "event_count": 5,
                        "turn_count": 2,
                        "latest_turn_id": "run-15:turn-2",
                        "latest_turn_seq": 2,
                        "latest_event": "sidecar_active_task_synced",
                        "family_counts": [
                            {"name": "approval", "count": 1},
                            {"name": "reviewer", "count": 1},
                            {"name": "run", "count": 2},
                            {"name": "sidecar", "count": 1},
                        ],
                        "previous_turn_family_counts": [
                            {"name": "run", "count": 1},
                        ],
                        "latest_turn_family_counts": [
                            {"name": "approval", "count": 1},
                            {"name": "reviewer", "count": 1},
                            {"name": "run", "count": 1},
                            {"name": "sidecar", "count": 1},
                        ],
                        "turn_family_delta": [
                            {"name": "approval", "count": 1},
                            {"name": "reviewer", "count": 1},
                            {"name": "sidecar", "count": 1},
                        ],
                        "new_reviewers": ["code-reviewer"],
                        "new_sidecars": ["task-active"],
                        "approval_changed": True,
                        "reviewers": [
                            {"id": "code-reviewer", "event": "reviewer_completed", "status": "needs-fix"},
                        ],
                        "sidecars": [
                            {"id": "task-active", "event": "sidecar_active_task_synced", "status": "ok"},
                        ],
                        "approval": {
                            "event": "approval_request_written",
                            "status": "pending",
                            "action": "fork",
                            "request_id": "run-15:fork",
                            "transition": "created",
                        },
                    },
                    "approval_contract": {
                        "required_action": "fork",
                        "status": "pending",
                        "decision": "",
                        "recommended_action": "pause",
                        "allowed_actions": ["inspect", "pause"],
                        "blocked_actions": ["fork", "resume", "rerun"],
                        "reason": "Waiting for operator approval.",
                    },
                }
            ],
        }

        html = project_health_common.dashboard_html(
            records,
            generated_at="2026-04-11T10:00:00+08:00",
            report_catalog=report_catalog,
            report_catalog_path="logs/ci/project-health/report-catalog.latest.json",
            active_task_summary=active_task_summary,
        )
        expected = (REPO_ROOT / "docs" / "workflows" / "examples" / "sc-project-health-dashboard.example.html").read_text(encoding="utf-8")

        self.assertEqual(expected, html)
        self.assertIn("run_events_latest_turn: run-15:turn-2 seq=2", html)
        self.assertIn("approval_recommended_action: pause", html)
        self.assertIn("Auto-refresh is disabled", html)

    def test_write_project_health_record_should_consume_active_task_example(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            example = json.loads((REPO_ROOT / "docs" / "workflows" / "examples" / "sc-active-task.example.json").read_text(encoding="utf-8"))
            _write(
                root / "logs" / "ci" / "active-tasks" / "task-15.active.json",
                json.dumps(example, ensure_ascii=False, indent=2) + "\n",
            )
            _write(
                root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15" / "latest.json",
                json.dumps(
                    {
                        "task_id": "15",
                        "run_id": "run-15",
                        "status": "fail",
                        "date": "2026-04-10",
                        "latest_out_dir": str(root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15-run-15"),
                        "summary_path": str(root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15-run-15" / "summary.json"),
                        "execution_context_path": str(root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15-run-15" / "execution-context.json"),
                        "repair_guide_json_path": str(root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15-run-15" / "repair-guide.json"),
                        "repair_guide_md_path": str(root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15-run-15" / "repair-guide.md"),
                        "run_events_path": str(root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15-run-15" / "run-events.jsonl"),
                    },
                    ensure_ascii=False,
                    indent=2,
                ) + "\n",
            )
            _write(
                root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15-run-15" / "summary.json",
                json.dumps(
                    {
                        "cmd": "sc-review-pipeline",
                        "status": "fail",
                        "recommended_action": "needs-fix-fast",
                        "recommended_action_why": "Repeat reviewer family is already deterministic.",
                        "recommended_command": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 15 --max-rounds 1",
                        "forbidden_commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 15"],
                    },
                    ensure_ascii=False,
                    indent=2,
                ) + "\n",
            )
            _write(
                root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15-run-15" / "execution-context.json",
                json.dumps(
                    {
                        "approval": example["approval"],
                    },
                    ensure_ascii=False,
                    indent=2,
                ) + "\n",
            )
            _write(root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15-run-15" / "repair-guide.json", json.dumps({"status": "needs-fix"}, ensure_ascii=False, indent=2) + "\n")
            _write(root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15-run-15" / "repair-guide.md", "# repair\n")
            _write(
                root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15-run-15" / "run-events.jsonl",
                (
                    (REPO_ROOT / "docs" / "workflows" / "examples" / "sc-run-events.example.jsonl")
                    .read_text(encoding="utf-8")
                    .replace("20260321T100000Z-10", "run-15")
                    .replace('"task_id":"10"', '"task_id":"15"')
                ),
            )

            project_health.write_project_health_record(
                root=root,
                kind="detect-project-stage",
                payload=self._detect_record_payload(),
            )

            latest_index = json.loads((root / "logs" / "ci" / "project-health" / "latest.json").read_text(encoding="utf-8"))
            active_task_summary = latest_index["active_task_summary"]
            top_record = active_task_summary["top_records"][0]
            detect_latest = json.loads(
                (root / "logs" / "ci" / "project-health" / "detect-project-stage.latest.json").read_text(encoding="utf-8")
            )

            project_health_schema.validate_project_health_dashboard_payload(latest_index)
            project_health_schema.validate_project_health_record_payload(detect_latest)
            self.assertEqual(1, active_task_summary["total"])
            self.assertEqual(1, active_task_summary["approval_pause_required"])
            self.assertEqual(1, active_task_summary["turn_diff_available"])
            self.assertEqual("needs-fix-fast", top_record["recommended_action"])
            self.assertEqual("pause", top_record["approval_contract"]["recommended_action"])
            self.assertEqual("run-15:turn-2", top_record["run_event_summary"]["latest_turn_id"])

    def test_project_health_scan_should_validate_against_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write(root / "project.godot", "[application]\nconfig/name=\"Demo\"\n")
            _write(root / "README.md", "# Demo\n")
            _write(root / "AGENTS.md", "# Demo\n")
            _write(root / "examples" / "taskmaster" / "tasks.json", "{}\n")
            _write(root / "examples" / "taskmaster" / "tasks_back.json", "{}\n")
            _write(root / "examples" / "taskmaster" / "tasks_gameplay.json", "{}\n")

            payload = project_health.project_health_scan(root)
            latest_scan = json.loads(
                (root / "logs" / "ci" / "project-health" / "project-health-scan.latest.json").read_text(encoding="utf-8")
            )

            project_health_schema.validate_project_health_scan_payload(payload)
            project_health_schema.validate_project_health_scan_payload(latest_scan)
            self.assertEqual("project-health-scan", payload["kind"])
            self.assertEqual(3, len(payload["results"]))
            self.assertEqual("detect-project-stage", payload["results"][0]["kind"])
            self.assertEqual("doctor-project", payload["results"][1]["kind"])
            self.assertEqual("check-directory-boundaries", payload["results"][2]["kind"])
            self.assertEqual(payload, latest_scan)

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
                        "recommended_command": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 14 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
                        "forbidden_commands": [
                            "py -3 scripts/sc/run_review_pipeline.py --task-id 14",
                            "py -3 scripts/sc/run_review_pipeline.py --task-id 14 --resume",
                        ],
                        "candidate_commands": {
                            "resume_summary": "py -3 scripts/python/dev_cli.py resume-task --task-id 14",
                            "inspect": "py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --latest logs/ci/2026-04-06/sc-review-pipeline-task-14/latest.json",
                            "resume": "py -3 scripts/sc/run_review_pipeline.py --task-id 14 --resume",
                            "fork": "py -3 scripts/sc/run_review_pipeline.py --task-id 14 --fork",
                            "rerun": "py -3 scripts/sc/run_review_pipeline.py --task-id 14",
                            "needs_fix_fast": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 14 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
                        },
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
                root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-14-run-a" / "execution-context.json",
                json.dumps(
                    {
                        "approval": {
                            "required_action": "fork",
                            "status": "pending",
                            "decision": "",
                            "reason": "Fork approval is still pending.",
                            "request_id": "run-a:fork",
                            "recommended_action": "pause",
                            "allowed_actions": ["inspect", "pause"],
                            "blocked_actions": ["fork", "resume", "rerun"],
                        }
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
            _write(
                root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-14-run-a" / "run-events.jsonl",
                "\n".join(
                    [
                        json.dumps(
                            {
                                "schema_version": "1.0.0",
                                "ts": "2026-04-06T09:18:00Z",
                                "event": "run_started",
                                "event_family": "run",
                                "task_id": "14",
                                "run_id": "run-a",
                                "turn_id": "run-a:turn-1",
                                "turn_seq": 1,
                                "delivery_profile": "fast-ship",
                                "security_profile": "host-safe",
                                "item_kind": "run",
                                "item_id": "run-a",
                                "step_name": None,
                                "status": None,
                                "details": {},
                            },
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            {
                                "schema_version": "1.0.0",
                                "ts": "2026-04-06T09:18:20Z",
                                "event": "run_resumed",
                                "event_family": "run",
                                "task_id": "14",
                                "run_id": "run-a",
                                "turn_id": "run-a:turn-2",
                                "turn_seq": 2,
                                "delivery_profile": "fast-ship",
                                "security_profile": "host-safe",
                                "item_kind": "run",
                                "item_id": "run-a",
                                "step_name": None,
                                "status": None,
                                "details": {},
                            },
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            {
                                "schema_version": "1.0.0",
                                "ts": "2026-04-06T09:18:21Z",
                                "event": "approval_request_written",
                                "event_family": "approval",
                                "task_id": "14",
                                "run_id": "run-a",
                                "turn_id": "run-a:turn-2",
                                "turn_seq": 2,
                                "delivery_profile": "fast-ship",
                                "security_profile": "host-safe",
                                "item_kind": "approval",
                                "item_id": "run-a:fork",
                                "step_name": None,
                                "status": "pending",
                                "details": {
                                    "action": "fork",
                                    "request_id": "run-a:fork",
                                    "transition": "created",
                                },
                            },
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            {
                                "schema_version": "1.0.0",
                                "ts": "2026-04-06T09:18:23Z",
                                "event": "reviewer_completed",
                                "event_family": "reviewer",
                                "task_id": "14",
                                "run_id": "run-a",
                                "turn_id": "run-a:turn-2",
                                "turn_seq": 2,
                                "delivery_profile": "fast-ship",
                                "security_profile": "host-safe",
                                "item_kind": "reviewer",
                                "item_id": "code-reviewer",
                                "step_name": None,
                                "status": "fail",
                                "details": {
                                    "reviewer": "code-reviewer",
                                    "review_verdict": "needs-fix",
                                },
                            },
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            {
                                "schema_version": "1.0.0",
                                "ts": "2026-04-06T09:18:24Z",
                                "event": "sidecar_execution_context_synced",
                                "event_family": "sidecar",
                                "task_id": "14",
                                "run_id": "run-a",
                                "turn_id": "run-a:turn-2",
                                "turn_seq": 2,
                                "delivery_profile": "fast-ship",
                                "security_profile": "host-safe",
                                "item_kind": "sidecar",
                                "item_id": "execution-context.json",
                                "step_name": None,
                                "status": "ok",
                                "details": {
                                    "sidecar": "execution-context.json",
                                },
                            },
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            {
                                "schema_version": "1.0.0",
                                "ts": "2026-04-06T09:18:25Z",
                                "event": "sidecar_active_task_synced",
                                "event_family": "sidecar",
                                "task_id": "14",
                                "run_id": "run-a",
                                "turn_id": "run-a:turn-2",
                                "turn_seq": 2,
                                "delivery_profile": "fast-ship",
                                "security_profile": "host-safe",
                                "item_kind": "sidecar",
                                "item_id": "task-active",
                                "step_name": None,
                                "status": "fail",
                                "details": {
                                    "sidecar": "task-active",
                                },
                            },
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            {
                                "schema_version": "1.0.0",
                                "ts": "2026-04-06T09:18:30Z",
                                "event": "run_completed",
                                "event_family": "run",
                                "task_id": "14",
                                "run_id": "run-a",
                                "turn_id": "run-a:turn-2",
                                "turn_seq": 2,
                                "delivery_profile": "fast-ship",
                                "security_profile": "host-safe",
                                "item_kind": "run",
                                "item_id": "run-a",
                                "step_name": None,
                                "status": None,
                                "details": {
                                    "result": "fail",
                                },
                            },
                            ensure_ascii=False,
                        ),
                    ]
                )
                + "\n",
            )
            _write(root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-14-run-a" / "child-artifacts" / "sc-test" / "summary.json", json.dumps({"cmd": "sc-test", "status": "ok"}, ensure_ascii=False, indent=2) + "\n")
            _write(root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-14-run-a" / "child-artifacts" / "sc-acceptance-check" / "summary.json", json.dumps({"cmd": "sc-acceptance-check", "status": "ok"}, ensure_ascii=False, indent=2) + "\n")
            _write(root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-14-run-a" / "child-artifacts" / "sc-llm-review" / "summary.json", json.dumps({"status": "fail", "results": []}, ensure_ascii=False, indent=2) + "\n")
            _write(
                root / "logs" / "ci" / "2026-04-05" / "single-task-light-lane-v2-batch" / "summary.json",
                json.dumps(
                    {
                        "kind": "single-task-light-lane-batch",
                        "status": "fail",
                        "summary": "batch failures need targeted rerun",
                        "recommended_next_action": "inspect-hotspot-and-rerun-quarantined-slice",
                        "recommended_next_action_why": "extract timeout dominates the current shard",
                        "step_duration_totals": {"extract": 65.0, "semantic_gate": 12.0},
                        "step_duration_avg": {"extract": 8.125, "semantic_gate": 4.0},
                        "slowest_tasks": [
                            {
                                "task_id": "71",
                                "total_duration_sec": 19.5,
                                "slowest_step": "extract",
                                "slowest_step_duration_sec": 12.0,
                                "first_failed_step": "extract",
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
            )
            project_health.write_project_health_record(
                root=root,
                kind="detect-project-stage",
                payload=self._detect_record_payload(status="warn", summary="triplet missing", stage="triplet-missing"),
            )
            project_health.write_project_health_record(
                root=root,
                kind="doctor-project",
                payload=self._doctor_record_payload(),
            )
            project_health.write_project_health_record(
                root=root,
                kind="check-directory-boundaries",
                payload=self._boundary_record_payload(),
            )

            latest_index = json.loads(
                (root / "logs" / "ci" / "project-health" / "latest.json").read_text(encoding="utf-8")
            )
            latest_html = (root / "logs" / "ci" / "project-health" / "latest.html").read_text(encoding="utf-8")
            report_catalog = json.loads(
                (root / "logs" / "ci" / "project-health" / "report-catalog.latest.json").read_text(encoding="utf-8")
            )
            detect_latest = json.loads(
                (root / "logs" / "ci" / "project-health" / "detect-project-stage.latest.json").read_text(encoding="utf-8")
            )
            doctor_latest = json.loads(
                (root / "logs" / "ci" / "project-health" / "doctor-project.latest.json").read_text(encoding="utf-8")
            )
            boundaries_latest = json.loads(
                (root / "logs" / "ci" / "project-health" / "check-directory-boundaries.latest.json").read_text(encoding="utf-8")
            )

            project_health_schema.validate_project_health_dashboard_payload(latest_index)
            project_health_schema.validate_project_health_report_catalog_payload(report_catalog)
            project_health_schema.validate_project_health_record_payload(detect_latest)
            project_health_schema.validate_project_health_record_payload(doctor_latest)
            project_health_schema.validate_project_health_record_payload(boundaries_latest)
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
            self.assertEqual(1, latest_index["active_task_summary"]["run_events_available"])
            self.assertEqual(1, latest_index["active_task_summary"]["multi_turn_runs"])
            self.assertEqual(1, latest_index["active_task_summary"]["turn_diff_available"])
            self.assertEqual(1, latest_index["active_task_summary"]["turn_diff_reviewer_change"])
            self.assertEqual(1, latest_index["active_task_summary"]["turn_diff_sidecar_change"])
            self.assertEqual(1, latest_index["active_task_summary"]["turn_diff_approval_change"])
            self.assertEqual(1, latest_index["active_task_summary"]["reviewer_activity_present"])
            self.assertEqual(1, latest_index["active_task_summary"]["sidecar_activity_present"])
            self.assertEqual(1, latest_index["active_task_summary"]["approval_activity_present"])
            self.assertEqual(1, latest_index["active_task_summary"]["approval_contract_present"])
            self.assertEqual(1, latest_index["active_task_summary"]["approval_pause_required"])
            self.assertEqual(0, latest_index["active_task_summary"]["approval_fork_ready"])
            self.assertEqual(1, latest_index["active_task_summary"]["run_type_deterministic_only"])
            self.assertEqual(1, latest_index["active_task_summary"]["next_action_needs_fix_fast"])
            top_record = latest_index["active_task_summary"]["top_records"][0]
            self.assertEqual(
                "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 14 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
                top_record["recommended_command"],
            )
            self.assertEqual(2, len(top_record["forbidden_commands"]))
            self.assertEqual(2, top_record["run_event_summary"]["latest_turn_seq"])
            self.assertEqual("run-a:turn-2", top_record["run_event_summary"]["latest_turn_id"])
            self.assertEqual("run-a:turn-1", top_record["run_event_summary"]["previous_turn_id"])
            self.assertTrue(top_record["run_event_summary"]["approval_changed"])
            self.assertEqual("run-a:fork", top_record["run_event_summary"]["approval"]["request_id"])
            self.assertEqual("pause", top_record["approval_contract"]["recommended_action"])
            self.assertEqual(["inspect", "pause"], top_record["approval_contract"]["allowed_actions"])
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
            self.assertIn("recommended_command", latest_html)
            self.assertIn("forbidden_commands", latest_html)
            self.assertIn("resume_summary_command", latest_html)
            self.assertIn("inspect_command", latest_html)
            self.assertIn("needs_fix_command", latest_html)
            self.assertIn("py -3 scripts/python/dev_cli.py resume-task --task-id 14", latest_html)
            self.assertIn("py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --latest logs/ci/2026-04-06/sc-review-pipeline-task-14/latest.json", latest_html)
            self.assertIn("py -3 scripts/sc/run_review_pipeline.py --task-id 14 --resume", latest_html)
            self.assertIn("py -3 scripts/sc/run_review_pipeline.py --task-id 14 --fork", latest_html)
            self.assertIn("py -3 scripts/sc/run_review_pipeline.py --task-id 14", latest_html)
            self.assertIn("py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 14 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1", latest_html)
            self.assertIn("llm_retry_stop_loss_blocked", latest_html)
            self.assertIn("sc_test_retry_stop_loss_blocked", latest_html)
            self.assertIn("artifact_integrity_blocked", latest_html)
            self.assertIn("recent_failure_summary_blocked", latest_html)
            self.assertIn("run_events_available", latest_html)
            self.assertIn("multi_turn_runs", latest_html)
            self.assertIn("turn_diff_available", latest_html)
            self.assertIn("turn_diff_reviewer_change", latest_html)
            self.assertIn("turn_diff_sidecar_change", latest_html)
            self.assertIn("turn_diff_approval_change", latest_html)
            self.assertIn("reviewer_activity_present", latest_html)
            self.assertIn("sidecar_activity_present", latest_html)
            self.assertIn("approval_activity_present", latest_html)
            self.assertIn("approval_contract_present", latest_html)
            self.assertIn("approval_pause_required", latest_html)
            self.assertIn("run_events_latest_turn: run-a:turn-2 seq=2", latest_html)
            self.assertIn("run_events_previous_turn: run-a:turn-1 seq=1", latest_html)
            self.assertIn("run_events_latest_event: run_completed", latest_html)
            self.assertIn("run_events_families: run=3,sidecar=2,approval=1,reviewer=1", latest_html)
            self.assertIn("run_events_previous_turn_families: run=1", latest_html)
            self.assertIn("run_events_latest_turn_families: run=2,sidecar=2,approval=1,reviewer=1", latest_html)
            self.assertIn("run_events_turn_family_delta: approval=+1,reviewer=+1,run=+1,sidecar=+2", latest_html)
            self.assertIn("run_events_new_reviewers: code-reviewer", latest_html)
            self.assertIn("run_events_new_sidecars: execution-context.json,task-active", latest_html)
            self.assertIn("run_events_approval_changed: true", latest_html)
            self.assertIn("reviewer_activity: code-reviewer:fail/reviewer_completed", latest_html)
            self.assertIn("sidecar_activity: execution-context.json:ok/sidecar_execution_context_synced; task-active:fail/sidecar_active_task_synced", latest_html)
            self.assertIn("approval_activity: pending/approval_request_written action=fork request_id=run-a:fork transition=created", latest_html)
            self.assertIn("approval_required_action: fork", latest_html)
            self.assertIn("approval_status: pending", latest_html)
            self.assertIn("approval_recommended_action: pause", latest_html)
            self.assertIn("approval_allowed_actions: inspect,pause", latest_html)
            self.assertIn("approval_blocked_actions: fork,resume,rerun", latest_html)
            self.assertIn("approval_reason: Fork approval is still pending.", latest_html)
            self.assertIn("run_type_deterministic_only", latest_html)
            self.assertIn("recommended_next_action: inspect-hotspot-and-rerun-quarantined-slice", latest_html)
            self.assertIn("recommended_next_action_why: extract timeout dominates the current shard", latest_html)
            self.assertIn("step_duration_totals: extract=65.0s; semantic_gate=12.0s", latest_html)
            self.assertIn("step_duration_avg: extract=8.125s; semantic_gate=4.0s", latest_html)
            self.assertIn("slowest_tasks: T71 total=19.5s slowest=extract/12.0s first_failed=extract", latest_html)
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
                    payload=self._detect_record_payload(),
                )

            latest_index = json.loads((root / "logs" / "ci" / "project-health" / "latest.json").read_text(encoding="utf-8"))
            self.assertEqual(2, latest_index["active_task_summary"]["total"])
            self.assertEqual(1, len(latest_index["active_task_summary"]["top_records"]))

    def test_write_project_health_record_should_prefer_summary_recommendation_over_stale_active_task_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write(
                root / "logs" / "ci" / "active-tasks" / "task-22.active.json",
                json.dumps(
                    {
                        "cmd": "active-task-sidecar",
                        "task_id": "22",
                        "run_id": "run-22",
                        "status": "fail",
                        "updated_at_utc": "2026-04-10T09:18:04+00:00",
                        "recommended_action": "continue",
                        "recommended_action_why": "stale active-task recommendation",
                        "chapter6_hints": {
                            "next_action": "continue",
                            "can_skip_6_7": False,
                            "can_go_to_6_8": False,
                            "blocked_by": "",
                            "rerun_forbidden": False,
                            "rerun_override_flag": "",
                        },
                        "paths": {
                            "latest_json": "logs/ci/2026-04-10/sc-review-pipeline-task-22/latest.json",
                            "summary_json": "logs/ci/2026-04-10/sc-review-pipeline-task-22-run-22/summary.json",
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
            )
            _write(
                root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-22" / "latest.json",
                json.dumps(
                    {
                        "task_id": "22",
                        "run_id": "run-22",
                        "status": "fail",
                        "latest_out_dir": str(root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-22-run-22"),
                        "summary_path": str(root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-22-run-22" / "summary.json"),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
            )
            _write(
                root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-22-run-22" / "summary.json",
                json.dumps(
                    {
                        "cmd": "sc-review-pipeline",
                        "task_id": "22",
                        "requested_run_id": "run-22",
                        "run_id": "run-22",
                        "allow_overwrite": False,
                        "force_new_run_id": False,
                        "status": "fail",
                        "started_at_utc": "2026-04-10T00:00:00+00:00",
                        "finished_at_utc": "2026-04-10T00:01:00+00:00",
                        "elapsed_sec": 60,
                        "run_type": "full",
                        "reason": "rerun_blocked:repeat_review_needs_fix",
                        "reuse_mode": "deterministic-only-reuse",
                        "steps": [
                            {
                                "name": "sc-test",
                                "cmd": ["py", "-3", "scripts/sc/test.py"],
                                "rc": 0,
                                "status": "ok",
                                "log": "logs/ci/2026-04-10/sc-review-pipeline-task-22-run-22/sc-test.log",
                            }
                        ],
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
                        "recommended_action_why": "summary recommendation should win",
                        "candidate_commands": {
                            "needs_fix_fast": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 22 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
                            "rerun": "py -3 scripts/sc/run_review_pipeline.py --task-id 22",
                        },
                        "recommended_command": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 22 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
                        "forbidden_commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 22"],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
            )

            project_health.write_project_health_record(
                root=root,
                kind="detect-project-stage",
                payload=self._detect_record_payload(),
            )

            latest_index = json.loads((root / "logs" / "ci" / "project-health" / "latest.json").read_text(encoding="utf-8"))
            top_record = latest_index["active_task_summary"]["top_records"][0]
            latest_html = (root / "logs" / "ci" / "project-health" / "latest.html").read_text(encoding="utf-8")

            self.assertEqual("needs-fix-fast", top_record["recommended_action"])
            self.assertEqual("summary recommendation should win", top_record["recommended_action_why"])
            self.assertEqual(
                "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 22 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
                top_record["recommended_command"],
            )
            self.assertEqual(
                ["py -3 scripts/sc/run_review_pipeline.py --task-id 22"],
                top_record["forbidden_commands"],
            )
            self.assertEqual("needs-fix-fast", top_record["chapter6_hints"]["next_action"])
            self.assertEqual("rerun_blocked:repeat_review_needs_fix", top_record["latest_summary_signals"]["reason"])
            self.assertIn("summary recommendation should win", latest_html)
            self.assertIn("py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 22 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1", latest_html)

    def test_write_project_health_record_should_render_chapter6_route_lane_and_repo_noise_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write(
                root / "logs" / "ci" / "active-tasks" / "task-31.active.json",
                json.dumps(
                    {
                        "cmd": "active-task-sidecar",
                        "task_id": "31",
                        "run_id": "run-31",
                        "status": "fail",
                        "updated_at_utc": "2026-04-10T09:18:04+00:00",
                        "recommended_action": "inspect",
                        "recommended_action_why": "route preflight classified the failure as repo noise",
                        "chapter6_hints": {
                            "next_action": "inspect",
                            "can_skip_6_7": True,
                            "can_go_to_6_8": False,
                            "blocked_by": "rerun_guard",
                            "rerun_forbidden": True,
                            "rerun_override_flag": "--allow-full-rerun",
                        },
                        "paths": {
                            "latest_json": "logs/ci/2026-04-10/sc-review-pipeline-task-31/latest.json",
                            "summary_json": "logs/ci/2026-04-10/sc-review-pipeline-task-31-run-31/summary.json",
                        },
                        "diagnostics": {
                            "rerun_guard": {
                                "kind": "chapter6_route_repo_noise_stop",
                                "blocked": True,
                                "recommended_path": "repo-noise-stop",
                            },
                            "recent_failure_summary": {
                                "latest_failure_family": "transport: file is locked by another process",
                                "same_family_count": 2,
                                "stop_full_rerun_recommended": True,
                            },
                        },
                        "clean_state": {
                            "state": "not_clean",
                            "deterministic_ok": False,
                            "llm_status": "unknown",
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
            )
            _write(
                root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-31" / "latest.json",
                json.dumps({"task_id": "31", "run_id": "run-31"}, ensure_ascii=False, indent=2) + "\n",
            )

            project_health.write_project_health_record(
                root=root,
                kind="detect-project-stage",
                payload=self._detect_record_payload(),
            )

            latest_index = json.loads((root / "logs" / "ci" / "project-health" / "latest.json").read_text(encoding="utf-8"))
            latest_html = (root / "logs" / "ci" / "project-health" / "latest.html").read_text(encoding="utf-8")
            top_record = latest_index["active_task_summary"]["top_records"][0]

            self.assertEqual("repo-noise-stop", top_record["chapter6_route_lane"])
            self.assertEqual(
                "prior chapter6-route already classified this run as repo-noise",
                top_record["repo_noise_reason"],
            )
            self.assertIn("chapter6_route_lane: repo-noise-stop", latest_html)
            self.assertIn(
                "repo_noise_reason: prior chapter6-route already classified this run as repo-noise",
                latest_html,
            )


if __name__ == "__main__":
    unittest.main()
