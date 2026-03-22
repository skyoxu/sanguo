#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))


def _load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


refs = _load_module("sc_test_refs_module", "scripts/sc/_sc_test_refs.py")


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


class ScTestRefsTests(unittest.TestCase):
    def test_task_scoped_cs_refs_should_fallback_to_examples_triplet(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cs_file = root / "Game.Core.Tests" / "Tasks" / "Task11FeatureTests.cs"
            cs_file.parent.mkdir(parents=True, exist_ok=True)
            cs_file.write_text("public sealed class Task11FeatureTests {}\n", encoding="utf-8")
            _write_json(root / "examples" / "taskmaster" / "tasks_back.json", [{"taskmaster_id": 11, "test_refs": ["Game.Core.Tests/Tasks/Task11FeatureTests.cs"]}])
            _write_json(root / "examples" / "taskmaster" / "tasks_gameplay.json", [])
            _write_json(root / "examples" / "taskmaster" / "tasks.json", {"master": {"tasks": [{"id": 11, "status": "in-progress"}]}})

            original_repo_root = refs.repo_root
            try:
                refs.repo_root = lambda: root
                actual = refs.task_scoped_cs_refs(task_id="11")
            finally:
                refs.repo_root = original_repo_root

        self.assertEqual(["Game.Core.Tests/Tasks/Task11FeatureTests.cs"], actual)


if __name__ == "__main__":
    unittest.main()
