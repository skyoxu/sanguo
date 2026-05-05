#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
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


ci_pipeline = _load_module("ci_pipeline_solution_resolution_module", "scripts/python/ci_pipeline.py")


class CiPipelineSolutionResolutionTests(unittest.TestCase):
    def test_all_should_resolve_test_solution_when_auto(self) -> None:
        commands: list[list[str]] = []

        def _fake_run_cmd(args, cwd=None, timeout=900_000):
            commands.append(list(args))
            if len(commands) == 1:
                return 0, "ok\n"
            if len(commands) == 2:
                return 0, "RUN_DOTNET status=ok line=90.0% branch=85.0 out=logs/unit/2026-04-08\n"
            if len(commands) == 3:
                return 0, "ok\n"
            if len(commands) == 4:
                return 0, "SELF_CHECK status=ok out=logs/e2e/2026-04-08/selfcheck\n"
            return 0, "ok\n"

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "templategame"
            root.mkdir(parents=True, exist_ok=True)
            argv = [
                "ci_pipeline.py",
                "all",
                "--solution",
                "auto",
                "--configuration",
                "Debug",
                "--godot-bin",
                "C:/Godot/Godot.exe",
            ]
            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(ci_pipeline.os, "getcwd", return_value=str(root)), \
                mock.patch.object(ci_pipeline, "resolve_test_solution_arg", return_value="Game.sln") as resolve_mock, \
                mock.patch.object(ci_pipeline, "run_cmd", side_effect=_fake_run_cmd), \
                mock.patch.object(ci_pipeline, "read_json", return_value={}), \
                mock.patch.object(ci_pipeline, "copy_if_exists", return_value=False):
                rc = ci_pipeline.main()

        self.assertEqual(0, rc)
        resolve_mock.assert_called_once_with("auto")
        dotnet_cmd = next(cmd for cmd in commands if cmd[:3] == ["py", "-3", "scripts/python/run_dotnet.py"])
        self.assertIn("--solution", dotnet_cmd)
        self.assertEqual("Game.sln", dotnet_cmd[dotnet_cmd.index("--solution") + 1])


if __name__ == "__main__":
    unittest.main()
