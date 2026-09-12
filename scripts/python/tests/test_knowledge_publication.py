from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class KnowledgePublicationTests(unittest.TestCase):
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
            "scripts/python/_knowledge_locator_core.py",
            "scripts/python/publish_knowledge_catalog.py",
        ]:
            target = self.repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        suite = {
            "schema_version": "newrouge.knowledge-evaluation-suite.v1",
            "cases": [
                {
                    "id": "repository-rules",
                    "consumer": "repository-session",
                    "query": "Repository Guide startup rules",
                    "must_include": [{"any_paths": ["AGENTS.md"], "domains": ["toolchain"], "statuses": ["active"]}],
                    "forbidden_path_prefixes": ["logs/"],
                }
            ],
        }
        suite_path = self.repo / "knowledge/evaluation/queries.v1.json"
        suite_path.parent.mkdir(parents=True, exist_ok=True)
        suite_path.write_text(json.dumps(suite, indent=2) + "\n", encoding="utf-8")
        files = {
            "AGENTS.md": "# Repository Guide\nStartup rules and authority.\n",
            "README.md": "# Game\nWindows Godot game.\n",
            "workflow.md": "# Workflow\nChapter 6 single task loop.\n",
            "DELIVERY_PROFILE.md": "# Delivery\nfast-ship\n",
            "docs/PROJECT_DOCUMENTATION_INDEX.md": "# Index\nRoutes.\n",
            "docs/testing-framework.md": "# Tests\nxUnit and GdUnit4.\n",
            "docs/architecture/ADR_INDEX_GODOT.md": "# ADR Index Godot\nAccepted ADRs.\n",
            "docs/adr/ADR-0034-test.md": "# ADR-0034: Test\n\n- Status: Accepted\n",
            "docs/prd/game.md": "# Game PRD\nCard combat.\n",
            ".taskmaster/tasks/tasks.json": "{\"master\":{\"tasks\":[]}}\n",
        }
        for relative, content in files.items():
            target = self.repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        subprocess.check_call(["git", "add", "."], cwd=self.repo)
        subprocess.check_call(["git", "commit", "-m", "baseline"], cwd=self.repo, stdout=subprocess.DEVNULL)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_publish(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "scripts/python/publish_knowledge_catalog.py", "--repository-root", str(self.repo), *args],
            cwd=self.repo,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )

    def test_publish_creates_immutable_generation_current_and_lkg(self) -> None:
        result = self.run_publish("--publish")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        current = json.loads((self.repo / "knowledge/indexes/current.json").read_text(encoding="utf-8"))
        lkg = json.loads((self.repo / "knowledge/indexes/last-known-good.json").read_text(encoding="utf-8"))
        self.assertEqual(current, lkg)
        generation = self.repo / "knowledge/indexes/generations" / current["generation_id"]
        self.assertTrue((generation / "manifest.json").is_file())
        self.assertTrue((generation / "query_suite.json").is_file())
        self.assertTrue((generation / "evaluation.json").is_file())
        check = self.run_publish("--check")
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_check_blocks_when_bound_control_plane_artifact_drifts(self) -> None:
        first = self.run_publish("--publish")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        exclusions_path = self.repo / "knowledge/policies/source-exclusions.v1.json"
        exclusions = json.loads(exclusions_path.read_text(encoding="utf-8"))
        exclusions["rules"][0]["reason"] = "Changed after publication."
        exclusions_path.write_text(json.dumps(exclusions, indent=2) + "\n", encoding="utf-8")
        check = self.run_publish("--check")
        self.assertNotEqual(check.returncode, 0)
        payload = json.loads(check.stdout)
        self.assertEqual(payload["status"], "blocked")
        self.assertIn("current_exclusions_mismatch", payload["reason"])

    def test_failed_candidate_does_not_advance_current_or_lkg_and_reports_case(self) -> None:
        first = self.run_publish("--publish")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        current_before = (self.repo / "knowledge/indexes/current.json").read_text(encoding="utf-8")
        lkg_before = (self.repo / "knowledge/indexes/last-known-good.json").read_text(encoding="utf-8")
        suite_path = self.repo / "knowledge/evaluation/queries.v1.json"
        suite = json.loads(suite_path.read_text(encoding="utf-8"))
        suite["cases"][0]["must_include"] = [{"any_paths": ["missing-authority.md"]}]
        suite_path.write_text(json.dumps(suite, indent=2) + "\n", encoding="utf-8")
        subprocess.check_call(["git", "add", str(suite_path.relative_to(self.repo))], cwd=self.repo)
        subprocess.check_call(["git", "commit", "-m", "break evaluation"], cwd=self.repo, stdout=subprocess.DEVNULL)
        failed = self.run_publish("--publish")
        self.assertNotEqual(failed.returncode, 0)
        payload = json.loads(failed.stdout)
        self.assertEqual(payload["reason"], "repository_query_evaluation_failed")
        evaluation = payload["details"]["evaluation"]
        self.assertEqual(evaluation["status"], "failed")
        self.assertEqual(evaluation["failures"][0]["id"], "repository-rules")
        self.assertEqual(evaluation["failures"][0]["query"], "Repository Guide startup rules")
        self.assertTrue(evaluation["failures"][0]["missing_expectations"])
        self.assertEqual((self.repo / "knowledge/indexes/current.json").read_text(encoding="utf-8"), current_before)
        self.assertEqual((self.repo / "knowledge/indexes/last-known-good.json").read_text(encoding="utf-8"), lkg_before)

    def test_restore_lkg_repairs_canonical_files(self) -> None:
        first = self.run_publish("--publish")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        catalog_path = self.repo / "knowledge/catalogs/repository-knowledge-catalog.v1.json"
        expected = catalog_path.read_text(encoding="utf-8")
        catalog_path.write_text("{}\n", encoding="utf-8")
        broken = self.run_publish("--check")
        self.assertNotEqual(broken.returncode, 0)
        restored = self.run_publish("--restore-lkg")
        self.assertEqual(restored.returncode, 0, restored.stdout + restored.stderr)
        self.assertEqual(catalog_path.read_text(encoding="utf-8"), expected)


if __name__ == "__main__":
    unittest.main()
