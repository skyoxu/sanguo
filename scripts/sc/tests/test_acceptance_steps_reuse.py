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

import _acceptance_steps as acceptance_steps  # noqa: E402
from _step_result import StepResult  # noqa: E402
from _taskmaster import TaskmasterTriplet  # noqa: E402


class AcceptanceStepsReuseTests(unittest.TestCase):
    def test_step_tests_all_should_reuse_matching_sc_test_summary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-03-31" / "sc-acceptance-check-task-56"
            out_dir.mkdir(parents=True, exist_ok=True)
            sc_test_dir = root / "logs" / "ci" / "2026-03-31" / "sc-test"
            sc_test_dir.mkdir(parents=True, exist_ok=True)
            (sc_test_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "cmd": "sc-test",
                        "run_id": "rid-56",
                        "type": "unit",
                        "task_id": "56",
                        "status": "ok",
                        "steps": [
                            {
                                "name": "unit",
                                "status": "ok",
                                "rc": 0,
                                "log": str(sc_test_dir / "unit.log"),
                                "artifacts_dir": str(root / "logs" / "unit" / "2026-03-31"),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (sc_test_dir / "run_id.txt").write_text("rid-56\n", encoding="utf-8")

            with (
                mock.patch.object(acceptance_steps, "repo_root", return_value=root),
                mock.patch.object(acceptance_steps, "today_str", return_value="2026-03-31"),
                mock.patch.object(acceptance_steps, "run_and_capture") as run_and_capture_mock,
            ):
                step = acceptance_steps.step_tests_all(
                    out_dir,
                    godot_bin=None,
                    run_id="rid-56",
                    test_type="unit",
                    task_id="56",
                )

            self.assertEqual("ok", step.status)
            self.assertEqual(0, int(step.rc or 0))
            self.assertTrue(bool((step.details or {}).get("reused")))
            self.assertEqual(str(sc_test_dir / "summary.json"), (step.details or {}).get("source_summary_file"))
            self.assertEqual(str(out_dir / "tests-all.log"), step.log)
            self.assertIn("SC_TEST status=ok", (out_dir / "tests-all.log").read_text(encoding="utf-8"))
            run_and_capture_mock.assert_not_called()

    def test_step_tests_all_should_fall_back_to_subprocess_when_run_id_mismatches(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-03-31" / "sc-acceptance-check-task-56"
            out_dir.mkdir(parents=True, exist_ok=True)
            sc_test_dir = root / "logs" / "ci" / "2026-03-31" / "sc-test"
            sc_test_dir.mkdir(parents=True, exist_ok=True)
            (sc_test_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "cmd": "sc-test",
                        "run_id": "other-run",
                        "type": "unit",
                        "task_id": "56",
                        "status": "ok",
                        "steps": [],
                    }
                ),
                encoding="utf-8",
            )
            (sc_test_dir / "run_id.txt").write_text("other-run\n", encoding="utf-8")

            expected = StepResult(name="tests-all", status="ok", rc=0, cmd=["py", "-3", "scripts/sc/test.py"])
            with (
                mock.patch.object(acceptance_steps, "repo_root", return_value=root),
                mock.patch.object(acceptance_steps, "today_str", return_value="2026-03-31"),
                mock.patch.object(acceptance_steps, "run_and_capture", return_value=expected) as run_and_capture_mock,
            ):
                step = acceptance_steps.step_tests_all(
                    out_dir,
                    godot_bin=None,
                    run_id="rid-56",
                    test_type="unit",
                    task_id="56",
                )

            self.assertEqual(expected, step)
            run_and_capture_mock.assert_called_once()

    def test_step_overlay_validate_should_scope_validate_task_overlays_to_current_task(self) -> None:
        triplet = TaskmasterTriplet(
            task_id="56",
            master={"id": "56", "overlay": "docs/architecture/overlays/PRD-NEWROUGE-GAME-0001/08/_index.md"},
            back={"taskmaster_id": 56},
            gameplay={"taskmaster_id": 56},
            tasks_json_path=".taskmaster/tasks/tasks.json",
            tasks_back_path=".taskmaster/tasks/tasks_back.json",
            tasks_gameplay_path=".taskmaster/tasks/tasks_gameplay.json",
            taskdoc_path=None,
        )
        calls: list[list[str]] = []

        def _fake_run_and_capture(_out_dir: Path, name: str, cmd: list[str], timeout_sec: int) -> StepResult:
            calls.append(cmd)
            return StepResult(name=name, status="ok", rc=0, cmd=cmd, log=f"fake/{name}.log")

        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            with mock.patch.object(acceptance_steps, "run_and_capture", side_effect=_fake_run_and_capture):
                step = acceptance_steps.step_overlay_validate(out_dir, triplet)

        self.assertEqual("ok", step.status)
        validate_cmds = [cmd for cmd in calls if "validate_task_overlays.py" in " ".join(cmd)]
        self.assertEqual(3, len(validate_cmds))
        for cmd in validate_cmds:
            self.assertIn("--task-id", cmd)
            self.assertIn("56", cmd)
            self.assertIn("--task-file", cmd)


if __name__ == "__main__":
    unittest.main()
