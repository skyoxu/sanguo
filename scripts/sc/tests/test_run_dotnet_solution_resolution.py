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


run_dotnet = _load_module("run_dotnet_test_module", "scripts/python/run_dotnet.py")


class RunDotnetSolutionResolutionTests(unittest.TestCase):
    def test_main_should_resolve_test_solution_when_auto(self) -> None:
        commands: list[list[str]] = []

        def _fake_run_cmd(args, cwd=None, timeout=900_000):
            commands.append(list(args))
            return 1, "restore failed\n"

        with tempfile.TemporaryDirectory(prefix="run-dotnet-", dir=str(REPO_ROOT)) as tmpdir:
            root = Path(tmpdir) / "sanguo"
            root.mkdir(parents=True, exist_ok=True)
            (root / "sanguo.sln").write_text("", encoding="utf-8")
            (root / "Game.sln").write_text(
                'Project("{x}") = "Game.Core.Tests", "Game.Core.Tests\\\\Game.Core.Tests.csproj", "{2}"\nEndProject\n',
                encoding="utf-8",
            )
            argv = ["run_dotnet.py", "--solution", "auto", "--configuration", "Debug"]
            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(run_dotnet.os, "getcwd", return_value=str(root)), \
                mock.patch.object(run_dotnet, "run_cmd", side_effect=_fake_run_cmd):
                rc = run_dotnet.main()

            self.assertEqual(1, rc)
            self.assertEqual(["dotnet", "restore", "Game.sln", "--property:RestoreBuildInParallel=false"], commands[0])
            summary = json.loads((root / "logs" / "unit" / run_dotnet.dt.date.today().strftime("%Y-%m-%d") / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("Game.sln", summary["solution"])

    def test_main_should_test_project_target_when_solution_contains_test_project(self) -> None:
        commands: list[list[str]] = []

        def _fake_run_cmd(args, cwd=None, timeout=900_000):
            commands.append(list(args))
            if args[:2] == ["dotnet", "restore"]:
                return 0, "restore ok\n"
            return 0, "test ok\n"

        with tempfile.TemporaryDirectory(prefix="run-dotnet-", dir=str(REPO_ROOT)) as tmpdir:
            root = Path(tmpdir) / "sanguo"
            root.mkdir(parents=True, exist_ok=True)
            (root / "Game.Core.Tests").mkdir(parents=True, exist_ok=True)
            (root / "Game.sln").write_text(
                'Project("{x}") = "Game.Core.Tests", "Game.Core.Tests\\\\Game.Core.Tests.csproj", "{2}"\nEndProject\n',
                encoding="utf-8",
            )
            (root / "Game.Core.Tests" / "Game.Core.Tests.csproj").write_text("<Project />\n", encoding="utf-8")
            argv = ["run_dotnet.py", "--solution", "Game.sln", "--configuration", "Debug", "--filter", "FullyQualifiedName~Task122"]
            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(run_dotnet.os, "getcwd", return_value=str(root)), \
                mock.patch.object(run_dotnet, "run_cmd", side_effect=_fake_run_cmd):
                rc = run_dotnet.main()

            self.assertEqual(0, rc)
            test_cmd = commands[1]
            self.assertEqual(["dotnet", "test", "Game.Core.Tests\\Game.Core.Tests.csproj"], test_cmd[:3])


if __name__ == "__main__":
    unittest.main()
