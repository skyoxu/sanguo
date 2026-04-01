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


if __name__ == "__main__":
    unittest.main()
