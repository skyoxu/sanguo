#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
sys.path.insert(0, str(SC_DIR))

from _acceptance_task_requirements import (  # noqa: E402
    collect_task_refs,
    parse_task_id,
    task_requires_env_evidence_preflight,
    task_requires_headless_e2e,
)


class AcceptanceTaskRequirementsTests(unittest.TestCase):
    def test_parse_task_id_should_normalize_subtask_id(self) -> None:
        self.assertEqual("10", parse_task_id("10.3"))
        self.assertEqual("10", parse_task_id("10"))
        self.assertIsNone(parse_task_id(None))
        self.assertIsNone(parse_task_id("  "))

    def test_collect_refs_should_include_acceptance_and_test_refs(self) -> None:
        triplet = SimpleNamespace(
            back={
                "acceptance": [
                    "ACC:T1.1 Refs: Tests/Scenes/test_scene.gd, Tests/Core/TestA.cs",
                    "ACC:T1.2 no refs",
                ],
                "test_refs": ["Tests/Core/TestA.cs", "Tests/Core/TestB.cs"],
            },
            gameplay={
                "acceptance": [
                    "ACC:T1.3 Refs: Tests/Scenes/test_scene.gd; Tests/Core/TestC.cs",
                ],
                "test_refs": [],
            },
        )
        refs = collect_task_refs(triplet)
        self.assertEqual(
            [
                "Tests/Scenes/test_scene.gd",
                "Tests/Core/TestA.cs",
                "Tests/Core/TestB.cs",
                "Tests/Core/TestC.cs",
            ],
            refs,
        )

    def test_requires_headless_should_be_true_when_gd_in_acceptance_refs(self) -> None:
        triplet = SimpleNamespace(
            back={"acceptance": ["ACC:T2.1 Refs: Tests/Scenes/test_battle.gd"], "test_refs": []},
            gameplay=None,
        )
        self.assertTrue(task_requires_headless_e2e(triplet))

    def test_requires_headless_should_be_true_when_gd_in_test_refs(self) -> None:
        triplet = SimpleNamespace(
            back={"acceptance": [], "test_refs": ["Tests/Scenes/test_reward_flow.gd"]},
            gameplay=None,
        )
        self.assertTrue(task_requires_headless_e2e(triplet))

    def test_requires_env_evidence_should_be_rule_driven_by_refs(self) -> None:
        triplet = SimpleNamespace(
            back={"acceptance": [], "test_refs": ["Game.Core.Tests/Task1EnvironmentEvidencePersistenceTests.cs"]},
            gameplay=None,
        )
        self.assertTrue(task_requires_env_evidence_preflight(triplet))


if __name__ == "__main__":
    unittest.main()
