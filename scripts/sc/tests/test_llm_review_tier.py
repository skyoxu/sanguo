#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
sys.path.insert(0, str(SC_DIR))

from _llm_review_tier import resolve_llm_review_tier_plan  # noqa: E402
from _taskmaster import TaskmasterTriplet  # noqa: E402


def _triplet(
    *,
    task_id: str = "11",
    priority: str = "P2",
    master_title: str = "Implement feature slice",
    master_details: str = "Gameplay-facing feature work.",
    back: dict | None = None,
    gameplay: dict | None = None,
) -> TaskmasterTriplet:
    return TaskmasterTriplet(
        task_id=task_id,
        master={
            "id": task_id,
            "title": master_title,
            "priority": priority,
            "details": master_details,
        },
        back=back,
        gameplay=gameplay,
        tasks_json_path="examples/taskmaster/tasks.json",
        tasks_back_path="examples/taskmaster/tasks_back.json",
        tasks_gameplay_path="examples/taskmaster/tasks_gameplay.json",
        taskdoc_path=None,
    )


class LlmReviewTierPlanTests(unittest.TestCase):
    def test_playable_ea_auto_should_resolve_to_minimal_for_low_risk_task(self) -> None:
        plan = resolve_llm_review_tier_plan(
            delivery_profile="playable-ea",
            triplet=_triplet(),
            profile_defaults={
                "agents": "architect-reviewer,code-reviewer",
                "semantic_gate": "skip",
                "timeout_sec": 300,
                "agent_timeout_sec": 120,
                "strict": False,
            },
        )

        self.assertEqual("auto", plan["requested_tier"])
        self.assertEqual("minimal", plan["effective_tier"])
        self.assertEqual("architect-reviewer,code-reviewer", plan["agents"])
        self.assertEqual("skip", plan["semantic_gate"])
        self.assertFalse(bool(plan["strict"]))
        self.assertEqual([], plan["escalation_reasons"])

    def test_fast_ship_minimal_should_escalate_to_full_for_contract_task(self) -> None:
        plan = resolve_llm_review_tier_plan(
            delivery_profile="fast-ship",
            triplet=_triplet(
                priority="P2",
                master_title="Update domain contracts",
                master_details="Add new contractRefs and event types.",
                back={"semantic_review_tier": "minimal", "contractRefs": ["Game.Core/Contracts/Guild/GuildEvent.cs"]},
            ),
            profile_defaults={
                "agents": "code-reviewer,security-auditor,semantic-equivalence-auditor",
                "semantic_gate": "warn",
                "timeout_sec": 600,
                "agent_timeout_sec": 180,
                "strict": False,
            },
        )

        self.assertEqual("minimal", plan["requested_tier"])
        self.assertEqual("full", plan["effective_tier"])
        self.assertEqual("code-reviewer,security-auditor,semantic-equivalence-auditor", plan["agents"])
        self.assertEqual("warn", plan["semantic_gate"])
        self.assertIn("contract_refs_present", plan["escalation_reasons"])

    def test_fast_ship_minimal_should_narrow_reviewers_for_low_risk_task(self) -> None:
        plan = resolve_llm_review_tier_plan(
            delivery_profile="fast-ship",
            triplet=_triplet(
                priority="P2",
                back={"semantic_review_tier": "minimal"},
            ),
            profile_defaults={
                "agents": "code-reviewer,security-auditor,semantic-equivalence-auditor",
                "semantic_gate": "warn",
                "timeout_sec": 600,
                "agent_timeout_sec": 180,
                "strict": False,
            },
        )

        self.assertEqual("minimal", plan["effective_tier"])
        self.assertEqual("code-reviewer,security-auditor", plan["agents"])
        self.assertEqual("skip", plan["semantic_gate"])
        self.assertEqual([], plan["escalation_reasons"])

    def test_fast_ship_targeted_should_keep_narrow_reviewers_for_low_risk_task(self) -> None:
        plan = resolve_llm_review_tier_plan(
            delivery_profile="fast-ship",
            triplet=_triplet(
                priority="P2",
                back={"semantic_review_tier": "targeted"},
            ),
            profile_defaults={
                "agents": "code-reviewer,security-auditor,semantic-equivalence-auditor",
                "semantic_gate": "warn",
                "timeout_sec": 600,
                "agent_timeout_sec": 180,
                "strict": False,
            },
        )

        self.assertEqual("targeted", plan["effective_tier"])
        self.assertEqual("code-reviewer,security-auditor", plan["agents"])
        self.assertEqual("warn", plan["semantic_gate"])
        self.assertEqual([], plan["escalation_reasons"])

    def test_priority_p1_should_escalate_minimal_to_targeted(self) -> None:
        plan = resolve_llm_review_tier_plan(
            delivery_profile="playable-ea",
            triplet=_triplet(
                priority="P1",
                back={"semantic_review_tier": "minimal"},
            ),
            profile_defaults={
                "agents": "architect-reviewer,code-reviewer",
                "semantic_gate": "skip",
                "timeout_sec": 300,
                "agent_timeout_sec": 120,
                "strict": False,
            },
        )

        self.assertEqual("targeted", plan["effective_tier"])
        self.assertEqual("warn", plan["semantic_gate"])
        self.assertIn("priority_p1", plan["escalation_reasons"])


if __name__ == "__main__":
    unittest.main()
