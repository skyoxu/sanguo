#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


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


solution_target = _load_module("solution_target_module", "scripts/python/solution_target.py")


class SolutionTargetTests(unittest.TestCase):
    def test_explicit_solution_should_be_preserved(self) -> None:
        resolved = solution_target.resolve_solution_arg("Game.sln", root=Path(tempfile.gettempdir()))
        self.assertEqual("Game.sln", resolved)

    def test_auto_should_prefer_repo_name_solution(self) -> None:
        with tempfile.TemporaryDirectory(prefix="repo-") as tmpdir:
            root = Path(tmpdir) / "templategame"
            root.mkdir(parents=True, exist_ok=True)
            (root / "templategame.sln").write_text("", encoding="utf-8")
            (root / "Game.sln").write_text("", encoding="utf-8")
            resolved = solution_target.resolve_solution_arg("", root=root)
            self.assertEqual("templategame.sln", resolved)

    def test_auto_should_fallback_to_game_sln(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sample-") as tmpdir:
            root = Path(tmpdir)
            (root / "Game.sln").write_text("", encoding="utf-8")
            resolved = solution_target.resolve_solution_arg("auto", root=root)
            self.assertEqual("Game.sln", resolved)

    def test_test_auto_should_prefer_solution_with_test_projects(self) -> None:
        with tempfile.TemporaryDirectory(prefix="repo-") as tmpdir:
            root = Path(tmpdir) / "templategame"
            root.mkdir(parents=True, exist_ok=True)
            (root / "templategame.sln").write_text(
                'Project("{x}") = "templategame", "templategame.csproj", "{1}"\nEndProject\n',
                encoding="utf-8",
            )
            (root / "Game.sln").write_text(
                'Project("{x}") = "Game.Core.Tests", "Game.Core.Tests\\\\Game.Core.Tests.csproj", "{2}"\nEndProject\n',
                encoding="utf-8",
            )
            resolved = solution_target.resolve_test_solution_arg("auto", root=root)
            self.assertEqual("Game.sln", resolved)

    def test_test_auto_should_fallback_to_normal_resolution_without_test_projects(self) -> None:
        with tempfile.TemporaryDirectory(prefix="repo-") as tmpdir:
            root = Path(tmpdir) / "templategame"
            root.mkdir(parents=True, exist_ok=True)
            (root / "templategame.sln").write_text("", encoding="utf-8")
            (root / "Game.sln").write_text("", encoding="utf-8")
            resolved = solution_target.resolve_test_solution_arg("auto", root=root)
            self.assertEqual("templategame.sln", resolved)

    def test_auto_should_use_first_solution_when_no_preferred_name(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sample-") as tmpdir:
            root = Path(tmpdir)
            (root / "Alpha.sln").write_text("", encoding="utf-8")
            (root / "Zeta.sln").write_text("", encoding="utf-8")
            resolved = solution_target.resolve_solution_arg("", root=root)
            self.assertEqual("Alpha.sln", resolved)


if __name__ == "__main__":
    unittest.main()
