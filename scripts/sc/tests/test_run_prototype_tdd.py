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


prototype_tdd = _load_module("prototype_tdd_module", "scripts/python/run_prototype_tdd.py")


class RunPrototypeTddTests(unittest.TestCase):
    def test_red_stage_should_accept_failing_step_and_create_record(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-04-09" / "prototype-tdd-hud-loop-red"

            with mock.patch.object(prototype_tdd, "repo_root", return_value=root), \
                mock.patch.object(prototype_tdd, "today_str", return_value="2026-04-09"), \
                mock.patch.object(prototype_tdd, "run_cmd", return_value=(1, "expected red failure\n")):
                rc = prototype_tdd.main(
                    [
                        "--slug",
                        "hud-loop",
                        "--stage",
                        "red",
                        "--dotnet-target",
                        "Game.Core.Tests/Game.Core.Tests.csproj",
                        "--out-dir",
                        str(out_dir),
                    ]
                )

            self.assertEqual(0, rc)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("ok", summary["status"])
            self.assertEqual("fail", summary["expected"])
            self.assertTrue(summary["prototype_record"].endswith("docs/prototypes/2026-04-09-hud-loop.md"))
            self.assertEqual(1, len(summary["steps"]))
            self.assertEqual(1, summary["steps"][0]["rc"])
            record = root / "docs" / "prototypes" / "2026-04-09-hud-loop.md"
            self.assertTrue(record.exists())
            self.assertIn("# Prototype: hud-loop", record.read_text(encoding="utf-8"))

    def test_green_stage_should_fail_when_verification_is_still_red(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-04-09" / "prototype-tdd-hud-loop-green"

            with mock.patch.object(prototype_tdd, "repo_root", return_value=root), \
                mock.patch.object(prototype_tdd, "today_str", return_value="2026-04-09"), \
                mock.patch.object(prototype_tdd, "run_cmd", return_value=(1, "still failing\n")):
                rc = prototype_tdd.main(
                    [
                        "--slug",
                        "hud-loop",
                        "--stage",
                        "green",
                        "--dotnet-target",
                        "Game.Core.Tests/Game.Core.Tests.csproj",
                        "--out-dir",
                        str(out_dir),
                    ]
                )

            self.assertEqual(1, rc)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("unexpected_red", summary["status"])
            self.assertEqual("pass", summary["expected"])

    def test_create_record_only_should_not_require_checks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-04-09" / "prototype-tdd-ui-loop-red"

            with mock.patch.object(prototype_tdd, "repo_root", return_value=root), \
                mock.patch.object(prototype_tdd, "today_str", return_value="2026-04-09"):
                rc = prototype_tdd.main(
                    [
                        "--slug",
                        "ui-loop",
                        "--create-record-only",
                        "--out-dir",
                        str(out_dir),
                    ]
                )

            self.assertEqual(0, rc)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertTrue(summary["create_record_only"])
            self.assertEqual([], summary["steps"])


if __name__ == "__main__":
    unittest.main()
