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


class ReviewKnowledgeRoutingTests(unittest.TestCase):
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
                    "test_refs": [
                        "Game.Core.Tests/Tasks/Task0029AcceptanceTests.cs",
                        "Game.Core.Tests/Services/CardPoolSelectionTests.cs",
                    ],
                    "acceptance": [
                        "OfferService preview is deterministic and does not advance RNG state."
                    ],
                }
            ]
        }
        task_text = json.dumps(task_view, ensure_ascii=False, indent=2) + "\n"
        self.task_identity_line = next(
            index
            for index, line in enumerate(task_text.splitlines(), 1)
            if line.strip() == '"id": "GM-0129",'
        )

        files = {
            "AGENTS.md": (
                "# Repository Guide\n"
                "Context Reset startup order: review repository authority before expensive work.\n"
            ),
            "README.md": "# Game\nWindows Godot game.\n",
            "workflow.md": (
                "# Workflow\n"
                "Chapter 6 single task daily loop.\n"
                "Section 6.7 runs the review pipeline before final closure.\n"
                "Use run_review_pipeline.py and bounded reviewers.\n"
            ),
            "DELIVERY_PROFILE.md": (
                "# DELIVERY_PROFILE\n"
                "fast-ship review agents include code-reviewer and security-auditor.\n"
            ),
            "docs/PROJECT_DOCUMENTATION_INDEX.md": "# Index\nADR and workflow routes.\n",
            "docs/testing-framework.md": "# Tests\nxUnit and GdUnit4.\n",
            "docs/workflows/run-protocol.md": "# Run Protocol\nReview pipeline delivery protocol.\n",
            "docs/architecture/ADR_INDEX_GODOT.md": "# ADR Index Godot\nAccepted Proposed Superseded.\n",
            "docs/adr/ADR-0032-save-resume-determinism.md": (
                "# ADR-0032: Save/Resume Policy and Deterministic Outcomes\n\n"
                "- Status: Accepted\n"
                "- Decision: Game.Core/Contracts is the SSoT for deterministic reward contracts; "
                "reward preview must not advance RNG state.\n"
            ),
            "docs/adr/ADR-0033-card-identity-and-forms.md": (
                "# ADR-0033: Card Identity and Forms\n\n"
                "- Status: Accepted\n"
                "- Decision: card identity and form semantics remain stable in deterministic offers.\n"
            ),
            "docs/prd/PRD-TEST-GAME-0001.md": "# PRD-TEST-GAME-0001\nCard combat.\n",
            ".taskmaster/tasks/tasks_gameplay.json": task_text,
            ".taskmaster/tasks/tasks.json": json.dumps(
                {
                    "master": {
                        "tasks": [
                            {
                                "id": 29,
                                "title": "Implement card drop pools per Act and encounter type",
                                "status": "done",
                                "adrRefs": ["ADR-0032", "ADR-0033"],
                            }
                        ]
                    }
                },
                indent=2,
            )
            + "\n",
            "decision-logs/2026-05-22-task29-card-pool-failure-analysis.md": (
                "# Task29 CardPoolSelection Failure Analysis\n\n"
                "- Status: accepted\n"
                "- Related task id(s): 29\n"
                "- Decision: CardPoolSelection must expose exactly one canonical selection pool.\n"
                "- Failure: reward preview pools polluted selection GetAll and caused multiple matches.\n"
                "- Review impact: preserve deterministic selection behavior.\n"
            ),
        }
        for index in range(40):
            files[f"execution-plans/2026-03-{index + 1:02d}-review-noise.md"] = (
                f"# Review Pipeline Noise {index}\n\n"
                "- Status: in-progress\n"
                "task 29 GM-0129 review scope 6.7 pipeline deterministic card pools acceptance.\n"
                "This plan is unrelated routing noise.\n"
            )

        for relative, text in files.items():
            path = self.repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

        subprocess.check_call(["git", "add", "."], cwd=self.repo)
        subprocess.check_call(["git", "commit", "-m", "seed"], cwd=self.repo, stdout=subprocess.DEVNULL)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_review_routes_scope_architecture_and_delivery_supplements(self) -> None:
        published = run(sys.executable, "scripts/python/publish_knowledge_catalog.py", "--publish", cwd=self.repo)
        self.assertEqual(published.returncode, 0, published.stdout + published.stderr)

        completed = run(
            sys.executable,
            "scripts/python/prepare_knowledge_context.py",
            "--consumer",
            "review",
            "--query",
            "task 29 GM-0129 review scope deterministic card pools acceptance ADR-0032 ADR-0033 6.7 run_review_pipeline delivery profile",
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
        self.assertIn("review-scope", task_candidate["retrieval_context_classes"])

        for path in (
            "docs/adr/ADR-0032-save-resume-determinism.md",
            "docs/adr/ADR-0033-card-identity-and-forms.md",
        ):
            candidate = next(item for item in bundle["candidates"] if item["path"] == path)
            self.assertIn("architecture-context", candidate["retrieval_context_classes"])

        for path in ("workflow.md", "DELIVERY_PROFILE.md"):
            candidate = next(item for item in bundle["candidates"] if item["path"] == path)
            self.assertIn("delivery-context", candidate["retrieval_context_classes"])

        failure_candidate = next(
            item
            for item in bundle["candidates"]
            if item["path"] == "decision-logs/2026-05-22-task29-card-pool-failure-analysis.md"
        )
        self.assertIn("delivery-context", failure_candidate["retrieval_context_classes"])

        self.assertTrue(all("accepted" not in candidate for candidate in bundle["candidates"]))


if __name__ == "__main__":
    unittest.main()
