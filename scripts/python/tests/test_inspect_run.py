#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON_DIR = REPO_ROOT / "scripts" / "python"
SC_DIR = REPO_ROOT / "scripts" / "sc"
for candidate in (PYTHON_DIR, SC_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))


def _load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


inspect_run = _load_module("inspect_run_module", "scripts/python/inspect_run.py")


class InspectRunTests(unittest.TestCase):
    def test_pipeline_compact_example_should_match_recommendation_payload(self) -> None:
        inspect_example_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-pipeline-inspect.example.json"
        compact_example_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-pipeline-compact.example.json"

        payload = json.loads(inspect_example_path.read_text(encoding="utf-8"))
        expected = json.loads(compact_example_path.read_text(encoding="utf-8"))

        actual = inspect_run._compact_recommendation_payload(payload)

        self.assertEqual(expected, actual)

    def test_pipeline_main_should_match_full_stdout_example(self) -> None:
        inspect_example_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-pipeline-inspect.example.json"
        stdout_example_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-pipeline-inspect.stdout.example.txt"
        payload = json.loads(inspect_example_path.read_text(encoding="utf-8"))
        expected = stdout_example_path.read_text(encoding="utf-8")

        stdout = io.StringIO()
        argv = [
            "--repo-root",
            str(REPO_ROOT),
            "--kind",
            "pipeline",
            "--latest",
            "logs/ci/2026-04-10/sc-review-pipeline-task-15/latest.json",
        ]
        with (
            mock.patch.object(inspect_run, "inspect_run_artifacts", return_value=(1, payload)),
            mock.patch.object(sys, "argv", ["inspect_run.py", *argv]),
            redirect_stdout(stdout),
        ):
            rc = inspect_run.main()

        self.assertEqual(1, rc)
        self.assertEqual(expected, stdout.getvalue())

    def test_pipeline_main_recommendation_only_json_should_match_compact_example(self) -> None:
        inspect_example_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-pipeline-inspect.example.json"
        compact_example_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-pipeline-compact.example.json"
        payload = json.loads(inspect_example_path.read_text(encoding="utf-8"))
        expected = json.loads(compact_example_path.read_text(encoding="utf-8"))

        stdout = io.StringIO()
        argv = [
            "--repo-root",
            str(REPO_ROOT),
            "--kind",
            "pipeline",
            "--latest",
            "logs/ci/2026-04-10/sc-review-pipeline-task-15/latest.json",
            "--recommendation-only",
            "--recommendation-format",
            "json",
        ]
        with (
            mock.patch.object(inspect_run, "inspect_run_artifacts", return_value=(1, payload)),
            mock.patch.object(sys, "argv", ["inspect_run.py", *argv]),
            redirect_stdout(stdout),
        ):
            rc = inspect_run.main()

        self.assertEqual(1, rc)
        self.assertEqual(expected, json.loads(stdout.getvalue()))

    def test_pipeline_main_recommendation_only_kv_should_match_stdout_example(self) -> None:
        inspect_example_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-pipeline-inspect.example.json"
        stdout_example_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-pipeline-compact.stdout.example.txt"
        payload = json.loads(inspect_example_path.read_text(encoding="utf-8"))
        expected = stdout_example_path.read_text(encoding="utf-8")

        stdout = io.StringIO()
        argv = [
            "--repo-root",
            str(REPO_ROOT),
            "--kind",
            "pipeline",
            "--latest",
            "logs/ci/2026-04-10/sc-review-pipeline-task-15/latest.json",
            "--recommendation-only",
        ]
        with (
            mock.patch.object(inspect_run, "inspect_run_artifacts", return_value=(1, payload)),
            mock.patch.object(sys, "argv", ["inspect_run.py", *argv]),
            redirect_stdout(stdout),
        ):
            rc = inspect_run.main()

        self.assertEqual(1, rc)
        self.assertEqual(expected, stdout.getvalue())

    def test_local_hard_checks_compact_example_should_match_recommendation_payload(self) -> None:
        inspect_example_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-local-hard-checks-inspect.example.json"
        compact_example_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-local-hard-checks-compact.example.json"

        payload = json.loads(inspect_example_path.read_text(encoding="utf-8"))
        expected = json.loads(compact_example_path.read_text(encoding="utf-8"))

        actual = inspect_run._compact_recommendation_payload(payload)

        self.assertEqual(expected, actual)

    def test_local_hard_checks_main_should_match_full_stdout_example(self) -> None:
        inspect_example_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-local-hard-checks-inspect.example.json"
        stdout_example_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-local-hard-checks-inspect.stdout.example.txt"
        payload = json.loads(inspect_example_path.read_text(encoding="utf-8"))
        expected = stdout_example_path.read_text(encoding="utf-8")

        stdout = io.StringIO()
        argv = [
            "--repo-root",
            str(REPO_ROOT),
            "--kind",
            "local-hard-checks",
            "--latest",
            "logs/ci/2026-04-11/local-hard-checks-latest.json",
        ]
        with (
            mock.patch.object(inspect_run, "inspect_run_artifacts", return_value=(1, payload)),
            mock.patch.object(sys, "argv", ["inspect_run.py", *argv]),
            redirect_stdout(stdout),
        ):
            rc = inspect_run.main()

        self.assertEqual(1, rc)
        self.assertEqual(expected, stdout.getvalue())

    def test_local_hard_checks_main_recommendation_only_json_should_match_compact_example(self) -> None:
        inspect_example_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-local-hard-checks-inspect.example.json"
        compact_example_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-local-hard-checks-compact.example.json"
        payload = json.loads(inspect_example_path.read_text(encoding="utf-8"))
        expected = json.loads(compact_example_path.read_text(encoding="utf-8"))

        stdout = io.StringIO()
        argv = [
            "--repo-root",
            str(REPO_ROOT),
            "--kind",
            "local-hard-checks",
            "--latest",
            "logs/ci/2026-04-11/local-hard-checks-latest.json",
            "--recommendation-only",
            "--recommendation-format",
            "json",
        ]
        with (
            mock.patch.object(inspect_run, "inspect_run_artifacts", return_value=(1, payload)),
            mock.patch.object(sys, "argv", ["inspect_run.py", *argv]),
            redirect_stdout(stdout),
        ):
            rc = inspect_run.main()

        self.assertEqual(1, rc)
        self.assertEqual(expected, json.loads(stdout.getvalue()))

    def test_local_hard_checks_main_recommendation_only_kv_should_match_stdout_example(self) -> None:
        inspect_example_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-local-hard-checks-inspect.example.json"
        stdout_example_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-local-hard-checks-compact.stdout.example.txt"
        payload = json.loads(inspect_example_path.read_text(encoding="utf-8"))
        expected = stdout_example_path.read_text(encoding="utf-8")

        stdout = io.StringIO()
        argv = [
            "--repo-root",
            str(REPO_ROOT),
            "--kind",
            "local-hard-checks",
            "--latest",
            "logs/ci/2026-04-11/local-hard-checks-latest.json",
            "--recommendation-only",
        ]
        with (
            mock.patch.object(inspect_run, "inspect_run_artifacts", return_value=(1, payload)),
            mock.patch.object(sys, "argv", ["inspect_run.py", *argv]),
            redirect_stdout(stdout),
        ):
            rc = inspect_run.main()

        self.assertEqual(1, rc)
        self.assertEqual(expected, stdout.getvalue())

    def test_inspect_run_artifacts_should_use_repo_scoped_commands_for_local_hard_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            latest = root / "logs" / "ci" / "2026-04-11" / "local-hard-checks-latest.json"
            out_dir = root / "logs" / "ci" / "2026-04-11" / "local-hard-checks-local-demo"
            _write_json(
                latest,
                {
                    "cmd": "local-hard-checks",
                    "task_id": "repo",
                    "run_id": "local-demo",
                    "status": "fail",
                    "out_dir": str(out_dir),
                    "summary_path": str(out_dir / "summary.json"),
                    "execution_context_path": str(out_dir / "execution-context.json"),
                    "repair_guide_json_path": str(out_dir / "repair-guide.json"),
                    "repair_guide_md_path": str(out_dir / "repair-guide.md"),
                    "run_events_path": str(out_dir / "run-events.jsonl"),
                },
            )
            _write_json(
                out_dir / "summary.json",
                {
                    "schema_version": "1.0.0",
                    "protocol_version": "1.0.0",
                    "cmd": "local-hard-checks",
                    "task_id": "repo",
                    "requested_run_id": "local-demo",
                    "run_id": "local-demo",
                    "delivery_profile": "fast-ship",
                    "security_profile": "host-safe",
                    "status": "fail",
                    "failed_step": "run-dotnet",
                    "started_at": "2026-04-11T11:00:00Z",
                    "finished_at": "2026-04-11T11:01:00Z",
                    "out_dir": str(out_dir),
                    "steps": [
                        {
                            "name": "run-dotnet",
                            "cmd": ["py", "-3", "scripts/python/run_dotnet.py"],
                            "rc": 1,
                            "status": "fail",
                            "log": str(out_dir / "run-dotnet.log"),
                        }
                    ],
                },
            )
            _write_json(
                out_dir / "execution-context.json",
                {
                    "cmd": "local-hard-checks",
                    "task_id": "repo",
                    "requested_run_id": "local-demo",
                    "run_id": "local-demo",
                    "delivery_profile": "fast-ship",
                    "security_profile": "host-safe",
                    "status": "fail",
                    "failed_step": "run-dotnet",
                    "artifacts": {
                        "summary_json": str(out_dir / "summary.json"),
                        "execution_context_json": str(out_dir / "execution-context.json"),
                        "repair_guide_json": str(out_dir / "repair-guide.json"),
                        "repair_guide_md": str(out_dir / "repair-guide.md"),
                        "run_events_jsonl": str(out_dir / "run-events.jsonl"),
                        "harness_capabilities_json": str(out_dir / "harness-capabilities.json"),
                        "run_id_txt": str(out_dir / "run_id.txt"),
                    },
                },
            )
            _write_json(
                out_dir / "repair-guide.json",
                {
                    "cmd": "local-hard-checks",
                    "task_id": "repo",
                    "run_id": "local-demo",
                    "status": "fail",
                    "failed_step": "run-dotnet",
                    "artifacts": {
                        "summary_json": str(out_dir / "summary.json"),
                        "execution_context_json": str(out_dir / "execution-context.json"),
                    },
                    "next_actions": [
                        "Open summary.json and inspect the first failing step.",
                        "Open the failing step log and then inspect the referenced artifact directory.",
                        "Re-run the command after fixing the first failing step.",
                    ],
                    "rerun_command": [
                        "py",
                        "-3",
                        "scripts/python/dev_cli.py",
                        "run-local-hard-checks",
                        "--run-id",
                        "local-demo",
                    ],
                },
            )
            (out_dir / "repair-guide.md").write_text("# Local Hard Checks Repair Guide\n", encoding="utf-8")
            (out_dir / "run-events.jsonl").write_text("", encoding="utf-8")
            (out_dir / "run-dotnet.log").write_text("fail\n", encoding="utf-8")

            rc, payload = inspect_run.inspect_run_artifacts(repo_root=root, kind="local-hard-checks", latest=str(latest))

            self.assertEqual(1, rc)
            self.assertEqual("local-hard-checks", payload["kind"])
            self.assertEqual("rerun", payload["recommended_action"])
            self.assertEqual(
                "py -3 scripts/python/dev_cli.py run-local-hard-checks --run-id local-demo",
                payload["recommended_command"],
            )
            self.assertEqual(
                "py -3 scripts/python/dev_cli.py inspect-run --kind local-hard-checks --latest logs/ci/2026-04-11/local-hard-checks-latest.json",
                payload["candidate_commands"]["inspect"],
            )
            self.assertEqual(
                "py -3 scripts/python/dev_cli.py run-local-hard-checks --run-id local-demo",
                payload["candidate_commands"]["rerun"],
            )
            self.assertEqual("", payload["candidate_commands"]["resume"])
            self.assertEqual("", payload["candidate_commands"]["fork"])
            self.assertEqual([], payload["forbidden_commands"])
            self.assertIn("repo-scoped hard checks failed at run-dotnet", payload["recommended_action_why"].lower())
            example_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-local-hard-checks-inspect.example.json"
            expected = json.loads(example_path.read_text(encoding="utf-8"))
            self.assertEqual(expected, payload)

    def test_inspect_run_artifacts_should_pause_when_fork_approval_is_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            latest = root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15" / "latest.json"
            out_dir = root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15-run-15"
            _write_json(
                latest,
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "15",
                    "run_id": "run-15",
                    "status": "fail",
                    "latest_out_dir": str(out_dir),
                    "summary_path": str(out_dir / "summary.json"),
                    "execution_context_path": str(out_dir / "execution-context.json"),
                    "repair_guide_json_path": str(out_dir / "repair-guide.json"),
                },
            )
            _write_json(
                out_dir / "summary.json",
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "15",
                    "run_id": "run-15",
                    "status": "fail",
                    "reason": "review_pending",
                    "steps": [],
                },
            )
            _write_json(
                out_dir / "execution-context.json",
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "15",
                    "run_id": "run-15",
                    "status": "fail",
                    "delivery_profile": "fast-ship",
                    "security_profile": "host-safe",
                    "approval": {
                        "soft_gate": True,
                        "required_action": "fork",
                        "status": "pending",
                        "decision": "",
                        "reason": "Await fork approval before continuing recovery.",
                        "request_id": "run-15:fork",
                        "request_path": str(out_dir / "approval-request.json"),
                        "response_path": "",
                    },
                    "diagnostics": {},
                },
            )
            _write_json(
                out_dir / "repair-guide.json",
                {
                    "status": "needs-fix",
                    "task_id": "15",
                    "summary_status": "fail",
                    "failed_step": "",
                    "approval": {
                        "soft_gate": True,
                        "required_action": "fork",
                        "status": "pending",
                        "decision": "",
                        "reason": "Await fork approval before continuing recovery.",
                        "request_id": "run-15:fork",
                        "request_path": str(out_dir / "approval-request.json"),
                        "response_path": "",
                    },
                    "recommendations": [
                        {
                            "id": "approval-fork-pending",
                            "title": "Fork recovery is pending approval",
                            "why": "Await fork approval before continuing recovery.",
                            "commands": [],
                            "files": [str(out_dir / "approval-request.json")],
                        }
                    ],
                },
            )

            rc, payload = inspect_run.inspect_run_artifacts(repo_root=root, kind="pipeline", task_id="15")

            self.assertEqual(1, rc)
            self.assertEqual("pause", payload["recommended_action"])
            self.assertEqual("pause", payload["chapter6_hints"]["next_action"])
            self.assertEqual("approval_pending", payload["chapter6_hints"]["blocked_by"])
            self.assertEqual("", payload["recommended_command"])
            self.assertIn("py -3 scripts/sc/run_review_pipeline.py --task-id 15 --resume", payload["forbidden_commands"])
            self.assertIn("py -3 scripts/sc/run_review_pipeline.py --task-id 15 --fork", payload["forbidden_commands"])
            self.assertEqual("pending", payload["approval"]["status"])
            self.assertEqual("pause", payload["approval"]["recommended_action"])
            self.assertEqual(["inspect", "pause"], payload["approval"]["allowed_actions"])
            self.assertIn("approval", payload["recommended_action_why"].lower())

    def test_inspect_run_artifacts_should_require_fork_when_fork_approval_is_approved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            latest = root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15" / "latest.json"
            out_dir = root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15-run-15"
            _write_json(
                latest,
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "15",
                    "run_id": "run-15",
                    "status": "fail",
                    "latest_out_dir": str(out_dir),
                    "summary_path": str(out_dir / "summary.json"),
                    "execution_context_path": str(out_dir / "execution-context.json"),
                    "repair_guide_json_path": str(out_dir / "repair-guide.json"),
                },
            )
            _write_json(
                out_dir / "summary.json",
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "15",
                    "run_id": "run-15",
                    "status": "fail",
                    "reason": "review_pending",
                    "steps": [],
                },
            )
            _write_json(
                out_dir / "execution-context.json",
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "15",
                    "run_id": "run-15",
                    "status": "fail",
                    "delivery_profile": "fast-ship",
                    "security_profile": "host-safe",
                    "approval": {
                        "soft_gate": True,
                        "required_action": "fork",
                        "status": "approved",
                        "decision": "approved",
                        "reason": "Fork is approved for isolated recovery.",
                        "request_id": "run-15:fork",
                        "request_path": str(out_dir / "approval-request.json"),
                        "response_path": str(out_dir / "approval-response.json"),
                    },
                    "diagnostics": {},
                },
            )
            _write_json(
                out_dir / "repair-guide.json",
                {
                    "status": "needs-fix",
                    "task_id": "15",
                    "summary_status": "fail",
                    "failed_step": "",
                    "approval": {
                        "soft_gate": True,
                        "required_action": "fork",
                        "status": "approved",
                        "decision": "approved",
                        "reason": "Fork is approved for isolated recovery.",
                        "request_id": "run-15:fork",
                        "request_path": str(out_dir / "approval-request.json"),
                        "response_path": str(out_dir / "approval-response.json"),
                    },
                    "recommendations": [
                        {
                            "id": "approval-fork-approved",
                            "title": "Fork recovery is approved",
                            "why": "Fork is approved for isolated recovery.",
                            "commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 15 --fork"],
                            "files": [str(out_dir / "approval-response.json")],
                        }
                    ],
                },
            )

            rc, payload = inspect_run.inspect_run_artifacts(repo_root=root, kind="pipeline", task_id="15")

            self.assertEqual(1, rc)
            self.assertEqual("fork", payload["recommended_action"])
            self.assertEqual("fork", payload["chapter6_hints"]["next_action"])
            self.assertEqual("approval_approved", payload["chapter6_hints"]["blocked_by"])
            self.assertEqual("py -3 scripts/sc/run_review_pipeline.py --task-id 15 --fork", payload["recommended_command"])
            self.assertIn("py -3 scripts/sc/run_review_pipeline.py --task-id 15 --resume", payload["forbidden_commands"])
            self.assertEqual("approved", payload["approval"]["status"])
            self.assertEqual("fork", payload["approval"]["recommended_action"])

    def test_inspect_run_artifacts_should_resume_when_fork_approval_is_denied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            latest = root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15" / "latest.json"
            out_dir = root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15-run-15"
            _write_json(
                latest,
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "15",
                    "run_id": "run-15",
                    "status": "fail",
                    "latest_out_dir": str(out_dir),
                    "summary_path": str(out_dir / "summary.json"),
                    "execution_context_path": str(out_dir / "execution-context.json"),
                    "repair_guide_json_path": str(out_dir / "repair-guide.json"),
                },
            )
            _write_json(
                out_dir / "summary.json",
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "15",
                    "run_id": "run-15",
                    "status": "fail",
                    "reason": "review_pending",
                    "steps": [],
                },
            )
            _write_json(
                out_dir / "execution-context.json",
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "15",
                    "run_id": "run-15",
                    "status": "fail",
                    "delivery_profile": "fast-ship",
                    "security_profile": "host-safe",
                    "approval": {
                        "soft_gate": True,
                        "required_action": "fork",
                        "status": "denied",
                        "decision": "denied",
                        "reason": "Fork is denied; continue inside the current run.",
                        "request_id": "run-15:fork",
                        "request_path": str(out_dir / "approval-request.json"),
                        "response_path": str(out_dir / "approval-response.json"),
                    },
                    "diagnostics": {},
                },
            )
            _write_json(
                out_dir / "repair-guide.json",
                {
                    "status": "needs-fix",
                    "task_id": "15",
                    "summary_status": "fail",
                    "failed_step": "",
                    "approval": {
                        "soft_gate": True,
                        "required_action": "fork",
                        "status": "denied",
                        "decision": "denied",
                        "reason": "Fork is denied; continue inside the current run.",
                        "request_id": "run-15:fork",
                        "request_path": str(out_dir / "approval-request.json"),
                        "response_path": str(out_dir / "approval-response.json"),
                    },
                    "recommendations": [
                        {
                            "id": "approval-fork-denied",
                            "title": "Fork recovery was denied",
                            "why": "Fork is denied; continue inside the current run.",
                            "commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 15 --resume"],
                            "files": [str(out_dir / "approval-response.json")],
                        }
                    ],
                },
            )

            rc, payload = inspect_run.inspect_run_artifacts(repo_root=root, kind="pipeline", task_id="15")

            self.assertEqual(1, rc)
            self.assertEqual("resume", payload["recommended_action"])
            self.assertEqual("resume", payload["chapter6_hints"]["next_action"])
            self.assertEqual("approval_denied", payload["chapter6_hints"]["blocked_by"])
            self.assertEqual("py -3 scripts/sc/run_review_pipeline.py --task-id 15 --resume", payload["recommended_command"])
            self.assertIn("py -3 scripts/sc/run_review_pipeline.py --task-id 15 --fork", payload["forbidden_commands"])
            self.assertEqual("denied", payload["approval"]["status"])
            self.assertEqual("resume", payload["approval"]["recommended_action"])

    def test_inspect_run_artifacts_should_inspect_when_fork_approval_is_mismatched(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            latest = root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15" / "latest.json"
            out_dir = root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15-run-15"
            _write_json(
                latest,
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "15",
                    "run_id": "run-15",
                    "status": "fail",
                    "latest_out_dir": str(out_dir),
                    "summary_path": str(out_dir / "summary.json"),
                    "execution_context_path": str(out_dir / "execution-context.json"),
                    "repair_guide_json_path": str(out_dir / "repair-guide.json"),
                },
            )
            _write_json(
                out_dir / "summary.json",
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "15",
                    "run_id": "run-15",
                    "status": "fail",
                    "reason": "review_pending",
                    "steps": [],
                },
            )
            _write_json(
                out_dir / "execution-context.json",
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "15",
                    "run_id": "run-15",
                    "status": "fail",
                    "delivery_profile": "fast-ship",
                    "security_profile": "host-safe",
                    "diagnostics": {},
                },
            )
            _write_json(
                out_dir / "approval-request.json",
                {
                    "schema_version": "1.0.0",
                    "request_id": "run-15:fork",
                    "task_id": "15",
                    "run_id": "run-15",
                    "action": "fork",
                    "reason": "Fork was requested.",
                    "requested_files": [],
                    "requested_commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 15 --fork"],
                    "status": "pending",
                },
            )
            _write_json(
                out_dir / "approval-response.json",
                {
                    "schema_version": "1.0.0",
                    "request_id": "wrong-run:fork",
                    "decision": "approved",
                    "reviewer": "human",
                    "reason": "Approved the wrong request.",
                },
            )
            _write_json(
                out_dir / "repair-guide.json",
                {
                    "status": "needs-fix",
                    "task_id": "15",
                    "summary_status": "fail",
                    "failed_step": "",
                    "recommendations": [],
                },
            )

            rc, payload = inspect_run.inspect_run_artifacts(repo_root=root, kind="pipeline", task_id="15")

            self.assertEqual(1, rc)
            self.assertEqual("inspect", payload["recommended_action"])
            self.assertEqual("inspect", payload["chapter6_hints"]["next_action"])
            self.assertEqual("approval_invalid", payload["chapter6_hints"]["blocked_by"])
            self.assertEqual("mismatched", payload["approval"]["status"])
            self.assertEqual("inspect", payload["approval"]["recommended_action"])
            self.assertIn("does not match", payload["recommended_action_why"])

    def test_derive_chapter6_hints_should_fallback_to_inspect_when_approval_contract_is_inconsistent(self) -> None:
        hints = inspect_run._derive_chapter6_hints(
            failure={"code": "review-needs-fix"},
            latest_summary_signals={"reason": "review_pending", "diagnostics_keys": []},
            recent_failure_summary={},
            approval={
                "required_action": "fork",
                "status": "pending",
                "recommended_action": "resume",
                "allowed_actions": ["pause"],
                "blocked_actions": ["resume"],
            },
        )

        self.assertEqual("inspect", hints["next_action"])
        self.assertEqual("approval_invalid", hints["blocked_by"])

    def test_inspect_run_artifacts_should_fallback_to_repair_guide_route_recommendation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            latest = root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15" / "latest.json"
            out_dir = root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15-run-15"
            _write_json(
                latest,
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "15",
                    "run_id": "run-15",
                    "status": "fail",
                    "latest_out_dir": str(out_dir),
                    "summary_path": str(out_dir / "summary.json"),
                    "execution_context_path": str(out_dir / "execution-context.json"),
                    "repair_guide_json_path": str(out_dir / "repair-guide.json"),
                },
            )
            _write_json(
                out_dir / "summary.json",
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "15",
                    "run_id": "run-15",
                    "status": "fail",
                    "reason": "rerun_blocked:chapter6_route_run_6_8",
                    "steps": [],
                    "latest_summary_signals": {
                        "reason": "rerun_blocked:chapter6_route_run_6_8",
                    },
                    "chapter6_hints": {
                        "next_action": "",
                        "blocked_by": "rerun_guard",
                    },
                },
            )
            _write_json(
                out_dir / "execution-context.json",
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "15",
                    "run_id": "run-15",
                    "status": "fail",
                    "delivery_profile": "fast-ship",
                    "security_profile": "host-safe",
                    "diagnostics": {
                        "rerun_guard": {
                            "kind": "chapter6_route_run_6_8",
                            "blocked": True,
                            "recommended_path": "run-6.8",
                        }
                    },
                },
            )
            _write_json(
                out_dir / "repair-guide.json",
                {
                    "status": "needs-fix",
                    "task_id": "15",
                    "summary_status": "fail",
                    "failed_step": "",
                    "recommendations": [
                        {
                            "id": "chapter6-route-run-6-8",
                            "title": "Use the narrow 6.8 lane instead of reopening a full 6.7 rerun",
                            "why": "The latest route already proved deterministic evidence is sufficient for this task. Continue with the targeted Needs Fix closure lane.",
                            "commands": [
                                "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 15 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1"
                            ],
                            "files": [],
                        }
                    ],
                },
            )

            rc, payload = inspect_run.inspect_run_artifacts(repo_root=root, kind="pipeline", task_id="15")

            self.assertEqual(1, rc)
            self.assertEqual("needs-fix-fast", payload["recommended_action"])
            self.assertEqual(
                "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 15 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
                payload["recommended_command"],
            )
            self.assertIn("deterministic evidence is sufficient", payload["recommended_action_why"].lower())

    def test_inspect_run_artifacts_should_surface_planned_only_recovery_hints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)

            latest = root / "logs" / "ci" / "2026-04-08" / "sc-review-pipeline-task-14" / "latest.json"
            out_dir = root / "logs" / "ci" / "2026-04-08" / "sc-review-pipeline-task-14-planned-run"
            _write_json(
                latest,
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": "planned-run",
                    "status": "ok",
                    "latest_out_dir": str(out_dir),
                    "summary_path": str(out_dir / "summary.json"),
                    "execution_context_path": str(out_dir / "execution-context.json"),
                    "repair_guide_json_path": str(out_dir / "repair-guide.json"),
                    "run_events_path": str(out_dir / "run-events.jsonl"),
                },
            )
            _write_json(
                out_dir / "summary.json",
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": "planned-run",
                    "status": "ok",
                    "run_type": "planned-only",
                    "reason": "pipeline_clean",
                    "steps": [
                        {"name": "sc-test", "status": "planned"},
                        {"name": "sc-acceptance-check", "status": "planned"},
                    ],
                    "finished_at_utc": "2026-04-08T10:00:00+00:00",
                },
            )
            _write_json(
                out_dir / "execution-context.json",
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": "planned-run",
                    "status": "ok",
                    "delivery_profile": "fast-ship",
                    "security_profile": "host-safe",
                    "diagnostics": {},
                },
            )
            _write_json(
                out_dir / "repair-guide.json",
                {
                    "status": "not-needed",
                    "task_id": "14",
                    "summary_status": "ok",
                    "failed_step": "",
                    "recommendations": [],
                },
            )
            (out_dir / "run-events.jsonl").write_text(
                json.dumps(
                    {
                        "event": "run_completed",
                        "task_id": "14",
                        "run_id": "planned-run",
                        "status": "ok",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
                newline="\n",
            )

            rc, payload = inspect_run.inspect_run_artifacts(repo_root=root, kind="pipeline", task_id="14")

            self.assertEqual(1, rc)
            self.assertEqual("fail", payload["status"])
            self.assertEqual("planned_only_incomplete", payload["latest_summary_signals"]["reason"])
            self.assertEqual("planned-only", payload["latest_summary_signals"]["run_type"])
            self.assertEqual("planned_only_incomplete", payload["latest_summary_signals"]["artifact_integrity_kind"])
            self.assertEqual("rerun", payload["chapter6_hints"]["next_action"])
            self.assertEqual("artifact_integrity", payload["chapter6_hints"]["blocked_by"])
            self.assertIn("planned-only evidence", payload["recommended_action_why"])
            self.assertIn("rerun 6.7", payload["recommended_action_why"])

    def test_resolve_latest_path_should_prefer_real_bundle_over_newer_dry_run_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)

            real_latest = root / "logs" / "ci" / "2026-04-07" / "sc-review-pipeline-task-14" / "latest.json"
            real_out_dir = root / "logs" / "ci" / "2026-04-07" / "sc-review-pipeline-task-14-real-run"
            _write_json(
                real_latest,
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": "real-run",
                    "status": "ok",
                    "latest_out_dir": str(real_out_dir),
                    "summary_path": str(real_out_dir / "summary.json"),
                },
            )
            _write_json(
                real_out_dir / "summary.json",
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": "real-run",
                    "status": "ok",
                    "run_type": "full",
                    "reason": "pipeline_clean",
                    "steps": [{"name": "sc-test", "status": "ok"}],
                    "finished_at_utc": "2026-04-07T10:00:00+00:00",
                },
            )

            dry_latest = root / "logs" / "ci" / "2026-04-08" / "sc-review-pipeline-task-14" / "latest.json"
            dry_out_dir = root / "logs" / "ci" / "2026-04-08" / "sc-review-pipeline-task-14-dry-run"
            _write_json(
                dry_latest,
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": "dry-run",
                    "status": "fail",
                    "latest_out_dir": str(dry_out_dir),
                    "summary_path": str(dry_out_dir / "summary.json"),
                },
            )
            _write_json(
                dry_out_dir / "summary.json",
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": "dry-run",
                    "status": "fail",
                    "run_type": "planned-only",
                    "reason": "planned_only_incomplete",
                    "steps": [
                        {"name": "sc-test", "status": "planned"},
                        {"name": "sc-acceptance-check", "status": "planned"},
                    ],
                    "finished_at_utc": "2026-04-08T10:00:00+00:00",
                },
            )

            os.utime(real_latest, (1712560000, 1712560000))
            os.utime(dry_latest, (1712646400, 1712646400))

            resolved = inspect_run._resolve_latest_path(root, latest="", kind="pipeline", task_id="14", run_id="")
            self.assertEqual(real_latest.resolve(), resolved)

    def test_render_recommendation_only_should_surface_compact_recovery_fields(self) -> None:
        payload = {
            "task_id": "15",
            "run_id": "run-15",
            "recommended_action": "needs-fix-fast",
            "recommended_command": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 15 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
            "forbidden_commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 15"],
            "recommended_action_why": "Deterministic evidence is already sufficient.",
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
            "failure": {
                "code": "review-needs-fix",
            },
        }

        text = inspect_run._render_recommendation_only(payload)

        self.assertIn("task_id=15", text)
        self.assertIn("run_id=run-15", text)
        self.assertIn("failure_code=review-needs-fix", text)
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

    def test_main_recommendation_only_should_print_compact_text(self) -> None:
        payload = {
            "task_id": "15",
            "run_id": "run-15",
            "recommended_action": "needs-fix-fast",
            "recommended_command": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 15 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
            "forbidden_commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 15"],
            "recommended_action_why": "Deterministic evidence is already sufficient.",
            "latest_summary_signals": {"reason": "rerun_blocked:repeat_review_needs_fix"},
            "chapter6_hints": {"next_action": "needs-fix-fast", "blocked_by": "rerun_guard"},
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
            "failure": {"code": "review-needs-fix"},
        }
        stdout = io.StringIO()
        argv = [
            "--repo-root",
            str(REPO_ROOT),
            "--kind",
            "pipeline",
            "--task-id",
            "15",
            "--recommendation-only",
        ]
        with (
            mock.patch.object(inspect_run, "inspect_run_artifacts", return_value=(1, payload)),
            mock.patch.object(sys, "argv", ["inspect_run.py", *argv]),
            redirect_stdout(stdout),
        ):
            rc = inspect_run.main()

        self.assertEqual(1, rc)
        output = stdout.getvalue()
        self.assertIn("task_id=15", output)
        self.assertIn("recommended_action=needs-fix-fast", output)
        self.assertIn("approval_recommended_action=pause", output)
        self.assertIn("latest_turn=run-15:turn-2", output)
        self.assertNotIn('"recommended_action": "needs-fix-fast"', output)

    def test_main_recommendation_only_json_should_print_compact_json(self) -> None:
        payload = {
            "task_id": "15",
            "run_id": "run-15",
            "recommended_action": "needs-fix-fast",
            "recommended_command": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 15 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
            "forbidden_commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 15"],
            "recommended_action_why": "Deterministic evidence is already sufficient.",
            "latest_summary_signals": {"reason": "rerun_blocked:repeat_review_needs_fix"},
            "chapter6_hints": {"next_action": "needs-fix-fast", "blocked_by": "rerun_guard"},
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
            "failure": {"code": "review-needs-fix"},
        }
        stdout = io.StringIO()
        argv = [
            "--repo-root",
            str(REPO_ROOT),
            "--kind",
            "pipeline",
            "--task-id",
            "15",
            "--recommendation-only",
            "--recommendation-format",
            "json",
        ]
        with (
            mock.patch.object(inspect_run, "inspect_run_artifacts", return_value=(1, payload)),
            mock.patch.object(sys, "argv", ["inspect_run.py", *argv]),
            redirect_stdout(stdout),
        ):
            rc = inspect_run.main()

        self.assertEqual(1, rc)
        compact = json.loads(stdout.getvalue())
        self.assertEqual("15", compact["task_id"])
        self.assertEqual("review-needs-fix", compact["failure_code"])
        self.assertEqual("rerun_guard", compact["blocked_by"])
        self.assertEqual("pause", compact["approval_recommended_action"])
        self.assertEqual("run-15:turn-2", compact["latest_turn"])


if __name__ == "__main__":
    unittest.main()
