#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

import _change_scope as change_scope  # noqa: E402


class ChangeScopeTests(unittest.TestCase):
    def test_classify_change_scope_should_allow_full_reuse_for_nonsemantic_docs_only(self) -> None:
        payload = change_scope.classify_change_scope(
            previous_head="abc123",
            previous_status_short=[],
            current_head="def456",
            current_status_short=[],
            diff_paths=[
                "README.md",
                "docs/agents/00-index.md",
            ],
        )

        self.assertTrue(payload["sc_test_reuse_allowed"])
        self.assertEqual("reuse-latest", payload["deterministic_strategy"])
        self.assertEqual([], payload["acceptance_only_steps"])
        self.assertEqual([], payload["unsafe_paths"])

    def test_classify_change_scope_should_require_minimal_acceptance_for_task_semantics_delta(self) -> None:
        payload = change_scope.classify_change_scope(
            previous_head="abc123",
            previous_status_short=[],
            current_head="def456",
            current_status_short=[],
            diff_paths=[
                ".taskmaster/tasks/tasks_back.json",
                "docs/architecture/overlays/PRD-template/08/feature-slice.md",
            ],
        )

        self.assertTrue(payload["sc_test_reuse_allowed"])
        self.assertEqual("minimal-acceptance", payload["deterministic_strategy"])
        self.assertIn("links", payload["acceptance_only_steps"])
        self.assertIn("overlay", payload["acceptance_only_steps"])
        self.assertIn("subtasks", payload["acceptance_only_steps"])
        self.assertTrue(str(payload["change_fingerprint"]).strip())

    def test_classify_change_scope_should_reject_runtime_code_delta(self) -> None:
        payload = change_scope.classify_change_scope(
            previous_head="abc123",
            previous_status_short=[],
            current_head="def456",
            current_status_short=[],
            diff_paths=[
                "Game.Core/Gameplay/GuildManager.cs",
                "docs/architecture/overlays/PRD-template/08/feature-slice.md",
            ],
        )

        self.assertFalse(payload["sc_test_reuse_allowed"])
        self.assertEqual("full-pipeline", payload["deterministic_strategy"])
        self.assertIn("Game.Core/Gameplay/GuildManager.cs", payload["unsafe_paths"])


if __name__ == "__main__":
    unittest.main()
