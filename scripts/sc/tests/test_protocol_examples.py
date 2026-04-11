#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
PYTHON_DIR = REPO_ROOT / "scripts" / "python"
for candidate in (SC_DIR, PYTHON_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from _sidecar_schema import validate_run_event_payload
from _sidecar_schema import validate_approval_request_payload
from _sidecar_schema import validate_approval_response_payload
from _sidecar_schema import validate_active_task_payload
import _sidecar_schema as sidecar_schema
import _active_task_sidecar as active_task_sidecar
import inspect_run
import chapter6_route
import local_hard_checks_support
import _project_health_common as project_health_common
project_health_schema = __import__("_project_health_schema")
artifact_schema = __import__("_artifact_schema")


class ProtocolExamplesTests(unittest.TestCase):
    def _assert_recovery_compact_schema(self, payload: dict[str, str]) -> None:
        schema = sidecar_schema._load_schema(
            REPO_ROOT / "scripts" / "sc" / "schemas" / "sc-recovery-compact.schema.json",
            "sc-recovery-compact",
        )
        if sidecar_schema.jsonschema is not None:
            errors = sidecar_schema._validate_with_jsonschema(payload, schema)
            self.assertEqual([], errors)
            return
        self.assertEqual(set(schema["required"]), set(payload))
        self.assertFalse(bool(schema.get("additionalProperties")))
        self.assertRegex(payload["turn_count"], r"^[0-9]+$")

    def test_approval_examples_should_validate_against_schema(self) -> None:
        request_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-approval-request.example.json"
        response_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-approval-response.example.json"

        request_payload = json.loads(request_path.read_text(encoding="utf-8"))
        response_payload = json.loads(response_path.read_text(encoding="utf-8"))

        self.assertEqual("fork", request_payload["action"])
        self.assertEqual("pending", request_payload["status"])
        self.assertEqual("pause", request_payload["recommended_action"])
        self.assertEqual(["inspect", "pause"], request_payload["allowed_actions"])
        self.assertEqual(["fork", "resume", "rerun"], request_payload["blocked_actions"])
        self.assertEqual(request_payload["request_id"], response_payload["request_id"])
        self.assertEqual("approved", response_payload["decision"])
        self.assertEqual("fork", response_payload["recommended_action"])
        self.assertEqual(["fork", "inspect"], response_payload["allowed_actions"])
        self.assertEqual(["resume", "rerun"], response_payload["blocked_actions"])

        validate_approval_request_payload(request_payload)
        validate_approval_response_payload(response_payload)

    def test_examples_readme_should_only_reference_existing_example_files(self) -> None:
        readme_path = REPO_ROOT / "docs" / "workflows" / "examples" / "README.md"
        text = readme_path.read_text(encoding="utf-8")
        referenced = {
            candidate
            for candidate in re.findall(r"`([^`]+)`", text)
            if candidate.startswith("sc-")
        }

        self.assertGreater(len(referenced), 0)
        for relative_name in referenced:
            with self.subTest(example=relative_name):
                self.assertTrue((readme_path.parent / relative_name).exists())

    def test_active_task_example_should_validate_against_schema(self) -> None:
        path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-active-task.example.json"
        payload = json.loads(path.read_text(encoding="utf-8"))

        validate_active_task_payload(payload)
        self.assertEqual("active-task-sidecar", payload["cmd"])
        self.assertEqual("pause", payload["approval"]["recommended_action"])
        self.assertEqual("run-15:turn-2", payload["run_event_summary"]["latest_turn_id"])

    def test_active_task_markdown_example_should_match_renderer_output(self) -> None:
        json_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-active-task.example.json"
        md_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-active-task.example.md"
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        expected = md_path.read_text(encoding="utf-8")

        actual = active_task_sidecar.render_active_task_markdown(payload)

        self.assertEqual(expected, actual)
        self.assertIn("- Chapter6 stop-loss note:", actual)
        self.assertIn("- Approval recommended action: pause", actual)
        self.assertIn("- Run events turn family delta: approval=+1, reviewer=+1, sidecar=+1", actual)

    def test_shared_recovery_compact_example_should_validate_against_schema(self) -> None:
        path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-recovery-compact.example.json"
        payload = json.loads(path.read_text(encoding="utf-8"))

        self._assert_recovery_compact_schema(payload)
        self.assertEqual("pause", payload["approval_recommended_action"])
        self.assertEqual("run-15:turn-2", payload["latest_turn"])

    def test_resume_task_compact_example_should_validate_against_schema(self) -> None:
        json_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-resume-task-compact.example.json"
        stdout_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-resume-task-compact.stdout.example.txt"
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        expected_stdout = stdout_path.read_text(encoding="utf-8")

        self._assert_recovery_compact_schema(payload)
        actual_stdout = "".join(f"{key}={value}\n" for key, value in payload.items())

        self.assertEqual(expected_stdout, actual_stdout)
        self.assertEqual("needs-fix-fast", payload["recommended_action"])
        self.assertEqual("pause", payload["approval_recommended_action"])

    def test_chapter6_route_compact_example_should_match_renderer_output(self) -> None:
        json_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-chapter6-route-compact.example.json"
        stdout_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-chapter6-route-compact.stdout.example.txt"
        compact_payload = json.loads(json_path.read_text(encoding="utf-8"))
        expected_stdout = stdout_path.read_text(encoding="utf-8")

        route_payload = {
            "task_id": "15",
            "run_id": "run-15",
            "preferred_lane": "run-6.8",
            "recommended_command": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 15",
            "forbidden_commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 15"],
            "reviewer_anchor_hit": True,
            "changed_paths": ["docs/architecture/overlays/PRD-1/08/overview.md"],
            "six_eight_worthwhile": True,
            "full_67_recommended": False,
            "repo_noise_classification": "task-issue",
            "repo_noise_reason": "",
            "recommended_action": "needs-fix-fast",
            "recommended_action_why": "",
            "latest_reason": "rerun_blocked:repeat_review_needs_fix",
            "chapter6_next_action": "needs-fix-fast",
            "blocked_by": "rerun_guard",
            "residual_recording": {
                "eligible": False,
                "reason": "no_low_priority_findings",
                "performed": False,
                "decision_log_path": "",
                "execution_plan_path": "",
            },
        }

        actual_compact = chapter6_route._compact_payload(route_payload)
        actual_stdout = "".join(f"{key}={value}\n" for key, value in actual_compact.items())

        self.assertEqual(compact_payload, actual_compact)
        self.assertEqual(expected_stdout, actual_stdout)
        self.assertEqual("run-6.8", compact_payload["preferred_lane"])
        self.assertEqual("yes", compact_payload["six_eight_worthwhile"])

    def test_project_health_report_catalog_example_should_validate_against_schema(self) -> None:
        path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-project-health-report-catalog.example.json"
        payload = json.loads(path.read_text(encoding="utf-8"))

        project_health_schema.validate_project_health_report_catalog_payload(payload)
        self.assertEqual(2, payload["total_json"])
        self.assertEqual("project-health-dashboard", payload["entries"][1]["kind"])

    def test_project_health_server_example_should_validate_against_schema(self) -> None:
        path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-project-health-server.example.json"
        payload = json.loads(path.read_text(encoding="utf-8"))

        project_health_schema.validate_project_health_server_payload(payload)
        self.assertEqual("127.0.0.1", payload["host"])
        self.assertEqual(8765, payload["port"])
        self.assertTrue(payload["url"].endswith("/latest.html"))

    def test_project_health_record_examples_should_validate_against_schema(self) -> None:
        for name, expected_kind in (
            ("sc-project-health-detect-project-stage.example.json", "detect-project-stage"),
            ("sc-project-health-doctor-project.example.json", "doctor-project"),
            ("sc-project-health-check-directory-boundaries.example.json", "check-directory-boundaries"),
        ):
            path = REPO_ROOT / "docs" / "workflows" / "examples" / name
            payload = json.loads(path.read_text(encoding="utf-8"))
            project_health_schema.validate_project_health_record_payload(payload)
            self.assertEqual(expected_kind, payload["kind"])

    def test_project_health_scan_example_should_validate_against_schema(self) -> None:
        path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-project-health-scan.example.json"
        payload = json.loads(path.read_text(encoding="utf-8"))

        project_health_schema.validate_project_health_scan_payload(payload)
        self.assertEqual("project-health-scan", payload["kind"])
        self.assertEqual(3, len(payload["results"]))

    def test_project_health_record_markdown_example_should_match_renderer_output(self) -> None:
        md_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-project-health-record.example.md"
        payload = {
            "kind": "detect-project-stage",
            "status": "warn",
            "summary": "triplet missing",
            "generated_at": "2026-04-11T10:00:00+08:00",
            "stage": "bootstrap",
            "history_json": "logs/ci/2026-04-11/project-health/detect-project-stage-100000000000.json",
        }

        actual = project_health_common.record_markdown(payload)
        expected = md_path.read_text(encoding="utf-8")

        self.assertEqual(expected, actual)
        self.assertIn("- stage: bootstrap", actual)
        self.assertIn("- history_json: logs/ci/2026-04-11/project-health/detect-project-stage-100000000000.json", actual)

    def test_local_hard_checks_examples_should_validate_against_schema(self) -> None:
        latest_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-local-hard-checks-latest-index.example.json"
        execution_context_path = (
            REPO_ROOT / "docs" / "workflows" / "examples" / "sc-local-hard-checks-execution-context.example.json"
        )
        repair_guide_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-local-hard-checks-repair-guide.example.json"

        latest_payload = json.loads(latest_path.read_text(encoding="utf-8"))
        execution_context_payload = json.loads(execution_context_path.read_text(encoding="utf-8"))
        repair_guide_payload = json.loads(repair_guide_path.read_text(encoding="utf-8"))

        artifact_schema.validate_local_hard_checks_latest_index_payload(latest_payload)
        artifact_schema.validate_local_hard_checks_execution_context_payload(execution_context_payload)
        artifact_schema.validate_local_hard_checks_repair_guide_payload(repair_guide_payload)

        self.assertEqual("fail", latest_payload["status"])
        self.assertEqual("run-dotnet", execution_context_payload["failed_step"])
        self.assertEqual("run-dotnet", repair_guide_payload["failed_step"])
        self.assertIn("--godot-bin", repair_guide_payload["rerun_command"])

    def test_local_hard_checks_repair_markdown_example_should_match_renderer_output(self) -> None:
        json_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-local-hard-checks-repair-guide.example.json"
        md_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-local-hard-checks-repair-guide.example.md"
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        expected = md_path.read_text(encoding="utf-8")

        actual = local_hard_checks_support.render_repair_guide_markdown(payload)

        self.assertEqual(expected, actual)
        self.assertIn("- failed_step: `run-dotnet`", actual)
        self.assertIn("run-local-hard-checks --godot-bin", actual)

    def test_local_hard_checks_compact_example_should_match_renderer_and_schema(self) -> None:
        inspect_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-local-hard-checks-inspect.example.json"
        compact_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-local-hard-checks-compact.example.json"
        stdout_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-local-hard-checks-compact.stdout.example.txt"

        inspect_payload = json.loads(inspect_path.read_text(encoding="utf-8"))
        compact_payload = json.loads(compact_path.read_text(encoding="utf-8"))
        compact_stdout = stdout_path.read_text(encoding="utf-8")

        actual_compact = inspect_run._compact_recommendation_payload(inspect_payload)
        actual_stdout = inspect_run._render_recommendation_only(inspect_payload)

        self._assert_recovery_compact_schema(compact_payload)
        self.assertEqual(compact_payload, actual_compact)
        self.assertEqual(compact_stdout, actual_stdout)
        self.assertEqual("repo", compact_payload["task_id"])
        self.assertEqual("rerun", compact_payload["recommended_action"])

    def test_local_hard_checks_inspect_stdout_example_should_match_json_payload(self) -> None:
        inspect_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-local-hard-checks-inspect.example.json"
        stdout_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-local-hard-checks-inspect.stdout.example.txt"

        inspect_payload = json.loads(inspect_path.read_text(encoding="utf-8"))
        expected = stdout_path.read_text(encoding="utf-8")
        actual = json.dumps(inspect_payload, ensure_ascii=False, indent=2) + "\n"

        self.assertEqual(expected, actual)
        self.assertIn('"recommended_action": "rerun"', actual)
        self.assertIn('"recommended_command": "py -3 scripts/python/dev_cli.py run-local-hard-checks --run-id local-demo"', actual)

    def test_pipeline_compact_example_should_match_renderer_and_schema(self) -> None:
        inspect_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-pipeline-inspect.example.json"
        compact_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-pipeline-compact.example.json"
        stdout_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-pipeline-compact.stdout.example.txt"

        inspect_payload = json.loads(inspect_path.read_text(encoding="utf-8"))
        compact_payload = json.loads(compact_path.read_text(encoding="utf-8"))
        compact_stdout = stdout_path.read_text(encoding="utf-8")

        actual_compact = inspect_run._compact_recommendation_payload(inspect_payload)
        actual_stdout = inspect_run._render_recommendation_only(inspect_payload)

        self._assert_recovery_compact_schema(compact_payload)
        self.assertEqual(compact_payload, actual_compact)
        self.assertEqual(compact_stdout, actual_stdout)
        self.assertEqual("pause", compact_payload["recommended_action"])
        self.assertEqual("approval_pending", compact_payload["blocked_by"])

    def test_pipeline_inspect_stdout_example_should_match_json_payload(self) -> None:
        inspect_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-pipeline-inspect.example.json"
        stdout_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-pipeline-inspect.stdout.example.txt"

        inspect_payload = json.loads(inspect_path.read_text(encoding="utf-8"))
        expected = stdout_path.read_text(encoding="utf-8")
        actual = json.dumps(inspect_payload, ensure_ascii=False, indent=2) + "\n"

        self.assertEqual(expected, actual)
        self.assertIn('"recommended_action": "pause"', actual)
        self.assertIn('"blocked_by": "approval_pending"', actual)

    def test_run_events_example_should_validate_against_schema(self) -> None:
        path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-run-events.example.jsonl"
        lines = path.read_text(encoding="utf-8").splitlines()
        payloads = [json.loads(line) for line in lines if line.strip()]

        self.assertGreaterEqual(len(payloads), 10)
        self.assertEqual({1, 2}, {int(item["turn_seq"]) for item in payloads})
        self.assertTrue(any(item["event_family"] == "approval" for item in payloads))
        self.assertTrue(any(item["event_family"] == "reviewer" for item in payloads))
        self.assertTrue(any(item["event"] == "run_completed" for item in payloads))
        self.assertEqual("sidecar", payloads[-1]["event_family"])

        for payload in payloads:
            validate_run_event_payload(payload)


if __name__ == "__main__":
    unittest.main()
