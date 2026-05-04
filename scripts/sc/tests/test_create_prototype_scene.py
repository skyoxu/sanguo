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


prototype_scene = _load_module("prototype_scene_module", "scripts/python/create_prototype_scene.py")


class CreatePrototypeSceneTests(unittest.TestCase):
    def test_should_create_scene_and_script_scaffold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rc = prototype_scene.main(
                [
                    "--repo-root",
                    str(root),
                    "--slug",
                    "combat-loop",
                ]
            )

            self.assertEqual(0, rc)
            scene_path = root / "Game.Godot" / "Prototypes" / "combat-loop" / "CombatLoopPrototype.tscn"
            script_path = root / "Game.Godot" / "Prototypes" / "combat-loop" / "Scripts" / "CombatLoopPrototype.cs"
            assets_dir = root / "Game.Godot" / "Prototypes" / "combat-loop" / "Assets"

            self.assertTrue(scene_path.exists())
            self.assertTrue(script_path.exists())
            self.assertTrue(assets_dir.is_dir())

            scene_text = scene_path.read_text(encoding="utf-8")
            script_text = script_path.read_text(encoding="utf-8")
            self.assertIn('type="Control"', scene_text)
            self.assertIn('res://Game.Godot/Prototypes/combat-loop/Scripts/CombatLoopPrototype.cs', scene_text)
            self.assertIn("public partial class CombatLoopPrototype : Control", script_text)

    def test_should_fail_when_scene_exists_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = prototype_scene.main(
                [
                    "--repo-root",
                    str(root),
                    "--slug",
                    "combat-loop",
                ]
            )
            second = prototype_scene.main(
                [
                    "--repo-root",
                    str(root),
                    "--slug",
                    "combat-loop",
                ]
            )

            self.assertEqual(0, first)
            self.assertEqual(1, second)


if __name__ == "__main__":
    unittest.main()
