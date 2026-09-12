from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def run(*args: str, cwd: Path, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        input=input_text,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


class KnowledgeControlPlaneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        subprocess.check_call(["git", "init", "-b", "main"], cwd=self.repo, stdout=subprocess.DEVNULL)
        subprocess.check_call(["git", "config", "user.email", "test@example.com"], cwd=self.repo)
        subprocess.check_call(["git", "config", "user.name", "Test"], cwd=self.repo)

        for relative in [
            "knowledge/policies/consumer-policies.v1.json",
            "knowledge/policies/source-exclusions.v1.json",
            "scripts/python/_knowledge_catalog_builder.py",
            "scripts/python/build_knowledge_catalog.py",
            "scripts/python/_knowledge_locator_core.py",
            "scripts/python/knowledge_locator.py",
            "scripts/python/evaluate_knowledge_queries.py",
            "scripts/python/prepare_knowledge_context.py",
            "scripts/python/publish_knowledge_catalog.py",
            "knowledge/evaluation/queries.v1.json",
        ]:
            target = self.repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)

        files = {
            "AGENTS.md": "# Repository Guide\nContext Reset startup order. Use Chinese with users.\n",
            "README.md": "# Game\nWindows Godot game.\n",
            "workflow.md": "# Workflow\nChapter 6 single task daily loop and review pipeline.\n",
            "DELIVERY_PROFILE.md": "# Delivery\nfast-ship\n",
            "docs/PROJECT_DOCUMENTATION_INDEX.md": "# Index\nADR and PRD routes.\n",
            "docs/testing-framework.md": "# Tests\nxUnit and GdUnit4.\n",
            "docs/workflows/run-protocol.md": "# Run Protocol\nReview pipeline run protocol delivery profile.\n",
            "docs/architecture/ADR_INDEX_GODOT.md": "# ADR Index Godot\nAccepted Proposed Superseded.\n",
            "docs/adr/ADR-0034-test.md": "# ADR-0034: Test\n\n- Status: Accepted\n\nContracts live in Game.Core/Contracts.\n",
            "docs/adr/ADR-0033-old.md": "# ADR-0033: Old\n\n- Status: Superseded\n",
            "docs/prd/game.md": "# Game PRD\nCard combat and roguelike progression.\n",
            "docs/prd/PRD-TEST-GAME-0001.md": "# PRD-TEST-GAME-0001\n\n## 产品定位\n确定性卡牌战斗。\n\n## v1 目标\n提供可完成的单局闭环。\n",
            "docs/architecture/overlays/PRD-TEST-GAME-0001/08/08-Contracts.md": "# Overlay Contracts\n\nPRD-TEST-GAME-0001 architecture overlay contracts ADR authority.\n",
            ".taskmaster/tasks/tasks.json": "{\"master\":{\"tasks\":[{\"id\":7,\"title\":\"overlay refs acceptance linkage\"}]}}\n",
            "execution-plans/2026-01-01-old.md": "# Old Plan\n\n- Status: done\n",
            "logs/ci/latest.md": "# Very relevant ADR card combat text that must stay excluded\n",
            ".agents/skills/workflow-chapter4-test/references/business-repos/newrouge.md": "# Empirical Business Repo Evidence\ncard combat ADR overlay refs acceptance linkage\n",
        }
        for relative, text in files.items():
            path = self.repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

        subprocess.check_call(["git", "add", "."], cwd=self.repo)
        subprocess.check_call(["git", "commit", "-m", "seed"], cwd=self.repo, stdout=subprocess.DEVNULL)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def build(self) -> dict:
        completed = run(sys.executable, "scripts/python/build_knowledge_catalog.py", "--write", cwd=self.repo)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def publish(self) -> dict:
        completed = run(sys.executable, "scripts/python/publish_knowledge_catalog.py", "--publish", cwd=self.repo)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        return json.loads(completed.stdout)

    def request(self, query: str, consumer: str = "repository-session") -> dict:
        snapshot = json.loads(
            (self.repo / "knowledge/snapshots/repository-source-snapshot.v1.json").read_text(encoding="utf-8")
        )
        request = {
            "schema_version": "newrouge.knowledge-locator-request.v1",
            "request_id": "t1",
            "consumer": consumer,
            "query": query,
            "snapshot": {"ref": snapshot["ref"], "commit": snapshot["commit"]},
            "policy_revision": "newrouge-knowledge-consumer-policies.v1",
        }
        completed = run(
            sys.executable,
            "scripts/python/knowledge_locator.py",
            cwd=self.repo,
            input_text=json.dumps(request),
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def test_build_excludes_transient_and_empirical_evidence_and_classifies_domains(self) -> None:
        summary = self.build()
        self.assertGreater(summary["modules"], 6)
        catalog = json.loads(
            (self.repo / "knowledge/catalogs/repository-knowledge-catalog.v1.json").read_text(encoding="utf-8")
        )
        paths = {module["source_path"] for module in catalog["modules"]}
        self.assertNotIn("logs/ci/latest.md", paths)
        self.assertNotIn(
            ".agents/skills/workflow-chapter4-test/references/business-repos/newrouge.md",
            paths,
        )
        self.assertIn("workflow.md", paths)
        self.assertIn("docs/architecture/ADR_INDEX_GODOT.md", paths)
        prd = next(module for module in catalog["modules"] if module["source_path"] == "docs/prd/game.md")
        self.assertEqual(prd["primary_domain"], "game-design")
        workflow = next(module for module in catalog["modules"] if module["source_path"] == "workflow.md")
        self.assertEqual(workflow["primary_domain"], "toolchain")
        adr_index = next(
            module
            for module in catalog["modules"]
            if module["source_path"] == "docs/architecture/ADR_INDEX_GODOT.md"
        )
        self.assertEqual(adr_index["primary_domain"], "game-runtime")

    def test_check_mode_detects_missing_and_then_matches_written_layers(self) -> None:
        missing = run(sys.executable, "scripts/python/build_knowledge_catalog.py", "--check", cwd=self.repo)
        self.assertEqual(missing.returncode, 1)
        self.assertEqual(json.loads(missing.stdout)["status"], "stale")
        self.build()
        current = run(sys.executable, "scripts/python/build_knowledge_catalog.py", "--check", cwd=self.repo)
        self.assertEqual(current.returncode, 0, current.stdout + current.stderr)
        self.assertEqual(json.loads(current.stdout)["status"], "ok")

    def test_build_only_does_not_authorize_canonical_locator(self) -> None:
        self.build()
        result = self.request("card combat roguelike")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["candidates"], [])

    def test_locator_is_location_only_and_hides_historical_without_exact_name(self) -> None:
        self.publish()
        result = self.request("card combat roguelike")
        self.assertEqual(result["status"], "matched")
        self.assertTrue(result["candidates"])
        self.assertTrue(all("answer" not in candidate for candidate in result["candidates"]))
        self.assertTrue(all(candidate["path"] != "logs/ci/latest.md" for candidate in result["candidates"]))
        self.assertTrue(
            all(candidate["path"] != "execution-plans/2026-01-01-old.md" for candidate in result["candidates"])
        )
        self.assertTrue(
            all(
                candidate["path"]
                != ".agents/skills/workflow-chapter4-test/references/business-repos/newrouge.md"
                for candidate in result["candidates"]
            )
        )

    def test_locator_can_retrieve_workflow_and_adr_index_authority(self) -> None:
        self.publish()
        workflow_result = self.request("workflow Chapter 6 single task daily loop")
        workflow = next(candidate for candidate in workflow_result["candidates"] if candidate["path"] == "workflow.md")
        self.assertTrue(workflow["rank_evidence"]["policy_exact_path"])
        self.assertGreater(workflow["rank_evidence"]["entrypoint_token_matches"], 0)
        self.assertEqual(workflow["rank_evidence"]["policy_exact_path_bonus"], 128)

        implicit_result = self.request("single task daily loop")
        implicit_workflow = next(candidate for candidate in implicit_result["candidates"] if candidate["path"] == "workflow.md")
        self.assertTrue(implicit_workflow["rank_evidence"]["policy_exact_path"])
        self.assertEqual(implicit_workflow["rank_evidence"]["entrypoint_token_matches"], 0)
        self.assertEqual(implicit_workflow["rank_evidence"]["policy_exact_path_bonus"], 0)

        adr_index = self.request("ADR Index Godot Accepted Proposed Superseded", consumer="chapter4")
        self.assertTrue(
            any(
                candidate["path"] == "docs/architecture/ADR_INDEX_GODOT.md"
                for candidate in adr_index["candidates"]
            )
        )

    def test_canonical_workflow_entrypoint_survives_repetitive_delivery_history(self) -> None:
        for index in range(30):
            path = self.repo / f"decision-logs/2026-04-{index + 1:02d}-task-{index + 10}-chapter6-daily-loop.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                f"# Task {index + 10} Chapter 6 Single Task Daily Loop\n\nWorkflow Chapter 6 single task daily loop residual followup.\n",
                encoding="utf-8",
            )
        subprocess.check_call(["git", "add", "decision-logs"], cwd=self.repo)
        subprocess.check_call(["git", "commit", "-m", "add repetitive delivery history"], cwd=self.repo, stdout=subprocess.DEVNULL)
        self.publish()
        result = self.request("workflow Chapter 6 single task daily loop")
        workflow = next(candidate for candidate in result["candidates"] if candidate["path"] == "workflow.md")
        self.assertTrue(workflow["rank_evidence"]["policy_exact_path"])
        self.assertGreater(workflow["rank_evidence"]["entrypoint_token_matches"], 0)
        self.assertEqual(workflow["rank_evidence"]["policy_exact_path_bonus"], 128)

    def test_repository_query_evaluation_passes_on_published_source_set(self) -> None:
        self.publish()
        completed = run(sys.executable, "scripts/python/evaluate_knowledge_queries.py", cwd=self.repo)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["passed"], report["total"])

    def test_shadow_context_falls_back_without_generated_layers_and_never_freezes(self) -> None:
        completed = run(
            sys.executable,
            "scripts/python/prepare_knowledge_context.py",
            "--consumer",
            "chapter6",
            "--query",
            "task 7 implementation authority",
            cwd=self.repo,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        bundle = json.loads(completed.stdout)
        self.assertEqual(bundle["status"], "fallback_required")
        self.assertEqual(bundle["freeze_state"], "unfrozen")
        self.assertTrue(bundle["semantic_decision_required"])
        enforced = run(
            sys.executable,
            "scripts/python/prepare_knowledge_context.py",
            "--consumer",
            "chapter6",
            "--query",
            "task 7 implementation authority",
            "--enforce",
            cwd=self.repo,
        )
        self.assertEqual(enforced.returncode, 2)

    def test_shadow_context_is_candidate_only_after_publication(self) -> None:
        self.publish()
        completed = run(
            sys.executable,
            "scripts/python/prepare_knowledge_context.py",
            "--consumer",
            "chapter6",
            "--query",
            "taskmaster overlay refs acceptance linkage",
            cwd=self.repo,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        bundle = json.loads(completed.stdout)
        self.assertEqual(bundle["status"], "shadow_ready")
        self.assertEqual(bundle["freeze_state"], "unfrozen")
        self.assertTrue(bundle["semantic_decision_required"])
        self.assertTrue(bundle["candidates"])
        self.assertTrue(all("accepted" not in candidate for candidate in bundle["candidates"]))

    def test_repository_session_shadow_maps_fixed_authority_entrypoints(self) -> None:
        self.publish()
        completed = run(
            sys.executable,
            "scripts/python/prepare_knowledge_context.py",
            "--consumer",
            "repository-session",
            "--query",
            "repository context",
            cwd=self.repo,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        bundle = json.loads(completed.stdout)
        self.assertEqual(bundle["status"], "shadow_ready")
        agents = next(candidate for candidate in bundle["candidates"] if candidate["path"] == "AGENTS.md")
        workflow = next(candidate for candidate in bundle["candidates"] if candidate["path"] == "workflow.md")
        self.assertIn("repository-rules", agents["retrieval_context_classes"])
        self.assertIn("workflow-context", workflow["retrieval_context_classes"])
        self.assertTrue(all("accepted" not in candidate for candidate in bundle["candidates"]))

    def test_chapter4_shadow_backfills_required_context_class_candidates(self) -> None:
        self.publish()
        completed = run(
            sys.executable,
            "scripts/python/prepare_knowledge_context.py",
            "--consumer",
            "chapter4",
            "--query",
            "PRD-TEST-GAME-0001 overlay contracts ADR architecture",
            cwd=self.repo,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        bundle = json.loads(completed.stdout)
        self.assertEqual(bundle["status"], "shadow_ready")
        prd = next(
            candidate
            for candidate in bundle["candidates"]
            if candidate["path"] == "docs/prd/PRD-TEST-GAME-0001.md"
        )
        self.assertIn("product-intent", prd["retrieval_context_classes"])
        overlay = next(
            candidate
            for candidate in bundle["candidates"]
            if candidate["path"] == "docs/architecture/overlays/PRD-TEST-GAME-0001/08/08-Contracts.md"
        )
        self.assertNotIn("product-intent", overlay["retrieval_context_classes"])
        self.assertTrue(
            any(
                "architecture-authority" in candidate.get("retrieval_context_classes", [])
                for candidate in bundle["candidates"]
            )
        )
        self.assertTrue(
            any(
                "contract-authority" in candidate.get("retrieval_context_classes", [])
                and candidate["path"].startswith(("docs/adr/", "Game.Core/Contracts/"))
                for candidate in bundle["candidates"]
            )
        )
        self.assertTrue(all("accepted" not in candidate for candidate in bundle["candidates"]))

    def test_locator_blocks_when_authority_ref_moves(self) -> None:
        self.publish()
        (self.repo / "docs/prd/game.md").write_text("# Game PRD\nChanged.\n", encoding="utf-8")
        subprocess.check_call(["git", "add", "docs/prd/game.md"], cwd=self.repo)
        subprocess.check_call(["git", "commit", "-m", "change source"], cwd=self.repo, stdout=subprocess.DEVNULL)
        result = self.request("card combat")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["candidates"], [])

    def test_superseded_adr_is_historical_but_exact_query_can_find_it(self) -> None:
        self.publish()
        general = self.request("old architecture")
        self.assertTrue(
            all(candidate["path"] != "docs/adr/ADR-0033-old.md" for candidate in general["candidates"])
        )
        exact = self.request("ADR-0033")
        self.assertTrue(any(candidate["path"] == "docs/adr/ADR-0033-old.md" for candidate in exact["candidates"]))


if __name__ == "__main__":
    unittest.main()
