#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))


def _load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


runtime = _load_module("semantic_gate_runtime_module", "scripts/sc/_semantic_gate_all_runtime.py")
coverage_llm = _load_module("subtasks_coverage_llm_module", "scripts/sc/_subtasks_coverage_llm.py")


class SemanticGatePromptBudgetTests(unittest.TestCase):
    def test_task_brief_should_keep_head_and_tail_acceptance_items_when_limited(self) -> None:
        back = {"acceptance": [f"Back item {i}" for i in range(1, 8)]}
        gameplay = {"acceptance": [f"Gameplay item {i}" for i in range(1, 8)]}

        brief = runtime._task_brief(
            11,
            max_acceptance_items=4,
            master={"title": "Task 11", "description": "desc", "details": "details"},
            back=back,
            gameplay=gameplay,
        )

        self.assertIn("Back item 1", brief)
        self.assertIn("Back item 7", brief)
        self.assertIn("Gameplay item 1", brief)
        self.assertIn("Gameplay item 7", brief)

    def test_build_prompt_with_budget_should_preserve_tail_acceptance_when_trimmed(self) -> None:
        prompt, trimmed, _budget = runtime.build_prompt_with_budget(
            batch=[11],
            max_acceptance_items=20,
            max_prompt_chars=2000,
            delivery_profile_context="profile: fast-ship",
            master_by_id={11: {"title": "Task 11", "description": "d" * 1200, "details": "x" * 1600}},
            back_by_id={11: {"acceptance": [f"Back acceptance {i}" for i in range(1, 18)]}},
            gameplay_by_id={11: {"acceptance": [f"Gameplay acceptance {i}" for i in range(1, 18)]}},
        )

        self.assertTrue(trimmed)
        self.assertIn("Back acceptance 17", prompt)
        self.assertIn("Gameplay acceptance 17", prompt)


class SubtasksCoveragePromptBudgetTests(unittest.TestCase):
    def test_truncate_keep_ends_should_keep_head_and_tail_markers(self) -> None:
        text = "HEAD-" + ("x" * 200) + "-TAIL"
        clipped = coverage_llm.truncate_keep_ends(text, max_chars=80)

        self.assertIn("HEAD-", clipped)
        self.assertIn("-TAIL", clipped)


if __name__ == "__main__":
    unittest.main()
