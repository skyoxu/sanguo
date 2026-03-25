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


local_hard_checks_harness = _load_module(
    "local_hard_checks_harness_test_module",
    "scripts/python/local_hard_checks_harness.py",
)


class LocalHardChecksHarnessTests(unittest.TestCase):
    def test_run_without_godot_bin_should_write_protocol_sidecars_and_two_steps(self) -> None:
        commands: list[list[str]] = []

        def runner(cmd: list[str]) -> int:
            commands.append(list(cmd))
            return 0

        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "local-hard-checks-demo"
            rc = local_hard_checks_harness.run_local_hard_checks(
                delivery_profile="standard",
                run_id="local-demo",
                out_dir=str(out_dir),
                run_fn=runner,
            )

            self.assertEqual(0, rc)
            self.assertEqual(3, len(commands))
            self.assertEqual(["py", "-3", "scripts/python/project_health_scan.py"], commands[0][:3])
            self.assertEqual(["py", "-3", "scripts/python/run_gate_bundle.py"], commands[1][:3])
            self.assertEqual(["py", "-3", "scripts/python/run_dotnet.py"], commands[2][:3])

            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            execution_context = json.loads((out_dir / "execution-context.json").read_text(encoding="utf-8"))
            repair_guide = json.loads((out_dir / "repair-guide.json").read_text(encoding="utf-8"))
            capabilities = json.loads((out_dir / "harness-capabilities.json").read_text(encoding="utf-8"))
            latest = json.loads((out_dir.parent / "local-hard-checks-latest.json").read_text(encoding="utf-8"))
            events = [
                json.loads(line)
                for line in (out_dir / "run-events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

            self.assertEqual("ok", summary["status"])
            self.assertEqual("", summary["failed_step"])
            self.assertEqual(
                ["project-health-scan", "gate-bundle-hard", "run-dotnet"],
                [item["name"] for item in summary["steps"]],
            )
            self.assertEqual("standard", execution_context["delivery_profile"])
            self.assertEqual("strict", execution_context["security_profile"])
            self.assertEqual("ok", repair_guide["status"])
            self.assertEqual("local-demo", capabilities["run_id"])
            self.assertEqual("repo", capabilities["task_id"])
            self.assertIn("run-events.jsonl", capabilities["supported_sidecars"])
            self.assertNotIn("approval-request.json", capabilities["supported_sidecars"])
            self.assertEqual("ok", latest["status"])
            self.assertEqual("run_started", events[0]["event"])
            self.assertEqual("run_completed", events[-1]["event"])

            for name in (
                "summary.json",
                "execution-context.json",
                "repair-guide.json",
                "repair-guide.md",
                "run-events.jsonl",
                "harness-capabilities.json",
                "run_id.txt",
            ):
                self.assertTrue((out_dir / name).exists(), name)

    def test_run_with_godot_bin_should_append_engine_steps(self) -> None:
        commands: list[list[str]] = []

        def runner(cmd: list[str]) -> int:
            commands.append(list(cmd))
            return 0

        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "local-hard-checks-demo"
            rc = local_hard_checks_harness.run_local_hard_checks(
                delivery_profile="fast-ship",
                run_id="local-demo",
                out_dir=str(out_dir),
                godot_bin="C:/Godot/Godot.exe",
                timeout_sec=7,
                run_fn=runner,
            )

            self.assertEqual(0, rc)
            self.assertEqual(5, len(commands))
            self.assertEqual(
                ["project-health-scan", "gate-bundle-hard", "run-dotnet", "gdunit-hard", "smoke-strict"],
                [item["name"] for item in json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))["steps"]],
            )
            self.assertIn("--godot-bin", commands[3])
            self.assertIn("C:/Godot/Godot.exe", commands[3])
            self.assertIn("--strict", commands[4])
            self.assertIn("--timeout-sec", commands[4])
            self.assertIn("7", commands[4])

    def test_project_health_fail_should_stop_before_other_hard_checks(self) -> None:
        commands: list[list[str]] = []

        def runner(cmd: list[str]) -> int:
            commands.append(list(cmd))
            return 9 if len(commands) == 1 else 0

        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "local-hard-checks-demo"
            rc = local_hard_checks_harness.run_local_hard_checks(
                delivery_profile="standard",
                run_id="local-demo",
                out_dir=str(out_dir),
                run_fn=runner,
            )

            self.assertEqual(9, rc)
            self.assertEqual(1, len(commands))
            self.assertEqual(["py", "-3", "scripts/python/project_health_scan.py"], commands[0][:3])
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("fail", summary["status"])
            self.assertEqual("project-health-scan", summary["failed_step"])

    def test_failure_should_stop_at_first_failed_step_and_write_failed_latest(self) -> None:
        commands: list[list[str]] = []
        rc_by_index = [0, 0, 7, 0, 0]

        def runner(cmd: list[str]) -> int:
            commands.append(list(cmd))
            return rc_by_index[len(commands) - 1]

        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "local-hard-checks-demo"
            rc = local_hard_checks_harness.run_local_hard_checks(
                delivery_profile="standard",
                run_id="local-demo",
                out_dir=str(out_dir),
                godot_bin="C:/Godot/Godot.exe",
                run_fn=runner,
            )

            self.assertEqual(7, rc)
            self.assertEqual(3, len(commands))

            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            latest = json.loads((out_dir.parent / "local-hard-checks-latest.json").read_text(encoding="utf-8"))
            events = [
                json.loads(line)
                for line in (out_dir / "run-events.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

            self.assertEqual("fail", summary["status"])
            self.assertEqual("run-dotnet", summary["failed_step"])
            self.assertEqual(
                ["project-health-scan", "gate-bundle-hard", "run-dotnet"],
                [item["name"] for item in summary["steps"]],
            )
            self.assertEqual("fail", latest["status"])
            self.assertEqual("run_failed", events[-1]["event"])
            self.assertEqual("fail", events[-1]["status"])
            self.assertFalse((out_dir / "gdunit-hard.log").exists())
            self.assertFalse((out_dir / "smoke-strict.log").exists())

    def test_invalid_summary_should_write_invalid_payload_and_return_two(self) -> None:
        def runner(cmd: list[str]) -> int:
            return 0

        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "local-hard-checks-demo"
            with mock.patch.object(
                local_hard_checks_harness,
                "validate_local_hard_checks_summary",
                side_effect=local_hard_checks_harness.SummarySchemaError("schema fail"),
            ):
                rc = local_hard_checks_harness.run_local_hard_checks(
                    delivery_profile="standard",
                    run_id="local-demo",
                    out_dir=str(out_dir),
                    run_fn=runner,
                )

            self.assertEqual(2, rc)
            self.assertFalse((out_dir / "summary.json").exists())
            self.assertTrue((out_dir / "summary.invalid.json").exists())
            self.assertTrue((out_dir / "summary-schema-validation-error.log").exists())
            self.assertFalse((out_dir / "execution-context.json").exists())
            self.assertFalse((out_dir / "repair-guide.json").exists())

            latest = json.loads((out_dir.parent / "local-hard-checks-latest.json").read_text(encoding="utf-8"))
            self.assertEqual("fail", latest["status"])


if __name__ == "__main__":
    unittest.main()
