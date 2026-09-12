from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, encoding="utf-8", capture_output=True, check=False)


class KnowledgeFreezeTests(unittest.TestCase):
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
            "scripts/python/prepare_knowledge_context.py",
            "scripts/python/freeze_knowledge_context.py",
            "scripts/python/publish_knowledge_catalog.py",
        ]:
            target = self.repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        suite = {
            "schema_version": "newrouge.knowledge-evaluation-suite.v1",
            "cases": [
                {
                    "id": "task-context",
                    "consumer": "chapter6",
                    "query": "taskmaster overlay refs acceptance linkage",
                    "must_include": [
                        {
                            "any_path_prefixes": [".taskmaster/tasks/"],
                            "domains": ["delivery"],
                        }
                    ],
                    "forbidden_path_prefixes": ["logs/"],
                }
            ],
        }
        suite_path = self.repo / "knowledge/evaluation/queries.v1.json"
        suite_path.parent.mkdir(parents=True, exist_ok=True)
        suite_path.write_text(json.dumps(suite, indent=2) + "\n", encoding="utf-8")
        files = {
            "AGENTS.md": "# Repository Guide\nRules.\n",
            "README.md": "# Game\nWindows Godot game.\n",
            "workflow.md": "# Workflow\nChapter 6 task loop.\n",
            "DELIVERY_PROFILE.md": "# Delivery\nfast-ship\n",
            "docs/PROJECT_DOCUMENTATION_INDEX.md": "# Index\nRoutes.\n",
            "docs/testing-framework.md": "# Tests\nxUnit and GdUnit4.\n",
            "docs/architecture/ADR_INDEX_GODOT.md": "# ADR Index Godot\nAccepted ADRs.\n",
            "docs/adr/ADR-0034-test.md": "# ADR-0034: Test\n\n- Status: Accepted\n",
            "docs/prd/game.md": "# Game PRD\nCard combat.\n",
            ".taskmaster/tasks/tasks.json": "{\"master\":{\"tasks\":[{\"id\":7,\"title\":\"overlay refs acceptance linkage\"}]}}\n",
        }
        for relative, text in files.items():
            path = self.repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        subprocess.check_call(["git", "add", "."], cwd=self.repo)
        subprocess.check_call(["git", "commit", "-m", "seed"], cwd=self.repo, stdout=subprocess.DEVNULL)
        published = run(sys.executable, "scripts/python/publish_knowledge_catalog.py", "--publish", cwd=self.repo)
        self.assertEqual(published.returncode, 0, published.stdout + published.stderr)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def bundle(self) -> dict:
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
        return bundle

    def inputs(self, bundle: dict, *, decision: str = "accepted", satisfies: list[str] | None = None) -> tuple[str, str]:
        candidate = bundle["candidates"][0]
        bundle_rel = "logs/ci/knowledge-context/chapter6.json"
        decisions_rel = "logs/ci/knowledge-context/chapter6.decisions.json"
        bundle_path = self.repo / bundle_rel
        bundle_path.parent.mkdir(parents=True, exist_ok=True)
        bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
        canonical = json.dumps(bundle, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        decision_set = {
            "schema_version": "newrouge.knowledge-consumption-decision-set.v1",
            "consumer": "chapter6",
            "request_id": bundle["request_id"],
            "source_bundle_sha256": "sha256:" + hashlib.sha256(canonical).hexdigest(),
            "decisions": [{
                "schema_version": "newrouge.knowledge-consumption-decision.v1",
                "consumer": "chapter6",
                "request_id": bundle["request_id"],
                "candidate": {"module_id": candidate["module_id"], "path": candidate["path"]},
                "decision": decision,
                "reason": "Explicit semantic fit for the synthetic task context.",
                "source_sha256": candidate["source_sha256"],
                "satisfies": satisfies if satisfies is not None else ["task-context", "implementation-authority"],
            }],
        }
        (self.repo / decisions_rel).write_text(json.dumps(decision_set), encoding="utf-8")
        return bundle_rel, decisions_rel

    def freeze(self, bundle_rel: str, decisions_rel: str) -> subprocess.CompletedProcess[str]:
        return run(
            sys.executable,
            "scripts/python/freeze_knowledge_context.py",
            "--bundle",
            bundle_rel,
            "--decisions",
            decisions_rel,
            "--task-id",
            "7",
            cwd=self.repo,
        )

    def test_freezes_only_explicit_complete_source_verified_context(self) -> None:
        bundle_rel, decisions_rel = self.inputs(self.bundle())
        completed = self.freeze(bundle_rel, decisions_rel)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        frozen = json.loads(completed.stdout)
        self.assertEqual(frozen["freeze_state"], "frozen")
        self.assertTrue(set(frozen["required_context_classes"]).issubset(set(frozen["satisfied_context_classes"])))
        self.assertEqual(len(frozen["accepted_sources"]), 1)
        self.assertTrue(frozen["context_id"].startswith("sha256:"))

    def test_chapter_freeze_requires_explicit_task_id(self) -> None:
        bundle_rel, decisions_rel = self.inputs(self.bundle())
        completed = run(
            sys.executable,
            "scripts/python/freeze_knowledge_context.py",
            "--bundle",
            bundle_rel,
            "--decisions",
            decisions_rel,
            cwd=self.repo,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("task_id_missing", json.loads(completed.stdout)["reason"])

    def test_rejected_candidate_cannot_satisfy_context(self) -> None:
        bundle_rel, decisions_rel = self.inputs(self.bundle(), decision="rejected")
        completed = self.freeze(bundle_rel, decisions_rel)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("rejected_candidate_cannot_satisfy", json.loads(completed.stdout)["reason"])

    def test_freeze_blocks_after_authority_ref_moves(self) -> None:
        bundle_rel, decisions_rel = self.inputs(self.bundle())
        (self.repo / "docs/prd/game.md").write_text("# Game PRD\nChanged.\n", encoding="utf-8")
        subprocess.check_call(["git", "add", "docs/prd/game.md"], cwd=self.repo)
        subprocess.check_call(["git", "commit", "-m", "move authority"], cwd=self.repo, stdout=subprocess.DEVNULL)
        completed = self.freeze(bundle_rel, decisions_rel)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("authority_ref_moved", json.loads(completed.stdout)["reason"])


if __name__ == "__main__":
    unittest.main()
