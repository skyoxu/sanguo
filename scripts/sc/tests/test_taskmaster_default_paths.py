#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

import _taskmaster as taskmaster  # noqa: E402
from _taskmaster_paths import resolve_default_task_triplet_paths  # noqa: E402


class TaskmasterDefaultPathsTests(unittest.TestCase):
    def _write_triplet(self, base_dir: Path) -> tuple[Path, Path, Path]:
        base_dir.mkdir(parents=True, exist_ok=True)
        tasks_json = base_dir / "tasks.json"
        tasks_back = base_dir / "tasks_back.json"
        tasks_gameplay = base_dir / "tasks_gameplay.json"
        tasks_json.write_text(
            "{\"master\":{\"tasks\":[{\"id\":1,\"status\":\"in-progress\",\"title\":\"Task 1\",\"details\":\"demo\"}]}}\n".encode("utf-8").decode("unicode_escape"),
            encoding="utf-8",
        )
        tasks_back.write_text(
            "[{\"taskmaster_id\":1,\"acceptance\":[\"back\"]}]\n".encode("utf-8").decode("unicode_escape"),
            encoding="utf-8",
        )
        tasks_gameplay.write_text(
            "[{\"taskmaster_id\":1,\"acceptance\":[\"gameplay\"]}]\n".encode("utf-8").decode("unicode_escape"),
            encoding="utf-8",
        )
        return tasks_json, tasks_back, tasks_gameplay

    def test_should_fallback_to_examples_triplet_when_real_taskmaster_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            expected = self._write_triplet(root / "examples" / "taskmaster")
            actual = resolve_default_task_triplet_paths(root)
        self.assertEqual(expected, actual)

    def test_should_prefer_real_taskmaster_triplet_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_triplet(root / "examples" / "taskmaster")
            expected = self._write_triplet(root / ".taskmaster" / "tasks")
            actual = resolve_default_task_triplet_paths(root)
        self.assertEqual(expected, actual)

    def test_default_paths_should_follow_resolved_triplet_paths(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            expected = self._write_triplet(root / "examples" / "taskmaster")
            original_repo_root = taskmaster.repo_root
            try:
                taskmaster.repo_root = lambda: root
                actual = taskmaster.default_paths()
            finally:
                taskmaster.repo_root = original_repo_root
        self.assertEqual(expected, actual)

    def test_resolve_triplet_should_read_examples_fallback_triplet(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_triplet(root / "examples" / "taskmaster")
            original_repo_root = taskmaster.repo_root
            try:
                taskmaster.repo_root = lambda: root
                triplet = taskmaster.resolve_triplet()
            finally:
                taskmaster.repo_root = original_repo_root
        self.assertEqual("1", triplet.task_id)
        self.assertTrue(Path(triplet.tasks_json_path).as_posix().endswith("examples/taskmaster/tasks.json"))
        self.assertEqual(["back"], list((triplet.back or {}).get("acceptance") or []))
        self.assertEqual(["gameplay"], list((triplet.gameplay or {}).get("acceptance") or []))


if __name__ == "__main__":
    unittest.main()
