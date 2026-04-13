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


dev_cli = _load_module("dev_cli_prototype_module", "scripts/python/dev_cli.py")


class DevCliPrototypeCommandsTests(unittest.TestCase):
    def test_run_prototype_tdd_should_forward_arguments(self) -> None:
        with mock.patch.object(dev_cli, "run", return_value=0) as run_mock:
            rc = dev_cli.main(
                [
                    "run-prototype-tdd",
                    "--slug",
                    "hud-loop",
                    "--stage",
                    "red",
                    "--dotnet-target",
                    "Game.Core.Tests/Game.Core.Tests.csproj",
                    "--filter",
                    "HUDLoop",
                    "--scope-in",
                    "HUD tick loop",
                    "--success-criteria",
                    "A failing test proves the loop is not implemented yet.",
                    "--out-dir",
                    "logs/ci/demo/prototype-hud-loop",
                ]
            )

        self.assertEqual(0, rc)
        cmd = run_mock.call_args[0][0]
        self.assertEqual(["py", "-3", "scripts/python/run_prototype_tdd.py"], cmd[:3])
        self.assertIn("--slug", cmd)
        self.assertIn("hud-loop", cmd)
        self.assertIn("--stage", cmd)
        self.assertIn("red", cmd)
        self.assertIn("--dotnet-target", cmd)
        self.assertIn("Game.Core.Tests/Game.Core.Tests.csproj", cmd)
        self.assertIn("--filter", cmd)
        self.assertIn("HUDLoop", cmd)
        self.assertIn("--scope-in", cmd)
        self.assertIn("HUD tick loop", cmd)
        self.assertIn("--success-criteria", cmd)
        self.assertIn("A failing test proves the loop is not implemented yet.", cmd)
        self.assertIn("--out-dir", cmd)
        self.assertIn("logs/ci/demo/prototype-hud-loop", cmd)


if __name__ == "__main__":
    unittest.main()
