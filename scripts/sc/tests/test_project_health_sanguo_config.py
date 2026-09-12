#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PYTHON_DIR = ROOT / "scripts" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from project_health_knowledge import load_config, validate_config


class ProjectHealthSanguoConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.path = ROOT / "scripts/python/project_health_knowledge_config.json"
        self.config = json.loads(self.path.read_text(encoding="utf-8"))

    def test_repository_config_is_the_effective_project_health_config(self) -> None:
        self.assertEqual(load_config(ROOT), self.config)
        self.assertEqual(validate_config(ROOT, self.config), self.config)

    def test_task_scene_bindings_are_real_sanguo_surfaces(self) -> None:
        bindings = self.config.get("task_scene_bindings", [])
        self.assertTrue(bindings)
        for binding in bindings:
            scene = ROOT / binding["scene"]
            script = ROOT / binding["script"]
            self.assertTrue(scene.is_file(), binding["scene"])
            self.assertTrue(script.is_file(), binding["script"])
            scene_text = scene.read_text(encoding="utf-8")
            script_text = script.read_text(encoding="utf-8")
            self.assertIn("res://" + binding["script"], scene_text)
            self.assertIn(binding["witness"], script_text)

    def test_default_binding_uses_task_192_main_menu_not_newrouge_reward(self) -> None:
        binding = self.config["task_scene_bindings"][0]
        self.assertEqual(binding["task_id"], 192)
        self.assertEqual(binding["scene"], "Game.Godot/Scenes/UI/Task192MainMenuSurface.tscn")
        self.assertNotIn("Reward", json.dumps(self.config, ensure_ascii=False))

    def test_query_aliases_cover_sanguo_navigation_terms(self) -> None:
        aliases = self.config["query_aliases"]
        self.assertIn("MainMenu", aliases["主菜单"])
        self.assertIn("SanguoBattle", aliases["战斗"])
        self.assertIn("Sanguo", aliases["三国"])


if __name__ == "__main__":
    unittest.main()
