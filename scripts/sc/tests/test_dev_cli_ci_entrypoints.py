#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
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


dev_cli = _load_module("dev_cli_ci_module", "scripts/python/dev_cli.py")


class DevCliCiEntrypointsTests(unittest.TestCase):
    def test_run_ci_basic_should_delegate_to_gate_bundle_hard_mode_by_default(self) -> None:
        with mock.patch.object(dev_cli, "run", return_value=0) as run_mock:
            rc = dev_cli.main(["run-ci-basic"])

        self.assertEqual(0, rc)
        run_mock.assert_called_once()
        cmd = run_mock.call_args[0][0]
        self.assertEqual(["py", "-3", "scripts/python/run_gate_bundle.py"], cmd[:3])
        self.assertIn("--mode", cmd)
        self.assertIn("hard", cmd)
        self.assertIn("--task-files", cmd)
        self.assertIn(".taskmaster/tasks/tasks_back.json", cmd)
        self.assertIn(".taskmaster/tasks/tasks_gameplay.json", cmd)
        self.assertNotIn("scripts/python/ci_pipeline.py", cmd)

    def test_run_ci_basic_should_forward_gate_bundle_runtime_options(self) -> None:
        with mock.patch.object(dev_cli, "run", return_value=0) as run_mock:
            rc = dev_cli.main(
                [
                    "run-ci-basic",
                    "--delivery-profile",
                    "standard",
                    "--run-id",
                    "local-demo",
                    "--out-dir",
                    "logs/ci/demo/gate-bundle",
                    "--task-file",
                    "custom/tasks_back.json",
                    "--task-file",
                    "custom/tasks_gameplay.json",
                ]
            )

        self.assertEqual(0, rc)
        cmd = run_mock.call_args[0][0]
        self.assertIn("--delivery-profile", cmd)
        self.assertIn("standard", cmd)
        self.assertIn("--run-id", cmd)
        self.assertIn("local-demo", cmd)
        self.assertIn("--out-dir", cmd)
        self.assertIn("logs/ci/demo/gate-bundle", cmd)
        task_files_index = cmd.index("--task-files")
        self.assertEqual(
            ["custom/tasks_back.json", "custom/tasks_gameplay.json"],
            cmd[task_files_index + 1 : task_files_index + 3],
        )

    def test_run_ci_basic_should_optionally_append_legacy_preflight(self) -> None:
        with mock.patch.object(dev_cli, "run", side_effect=[0, 0]) as run_mock:
            rc = dev_cli.main(
                [
                    "run-ci-basic",
                    "--legacy-preflight",
                    "--godot-bin",
                    "C:/Godot/Godot.exe",
                    "--solution",
                    "Game.sln",
                    "--configuration",
                    "Release",
                ]
            )

        self.assertEqual(0, rc)
        self.assertEqual(2, run_mock.call_count)

        bundle_cmd = run_mock.call_args_list[0][0][0]
        legacy_cmd = run_mock.call_args_list[1][0][0]

        self.assertEqual(["py", "-3", "scripts/python/run_gate_bundle.py"], bundle_cmd[:3])
        self.assertEqual(["py", "-3", "scripts/python/ci_pipeline.py"], legacy_cmd[:3])
        self.assertIn("--godot-bin", legacy_cmd)
        self.assertIn("C:/Godot/Godot.exe", legacy_cmd)
        self.assertIn("--solution", legacy_cmd)
        self.assertIn("Game.sln", legacy_cmd)
        self.assertIn("--configuration", legacy_cmd)
        self.assertIn("Release", legacy_cmd)

    def test_run_quality_gates_should_delegate_to_quality_gates_entrypoint(self) -> None:
        with mock.patch.object(dev_cli, "run", return_value=0) as run_mock:
            rc = dev_cli.main(
                [
                    "run-quality-gates",
                    "--delivery-profile",
                    "standard",
                    "--run-id",
                    "local-demo",
                    "--out-dir",
                    "logs/ci/demo/gate-bundle",
                    "--task-file",
                    "custom/tasks_back.json",
                    "--task-file",
                    "custom/tasks_gameplay.json",
                ]
            )

        self.assertEqual(0, rc)
        cmd = run_mock.call_args[0][0]
        self.assertEqual(["py", "-3", "scripts/python/quality_gates.py"], cmd[:3])
        self.assertIn("--delivery-profile", cmd)
        self.assertIn("standard", cmd)
        self.assertIn("--run-id", cmd)
        self.assertIn("local-demo", cmd)
        self.assertIn("--out-dir", cmd)
        self.assertIn("logs/ci/demo/gate-bundle", cmd)
        task_files_index = cmd.index("--task-file")
        self.assertEqual("custom/tasks_back.json", cmd[task_files_index + 1])
        self.assertEqual("--task-file", cmd[task_files_index + 2])
        self.assertEqual("custom/tasks_gameplay.json", cmd[task_files_index + 3])
        self.assertNotIn("--godot-bin", cmd)

    def test_run_quality_gates_should_forward_optional_godot_steps(self) -> None:
        with mock.patch.object(dev_cli, "run", return_value=0) as run_mock:
            rc = dev_cli.main(
                [
                    "run-quality-gates",
                    "--gdunit-hard",
                    "--smoke",
                    "--godot-bin",
                    "C:/Godot/Godot.exe",
                ]
            )

        self.assertEqual(0, rc)
        cmd = run_mock.call_args[0][0]
        self.assertIn("--gdunit-hard", cmd)
        self.assertIn("--smoke", cmd)
        self.assertIn("--godot-bin", cmd)
        self.assertIn("C:/Godot/Godot.exe", cmd)

    def test_run_local_hard_checks_should_delegate_to_protocol_harness(self) -> None:
        with mock.patch.object(dev_cli, "run_local_hard_checks", create=True, return_value=0) as harness_mock, \
            mock.patch.object(dev_cli, "run") as run_mock:
            rc = dev_cli.main(
                [
                    "run-local-hard-checks",
                    "--godot-bin",
                    "C:/Godot/Godot.exe",
                    "--delivery-profile",
                    "standard",
                    "--run-id",
                    "local-demo",
                    "--out-dir",
                    "logs/ci/demo/local-hard-checks",
                    "--task-file",
                    "custom/tasks_back.json",
                    "--task-file",
                    "custom/tasks_gameplay.json",
                ]
            )

        self.assertEqual(0, rc)
        run_mock.assert_not_called()
        harness_mock.assert_called_once_with(
            solution=dev_cli.resolve_test_solution_path("auto"),
            configuration="Debug",
            godot_bin="C:/Godot/Godot.exe",
            delivery_profile="standard",
            task_files=["custom/tasks_back.json", "custom/tasks_gameplay.json"],
            out_dir="logs/ci/demo/local-hard-checks",
            run_id="local-demo",
            timeout_sec=5,
            run_fn=run_mock,
        )

    def test_run_local_hard_checks_should_return_harness_failure_code(self) -> None:
        with mock.patch.object(dev_cli, "run_local_hard_checks", create=True, return_value=7) as harness_mock:
            rc = dev_cli.main(["run-local-hard-checks"])

        self.assertEqual(7, rc)
        harness_mock.assert_called_once_with(
            solution=dev_cli.resolve_test_solution_path("auto"),
            configuration="Debug",
            godot_bin="",
            delivery_profile="",
            task_files=dev_cli.DEFAULT_GATE_BUNDLE_TASK_FILES,
            out_dir="",
            run_id="",
            timeout_sec=5,
            run_fn=dev_cli.run,
        )

    def test_run_local_hard_checks_preflight_should_run_gate_bundle_then_dotnet(self) -> None:
        with mock.patch.object(dev_cli, "run", side_effect=[0, 0]) as run_mock:
            rc = dev_cli.main(
                [
                    "run-local-hard-checks-preflight",
                    "--solution",
                    "Game.sln",
                    "--configuration",
                    "Release",
                    "--delivery-profile",
                    "fast-ship",
                    "--run-id",
                    "preflight-demo",
                    "--out-dir",
                    "logs/ci/demo/local-hard-checks-preflight",
                    "--task-file",
                    "custom/tasks_back.json",
                    "--task-file",
                    "custom/tasks_gameplay.json",
                ]
            )

        self.assertEqual(0, rc)
        self.assertEqual(2, run_mock.call_count)
        gate_cmd = run_mock.call_args_list[0][0][0]
        dotnet_cmd = run_mock.call_args_list[1][0][0]

        self.assertEqual(["py", "-3", "scripts/python/run_gate_bundle.py"], gate_cmd[:3])
        self.assertIn("--mode", gate_cmd)
        self.assertIn("hard", gate_cmd)
        self.assertIn("--delivery-profile", gate_cmd)
        self.assertIn("fast-ship", gate_cmd)
        self.assertIn("--task-files", gate_cmd)
        self.assertIn("--run-id", gate_cmd)
        self.assertIn("preflight-demo", gate_cmd)
        self.assertIn("--out-dir", gate_cmd)
        self.assertIn("logs/ci/demo/local-hard-checks-preflight", gate_cmd)

        self.assertEqual(["py", "-3", "scripts/python/run_dotnet.py"], dotnet_cmd[:3])
        self.assertIn("--solution", dotnet_cmd)
        self.assertIn("Game.sln", dotnet_cmd)
        self.assertIn("--configuration", dotnet_cmd)
        self.assertIn("Release", dotnet_cmd)

    def test_run_local_hard_checks_preflight_should_stop_when_gate_bundle_fails(self) -> None:
        with mock.patch.object(dev_cli, "run", side_effect=[3]) as run_mock:
            rc = dev_cli.main(["run-local-hard-checks-preflight"])

        self.assertEqual(3, rc)
        self.assertEqual(1, run_mock.call_count)

    def test_run_acceptance_preflight_should_run_refs_then_anchors(self) -> None:
        with mock.patch.object(dev_cli, "run", side_effect=[0, 0]) as run_mock:
            rc = dev_cli.main(
                [
                    "run-acceptance-preflight",
                    "--task-id",
                    "11",
                    "--stage",
                    "refactor",
                    "--out-dir",
                    "logs/ci/demo/acceptance-preflight",
                ]
            )

        self.assertEqual(0, rc)
        self.assertEqual(2, run_mock.call_count)

        refs_cmd = run_mock.call_args_list[0][0][0]
        anchors_cmd = run_mock.call_args_list[1][0][0]

        self.assertEqual(["py", "-3", "scripts/python/validate_acceptance_refs.py"], refs_cmd[:3])
        self.assertIn("--task-id", refs_cmd)
        self.assertIn("11", refs_cmd)
        self.assertIn("--stage", refs_cmd)
        self.assertIn("refactor", refs_cmd)
        self.assertIn("--out", refs_cmd)
        self.assertIn("logs/ci/demo/acceptance-preflight/acceptance-refs.json", refs_cmd)

        self.assertEqual(["py", "-3", "scripts/python/validate_acceptance_anchors.py"], anchors_cmd[:3])
        self.assertIn("--task-id", anchors_cmd)
        self.assertIn("11", anchors_cmd)
        self.assertIn("--stage", anchors_cmd)
        self.assertIn("refactor", anchors_cmd)
        self.assertIn("--out", anchors_cmd)
        self.assertIn("logs/ci/demo/acceptance-preflight/acceptance-anchors.json", anchors_cmd)

    def test_run_acceptance_preflight_should_stop_when_refs_fail(self) -> None:
        with mock.patch.object(dev_cli, "run", side_effect=[5]) as run_mock:
            rc = dev_cli.main(["run-acceptance-preflight", "--task-id", "11"])

        self.assertEqual(5, rc)
        self.assertEqual(1, run_mock.call_count)

    def test_run_smoke_strict_should_use_current_smoke_headless_args(self) -> None:
        with mock.patch.object(dev_cli, "run", return_value=0) as run_mock:
            rc = dev_cli.main(
                [
                    "run-smoke-strict",
                    "--godot-bin",
                    "C:/Godot/Godot.exe",
                    "--timeout-sec",
                    "7",
                ]
            )

        self.assertEqual(0, rc)
        cmd = run_mock.call_args[0][0]
        self.assertEqual(["py", "-3", "scripts/python/smoke_headless.py"], cmd[:3])
        self.assertIn("--project-path", cmd)
        self.assertIn(".", cmd)
        self.assertIn("--scene", cmd)
        self.assertIn("res://Game.Godot/Scenes/Main.tscn", cmd)
        self.assertIn("--timeout-sec", cmd)
        self.assertIn("7", cmd)
        self.assertIn("--strict", cmd)
        self.assertNotIn("--project", cmd)
        self.assertNotIn("--mode", cmd)


if __name__ == "__main__":
    unittest.main()
