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


prototype_workflow = _load_module("run_prototype_workflow_bmad_test_module", "scripts/python/run_prototype_workflow.py")


class RunPrototypeWorkflowBmadIntakeTests(unittest.TestCase):
    def test_game_type_guide_parser_should_extract_step07_sections(self) -> None:
        parsed = prototype_workflow.parse_game_type_guide(
            "## Puzzle Game Specific Elements\n\n"
            "### Core Puzzle Mechanics\n\n"
            "{{puzzle_mechanics}}\n\n"
            "**Puzzle elements:**\n\n"
            "- Primary puzzle mechanic(s)\n"
            "- Constraint systems\n\n"
            "### Puzzle Progression\n\n"
            "{{puzzle_progression}}\n\n"
            "- Tutorial puzzles\n",
            game_type="puzzle",
            path="docs/game-type-guides/puzzle.md",
        )

        self.assertEqual("puzzle", parsed["game_type"])
        self.assertEqual("docs/game-type-guides/puzzle.md", parsed["guide_path"])
        self.assertEqual("core_puzzle_mechanics", parsed["sections"][0]["id"])
        self.assertEqual("Core Puzzle Mechanics", parsed["sections"][0]["title"])
        self.assertEqual(["puzzle_mechanics"], parsed["sections"][0]["placeholders"])
        self.assertIn("Primary puzzle mechanic", parsed["sections"][0]["prompt"])

    def test_prototype_relevant_sections_should_keep_step07_lite(self) -> None:
        parsed = prototype_workflow.parse_game_type_guide(
            "### Core Puzzle Mechanics\n\n{{puzzle_mechanics}}\n\n- Primary mechanic\n\n"
            "### Puzzle Progression\n\n{{puzzle_progression}}\n\n- Difficulty curve\n\n"
            "### Level Structure\n\n{{level_structure}}\n\n- Level count\n\n"
            "### Player Assistance\n\n{{player_assistance}}\n\n- Hint system\n\n"
            "### Replayability\n\n{{replayability}}\n\n- Daily puzzle\n",
            game_type="puzzle",
            path="docs/game-type-guides/puzzle.md",
        )

        selected = prototype_workflow.select_prototype_relevant_sections(parsed, limit=3)

        self.assertEqual(["core_puzzle_mechanics", "puzzle_progression", "level_structure"], [item["id"] for item in selected])
        self.assertLessEqual(len(selected), 3)

    def test_required_questions_should_add_step07_lite_questions_after_core_fields(self) -> None:
        payload = prototype_workflow.normalize_prototype_payload(
            {
                "slug": "gravity-room",
                "game_type": "puzzle",
                "game_type_guide_path": "docs/game-type-guides/puzzle.md",
                "game_type_guide_content": "### Core Puzzle Mechanics\n\n{{puzzle_mechanics}}\n\n- Primary mechanic\n\n",
                "hypothesis": "Gravity flipping can support a readable one-room puzzle prototype.",
                "core_player_fantasy": "The player feels clever after bending the room rules.",
                "minimum_playable_loop": "Enter a room, flip gravity, dodge one hazard, and reach the exit.",
                "success_criteria": ["The player reaches the exit without extra explanation."],
                "game_feature": "Gravity flip rooms",
                "core_gameplay_loop": "Read room, flip gravity, move, dodge, exit",
                "win_fail_conditions": "Win on exit, fail on spikes or timeout",
            },
            today="2026-05-03",
        )

        questions = prototype_workflow.required_questions_for_missing_payload(payload)

        self.assertEqual(["game_type_specifics.core_puzzle_mechanics"], [item["id"] for item in questions])
        self.assertIn("Core Puzzle Mechanics", questions[0]["prompt"])

    def test_main_should_persist_step07_lite_answers_in_active_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            guide = root / "docs" / "game-type-guides" / "puzzle.md"
            guide.parent.mkdir(parents=True)
            guide.write_text("### Core Puzzle Mechanics\n\n{{puzzle_mechanics}}\n\n- Primary mechanic\n", encoding="utf-8")

            with mock.patch.object(prototype_workflow, "repo_root", return_value=root):
                rc = prototype_workflow.main(
                    [
                        "--set",
                        "slug=gravity-room",
                        "--set",
                        "game_type=puzzle",
                        "--set",
                        "hypothesis=Gravity flipping can support a readable one-room puzzle prototype.",
                        "--set",
                        "core_player_fantasy=The player feels clever after bending the room rules.",
                        "--set",
                        "minimum_playable_loop=Enter a room, flip gravity, dodge one hazard, and reach the exit.",
                        "--set",
                        "success_criteria=The player reaches the exit without extra explanation.",
                        "--set",
                        "game_feature=Gravity flip rooms",
                        "--set",
                        "core_gameplay_loop=Read room, flip gravity, move, dodge, exit",
                        "--set",
                        "win_fail_conditions=Win on exit, fail on spikes or timeout",
                        "--set",
                        "game_type_specifics.core_puzzle_mechanics=Flip gravity changes the valid path through one constrained room.",
                    ]
                )

            self.assertEqual(0, rc)
            state = json.loads((root / "logs" / "ci" / "active-prototypes" / "gravity-room.active.json").read_text(encoding="utf-8"))
            specifics = state["prototype"]["game_type_specifics"]
            self.assertEqual("puzzle", specifics["game_type"])
            self.assertEqual("docs/game-type-guides/puzzle.md", specifics["guide_path"])
            self.assertEqual("core_puzzle_mechanics", specifics["selected_sections"][0]["id"])
            self.assertEqual("Flip gravity changes the valid path through one constrained room.", specifics["selected_sections"][0]["answer"])
            self.assertIn("Core Puzzle Mechanics", state["confirmation_summary"])
            self.assertIn("Flip gravity changes", state["confirmation_summary"])

    def test_required_questions_should_ask_core_gameplay_fields_sequentially_after_base_fields(self) -> None:
        payload = prototype_workflow.normalize_prototype_payload(
            {
                "slug": "gravity-room",
                "hypothesis": "Gravity flipping can support a readable one-room puzzle prototype.",
                "core_player_fantasy": "The player feels clever after bending the room rules.",
                "minimum_playable_loop": "Enter a room, flip gravity, dodge one hazard, and reach the exit.",
                "success_criteria": ["The player reaches the exit without extra explanation."],
            },
            today="2026-05-03",
        )

        self.assertEqual(
            ["game_feature", "core_gameplay_loop", "win_fail_conditions"],
            prototype_workflow.required_field_names(payload),
        )
        self.assertEqual(
            ["game_feature", "core_gameplay_loop", "win_fail_conditions"],
            [item["id"] for item in prototype_workflow.required_questions_for_missing_payload(payload)],
        )

    def test_main_should_persist_core_gameplay_fields_in_active_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "scripts" / "python").mkdir(parents=True)
            with mock.patch.object(prototype_workflow, "repo_root", return_value=root):
                rc = prototype_workflow.main(
                    [
                        "--set",
                        "slug=gravity-room",
                        "--set",
                        "hypothesis=Gravity flipping can support a readable one-room puzzle prototype.",
                        "--set",
                        "core_player_fantasy=The player feels clever after bending the room rules.",
                        "--set",
                        "minimum_playable_loop=Enter a room, flip gravity, dodge one hazard, and reach the exit.",
                        "--set",
                        "success_criteria=The player reaches the exit without extra explanation.",
                        "--set",
                        "game_feature=Gravity flip rooms",
                        "--set",
                        "core_gameplay_loop=Read room, flip gravity, move, dodge, exit",
                        "--set",
                        "win_fail_conditions=Win on exit, fail on spikes or timeout",
                    ]
                )

            self.assertEqual(0, rc)
            active_path = root / "logs" / "ci" / "active-prototypes" / "gravity-room.active.json"
            state = json.loads(active_path.read_text(encoding="utf-8"))
            self.assertEqual("needs-confirmation", state["status"])
            self.assertEqual("Gravity flip rooms", state["prototype"]["game_feature"])
            self.assertEqual("Read room, flip gravity, move, dodge, exit", state["prototype"]["core_gameplay_loop"])
            self.assertEqual("Win on exit, fail on spikes or timeout", state["prototype"]["win_fail_conditions"])
            self.assertIn("游戏特色：Gravity flip rooms", state["confirmation_summary"])

    def test_game_type_guide_should_be_loaded_when_game_type_is_known(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            guide = root / "docs" / "game-type-guides" / "puzzle.md"
            guide.parent.mkdir(parents=True)
            guide.write_text("# Puzzle Guide\n\n{{puzzle_mechanics}}\n", encoding="utf-8")

            payload = prototype_workflow.normalize_prototype_payload(
                {
                    "slug": "gravity-room",
                    "game_type": "puzzle",
                    "hypothesis": "Gravity flipping can support a readable one-room puzzle prototype.",
                    "core_player_fantasy": "The player feels clever after bending the room rules.",
                    "minimum_playable_loop": "Enter a room, flip gravity, dodge one hazard, and reach the exit.",
                    "success_criteria": ["The player reaches the exit without extra explanation."],
                    "game_feature": "Gravity flip rooms",
                    "core_gameplay_loop": "Read room, flip gravity, move, dodge, exit",
                    "win_fail_conditions": "Win on exit, fail on spikes or timeout",
                },
                today="2026-05-03",
            )

            loaded = prototype_workflow.load_game_type_guide(root=root, payload=payload)

            self.assertEqual("docs/game-type-guides/puzzle.md", loaded["path"])
            self.assertIn("Puzzle Guide", loaded["content"])


if __name__ == "__main__":
    unittest.main()
