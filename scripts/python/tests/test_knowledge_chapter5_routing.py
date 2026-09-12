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


class Chapter5KnowledgeRoutingTests(unittest.TestCase):
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
                    "id": "GM-0128",
                    "taskmaster_id": 28,
                    "title": "Create ActConfig data model and loader",
                    "status": "done",
                    "adr_refs": ["ADR-0021"],
                    "overlay_refs": [
                        "docs/architecture/overlays/PRD-TEST-GAME-0001/08/08-T28.md"
                    ],
                    "test_refs": ["Game.Core.Tests/Tasks/Task0028AcceptanceTests.cs"],
                    "acceptance": [
                        "ActConfig schema validation must return deterministic success or stable failure details."
                    ],
                },
                {
                    "id": "GM-0221",
                    "taskmaster_id": 121,
                    "title": "Wire UI: Save, Settings, And Meta Surfaces",
                    "status": "cancelled",
                    "depends_on": ["GM-0128"],
                    "details": (
                        "task 28 GM-0128 ActConfig loader acceptance schema validation "
                        "contract ADR-0021 overlay test refs appears here only as a dependency."
                    ),
                },
            ]
        }
        task_text = json.dumps(task_view, ensure_ascii=False, indent=2) + "\n"
        self.task_identity_line = next(
            index
            for index, line in enumerate(task_text.splitlines(), 1)
            if line.strip() == '"id": "GM-0128",'
        )

        files = {
            "AGENTS.md": "# Repository Guide\nContext Reset startup order. Use Chinese with users.\n",
            "README.md": "# Game\nWindows Godot game.\n",
            "workflow.md": "# Workflow\nChapter 6 single task daily loop and review pipeline.\n",
            "DELIVERY_PROFILE.md": "# Delivery\nfast-ship\n",
            "docs/PROJECT_DOCUMENTATION_INDEX.md": "# Index\nADR and PRD routes.\n",
            "docs/testing-framework.md": "# Tests\nxUnit and GdUnit4.\n",
            "docs/workflows/run-protocol.md": "# Run Protocol\nReview pipeline run protocol delivery profile.\n",
            "docs/architecture/ADR_INDEX_GODOT.md": "# ADR Index Godot\nAccepted Proposed Superseded.\n",
            "docs/adr/ADR-0021-domain.md": (
                "# ADR-0021: C# Domain Layer Architecture\n\n"
                "- Status: Accepted\n"
                "- Decision: keep Game.Core architecture engine-agnostic and contracts under Game.Core/Contracts.\n"
            ),
            "docs/adr/ADR-0034-test.md": "# ADR-0034: Test\n\n- Status: Accepted\n\nContracts live in Game.Core/Contracts.\n",
            "docs/adr/ADR-0033-old.md": "# ADR-0033: Old\n\n- Status: Superseded\n",
            "docs/prd/game.md": "# Game PRD\nCard combat and roguelike progression.\n",
            "docs/prd/PRD-TEST-GAME-0001.md": "# PRD-TEST-GAME-0001\n\n## 产品定位\n确定性卡牌战斗。\n",
            "docs/architecture/overlays/PRD-TEST-GAME-0001/08/08-T28.md": (
                "# Task28 Contract Backlinks\n"
                "Task: T28 / GM-0128 Create ActConfig data model and loader.\n"
                "ADR-Refs: ADR-0021. Acceptance test refs cover schema validation.\n"
            ),
            "Game.Core/Contracts/Config/ActConfigLoadResult.cs": (
                "namespace Game.Core.Contracts.Config;\n"
                "// ADR-0021 contract architecture authority for ActConfig.\n"
                "public sealed record ActConfigLoadResult(bool IsSuccess);\n"
            ),
            ".taskmaster/tasks/tasks.json": "{\"master\":{\"tasks\":[{\"id\":7,\"title\":\"overlay refs acceptance linkage\"}]}}\n",
            ".taskmaster/tasks/tasks_gameplay.json": task_text,
            "execution-plans/2026-01-01-old.md": "# Old Plan\n\n- Status: done\n",
            "logs/ci/latest.md": "# Very relevant ADR card combat text that must stay excluded\n",
            ".agents/skills/workflow-chapter4-test/references/business-repos/newrouge.md": "# Evidence\ncard combat\n",
        }
        for index in range(40):
            files[
                f"execution-plans/2026-02-{index + 1:02d}-gm-0128-task-28-acceptance-test-refs-noise.md"
            ] = (
                f"# GM-0128 task 28 acceptance test refs routing noise {index}\n\n"
                "- Status: in-progress\n"
                "GM-0128 task 28 acceptance test refs ActConfig loader schema validation overlay.\n"
                "This plan mentions the task but is not the task or its acceptance overlay authority.\n"
            )
        for relative, text in files.items():
            path = self.repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

        subprocess.check_call(["git", "add", "."], cwd=self.repo)
        subprocess.check_call(["git", "commit", "-m", "seed"], cwd=self.repo, stdout=subprocess.DEVNULL)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_chapter5_routes_exact_task_identity_and_direct_semantic_authority(self) -> None:
        published = run(sys.executable, "scripts/python/publish_knowledge_catalog.py", "--publish", cwd=self.repo)
        self.assertEqual(published.returncode, 0, published.stdout + published.stderr)

        completed = run(
            sys.executable,
            "scripts/python/prepare_knowledge_context.py",
            "--consumer",
            "chapter5",
            "--query",
            "task 28 GM-0128 ActConfig loader acceptance schema validation contract ADR-0021 overlay",
            cwd=self.repo,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        bundle = json.loads(completed.stdout)
        self.assertEqual(bundle["status"], "shadow_ready")

        task_candidate = next(
            candidate
            for candidate in bundle["candidates"]
            if candidate["path"] == ".taskmaster/tasks/tasks_gameplay.json"
        )
        self.assertEqual(task_candidate["line_start"], self.task_identity_line)
        self.assertEqual(task_candidate["rank_evidence"]["location_strategy"], "task-identity")
        self.assertTrue(task_candidate["rank_evidence"]["task_identity_match"])
        self.assertEqual(task_candidate["rank_evidence"]["task_identity_bonus"], 256)
        self.assertIn("acceptance-scope", task_candidate["retrieval_context_classes"])

        adr_candidate = next(
            candidate
            for candidate in bundle["candidates"]
            if candidate["path"] == "docs/adr/ADR-0021-domain.md"
        )
        self.assertIn("semantic-authority", adr_candidate["retrieval_context_classes"])

        contract_candidate = next(
            candidate
            for candidate in bundle["candidates"]
            if candidate["path"] == "Game.Core/Contracts/Config/ActConfigLoadResult.cs"
        )
        self.assertIn("semantic-authority", contract_candidate["retrieval_context_classes"])

        overlay_candidate = next(
            candidate
            for candidate in bundle["candidates"]
            if candidate["path"] == "docs/architecture/overlays/PRD-TEST-GAME-0001/08/08-T28.md"
        )
        self.assertNotIn("semantic-authority", overlay_candidate["retrieval_context_classes"])

        noise = [
            candidate
            for candidate in bundle["candidates"]
            if candidate["path"].startswith("execution-plans/2026-02-")
        ]
        self.assertTrue(noise)
        self.assertTrue(
            all("acceptance-scope" not in candidate["retrieval_context_classes"] for candidate in noise)
        )
        self.assertTrue(all("accepted" not in candidate for candidate in bundle["candidates"]))


if __name__ == "__main__":
    unittest.main()
