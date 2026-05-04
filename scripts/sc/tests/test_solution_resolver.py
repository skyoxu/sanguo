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


solution_resolver = _load_module("solution_resolver_test_module", "scripts/python/solution_resolver.py")


class SolutionResolverTests(unittest.TestCase):
    def test_auto_should_prefer_repo_named_solution_for_general_builds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="repo-") as tmpdir:
            root = Path(tmpdir) / "templategame"
            root.mkdir(parents=True, exist_ok=True)
            (root / "templategame.sln").write_text("", encoding="utf-8")
            (root / "Game.sln").write_text(
                'Project("{x}") = "Game.Core.Tests", "Game.Core.Tests\\\\Game.Core.Tests.csproj", "{2}"\nEndProject\n',
                encoding="utf-8",
            )

            resolved = solution_resolver.resolve_solution_path("auto", repo_root=root)

        self.assertEqual("templategame.sln", resolved)

    def test_auto_should_prefer_test_bearing_solution_for_test_entrypoints(self) -> None:
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

            resolved = solution_resolver.resolve_test_solution_path("auto", repo_root=root)

        self.assertEqual("Game.sln", resolved)


if __name__ == "__main__":
    unittest.main()
