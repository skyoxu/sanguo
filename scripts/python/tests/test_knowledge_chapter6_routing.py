from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


class Chapter6KnowledgeRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        subprocess.check_call(["git", "init", "-b", "main"], cwd=self.repo, stdout=subprocess.DEVNULL)
        subprocess.check_call(["git", "config", "user.email", "test@example.com"], cwd=self.repo)
        subprocess.check_call(["git", "config", "user.name", "Test"], cwd=self.repo)

        for relative in [
            "knowledge/policies/consumer-policies.v1.json",
            "knowledge/policies/source-exclusions.v1.json",
            "knowledge/evaluation/queries.v1.json",
            "scripts/python/_knowledge_catalog_builder.py",
            "scripts/python/build_knowledge_catalog.py",
            "scripts/python/_knowledge_locator_core.py",
            "scripts/python/knowledge_locator.py",
            "scripts/python/evaluate_knowledge_queries.py",
            "scripts/python/prepare_knowledge_context.py",
            "scripts/python/publish_knowledge_catalog.py",
        ]:
            target = self.repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)

        task_view = {
            "tasks": [
                {
                    "id": "GM-0129",
                    "taskmaster_id": 29,
                    "title": "Implement card drop pools per Act and encounter type",
                    "status": "done",
                    "adr_refs": ["ADR-0032", "ADR-0033"],
                    "overlay_refs": [
                        "docs/architecture/overlays/PRD-TEST-GAME-0001/08/08-T29.md"
                    ],
                    "test_refs": [
                        "Game.Core.Tests/Tasks/Task0029AcceptanceTests.cs",
                        "Game.Core.Tests/Services/OfferServiceDeterminismTests.cs",
                    ],
                    "acceptance": [
                        "Reward preview is deterministic and UI inspection does not advance RNG state."
                    ],
                    "contractRefs": ["core.reward.offer.presented"],
                },
                {
                    "id": "GM-0229",
                    "taskmaster_id": 229,
                    "title": "Later reward UI wiring",
                    "status": "planned",
                    "depends_on": ["GM-0129"],
                    "details": (
                        "task 29 GM-0129 card drop pools reward offer deterministic "
                        "ADR-0032 ADR-0033 appears here only as a dependency reference."
                    ),
                },
            ]
        }
        task_text = json.dumps(task_view, ensure_ascii=False, indent=2) + "\n"
        self.task_identity_line = next(
            index
            for index, line in enumerate(task_text.splitlines(), 1)
            if line.strip() == '"id": "GM-0129",'
        )

        files = {
            "AGENTS.md": "# Repository Guide\nContext Reset startup order. Use Chinese with users.\n",
            "README.md": "# Game\nWindows Godot game.\n",
            "workflow.md": "# Workflow\nChapter 6 RED GREEN REFACTOR single-task daily loop.\n",
            "DELIVERY_PROFILE.md": "# Delivery\nfast-ship\n",
            "docs/PROJECT_DOCUMENTATION_INDEX.md": "# Index\nADR and PRD routes.\n",
            "docs/testing-framework.md": "# Tests\nxUnit and GdUnit4.\n",
            "docs/workflows/run-protocol.md": "# Run Protocol\nReview pipeline run protocol delivery profile.\n",
            "docs/architecture/ADR_INDEX_GODOT.md": "# ADR Index Godot\nADR-0032 and ADR-0033 are Accepted.\n",
            "docs/adr/ADR-0032-determinism.md": (
                "# ADR-0032: Deterministic Outcomes\n\n"
                "- Status: Accepted\n"
                "- Decision: reward candidates are locked; UI preview must not advance RNG.\n"
                "- Related: ADR-0033.\n"
            ),
            "docs/adr/ADR-0033-card-identity.md": (
                "# ADR-0033: Card Identity And Forms\n\n"
                "- Status: Accepted\n"
                "- Decision: reward card identity/form is stable and deterministic.\n"
                "- Related: ADR-0032.\n"
            ),
            "docs/prd/PRD-TEST-GAME-0001.md": "# PRD-TEST-GAME-0001\nDeterministic card rewards.\n",
            "docs/architecture/overlays/PRD-TEST-GAME-0001/08/08-T29.md": (
                "# Task29 Backlinks\n"
                "Task: T29 / GM-0129.\n"
                "ADR-Refs: ADR-0032, ADR-0033.\n"
                "Contract: core.reward.offer.presented.\n"
            ),
            "Game.Core/Contracts/Events/RewardOfferPresentedEvent.cs": (
                "namespace Game.Core.Contracts.Events;\n"
                "// ADR-0032 ADR-0033 reward contract.\n"
                "public sealed record RewardOfferPresentedEvent(string OfferId);\n"
            ),
            ".taskmaster/tasks/tasks.json": "{\"master\":{\"tasks\":[{\"id\":29,\"title\":\"Implement card drop pools per Act and encounter type\"}]}}\n",
            ".taskmaster/tasks/tasks_gameplay.json": task_text,
            "execution-plans/2026-01-01-old.md": "# Old Plan\n\n- Status: done\n",
            "decision-logs/2026-01-01-old.md": "# Old Decision\nReward implementation history.\n",
            "logs/ci/latest.md": "# Relevant reward text that must stay excluded\n",
            ".agents/skills/workflow-chapter4-test/references/business-repos/newrouge.md": "# Evidence\nreward\n",
        }
        for index in range(12):
            files[f"execution-plans/2026-02-{index + 1:02d}-gm-0129-reward-noise.md"] = (
                f"# GM-0129 reward implementation plan noise {index}\n\n"
                "- Status: in-progress\n"
                "task 29 GM-0129 card drop pools reward offer implementation.\n"
                "This plan references the task but is not task authority or ADR authority.\n"
            )
        for relative, text in files.items():
            path = self.repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

        subprocess.check_call(["git", "add", "."], cwd=self.repo)
        subprocess.check_call(["git", "commit", "-m", "seed"], cwd=self.repo, stdout=subprocess.DEVNULL)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_chapter6_freezes_task_and_implementation_authority_before_red(self) -> None:
        published = run(sys.executable, "scripts/python/publish_knowledge_catalog.py", "--publish", cwd=self.repo)
        self.assertEqual(published.returncode, 0, published.stdout + published.stderr)

        completed = run(
            sys.executable,
            "scripts/python/prepare_knowledge_context.py",
            "--consumer",
            "chapter6",
            "--query",
            "task 29 GM-0129 card drop pools Act encounter reward offer deterministic ADR-0032 ADR-0033 core.reward.offer.presented",
            cwd=self.repo,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        bundle = json.loads(completed.stdout)
        self.assertEqual(bundle["status"], "shadow_ready")
        self.assertEqual(bundle["freeze_state"], "unfrozen")

        task_candidate = next(
            candidate
            for candidate in bundle["candidates"]
            if candidate["path"] == ".taskmaster/tasks/tasks_gameplay.json"
        )
        self.assertEqual(task_candidate["line_start"], self.task_identity_line)
        self.assertEqual(task_candidate["rank_evidence"]["location_strategy"], "task-identity")
        self.assertTrue(task_candidate["rank_evidence"]["task_identity_match"])
        self.assertEqual(task_candidate["rank_evidence"]["task_identity_bonus"], 256)
        self.assertIn("task-context", task_candidate["retrieval_context_classes"])

        for path in (
            "docs/adr/ADR-0032-determinism.md",
            "docs/adr/ADR-0033-card-identity.md",
        ):
            candidate = next(item for item in bundle["candidates"] if item["path"] == path)
            self.assertIn("implementation-authority", candidate["retrieval_context_classes"])

        overlay_candidate = next(
            candidate
            for candidate in bundle["candidates"]
            if candidate["path"] == "docs/architecture/overlays/PRD-TEST-GAME-0001/08/08-T29.md"
        )
        self.assertNotIn("implementation-authority", overlay_candidate["retrieval_context_classes"])

        noise = [
            candidate
            for candidate in bundle["candidates"]
            if candidate["path"].startswith("execution-plans/2026-02-")
        ]
        self.assertTrue(noise)
        self.assertTrue(all("task-context" not in item["retrieval_context_classes"] for item in noise))
        self.assertTrue(
            all("implementation-authority" not in item["retrieval_context_classes"] for item in noise)
        )
        self.assertTrue(all("accepted" not in candidate for candidate in bundle["candidates"]))


if __name__ == "__main__":
    unittest.main()
