#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON_DIR = REPO_ROOT / "scripts" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from solution_resolver import resolve_solution_path  # noqa: E402


class SolutionResolverTests(unittest.TestCase):
    def test_explicit_existing_solution_should_be_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Custom.sln").write_text("stub", encoding="utf-8")
            resolved = resolve_solution_path("Custom.sln", repo_root=root)
            self.assertEqual("Custom.sln", resolved)

    def test_auto_should_prefer_repo_name_then_godotgame_then_game(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Game.sln").write_text("stub", encoding="utf-8")
            (root / "GodotGame.sln").write_text("stub", encoding="utf-8")
            (root / f"{root.name}.sln").write_text("stub", encoding="utf-8")
            resolved = resolve_solution_path("auto", repo_root=root)
            self.assertEqual(f"{root.name}.sln", resolved)

    def test_auto_should_fallback_to_first_solution_when_no_preferred(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "A.sln").write_text("stub", encoding="utf-8")
            (root / "Z.sln").write_text("stub", encoding="utf-8")
            resolved = resolve_solution_path("auto", repo_root=root)
            self.assertEqual("A.sln", resolved)


if __name__ == "__main__":
    unittest.main()

