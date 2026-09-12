from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
PYTHON_DIR = ROOT / "scripts" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

import generate_knowledge_links as module


class GenerateKnowledgeLinksTests(unittest.TestCase):
    def test_full_rebuild_replaces_stale_catalog_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base = root / "logs/ci/project-health-knowledge"
            base.mkdir(parents=True)
            (base / "latest.json").write_text(json.dumps({
                "revision": "a" * 40,
                "tasks": [{"task": {"id": 192, "title": "Main Menu", "test_refs": []}}],
            }), encoding="utf-8")
            catalog = root / "docs/knowledge/catalog/knowledge-catalog.json"
            catalog.parent.mkdir(parents=True)
            catalog.write_text(json.dumps({
                "schema_version": "1.0",
                "project": "newrouge",
                "entries": [{"id": "scene:115:Reward", "task_id": "115", "path": "Reward.tscn"}],
                "last_scan_revision": None,
            }), encoding="utf-8")
            navigation = {
                "configs": [{"path": "Game.Core/Data/sanguo.json", "focus": "core"}],
                "assets": [], "scenes": [], "code": [],
            }
            with mock.patch.object(module, "base_dir", return_value=base), mock.patch.object(module, "build_navigation", return_value=navigation):
                result = module.generate(root)
            self.assertEqual(result["entries"], 1)
            rebuilt = json.loads(catalog.read_text(encoding="utf-8"))
            self.assertEqual(rebuilt["project"], "sanguo")
            self.assertEqual([entry["task_id"] for entry in rebuilt["entries"]], ["192"])
            self.assertNotIn("Reward", json.dumps(rebuilt))

    def test_cli_without_task_ids_requests_full_rebuild(self) -> None:
        with mock.patch.object(module, "generate", return_value={"status": "ok"}) as generate:
            self.assertEqual(module.main([]), 0)
        self.assertIsNone(generate.call_args.args[1])


if __name__ == "__main__":
    unittest.main()
