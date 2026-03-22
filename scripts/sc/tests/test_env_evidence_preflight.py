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

import _env_evidence_preflight as env_preflight  # noqa: E402


class EnvEvidencePreflightTests(unittest.TestCase):
    def test_discover_packages_lock_files_should_find_root_and_project_level_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            root_lock = root / "packages.lock.json"
            project_lock = root / "Game.Core" / "packages.lock.json"
            root_lock.write_text("{}\n", encoding="utf-8")
            project_lock.parent.mkdir(parents=True, exist_ok=True)
            project_lock.write_text("{}\n", encoding="utf-8")

            actual = env_preflight._discover_packages_lock_files(root)

        self.assertEqual([root_lock, project_lock], actual)

    def test_discover_packages_lock_files_should_ignore_generated_directories(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            keep = root / "Game.Core.Tests" / "packages.lock.json"
            ignore_obj = root / "Game.Core.Tests" / "obj" / "packages.lock.json"
            ignore_logs = root / "logs" / "ci" / "packages.lock.json"
            keep.parent.mkdir(parents=True, exist_ok=True)
            ignore_obj.parent.mkdir(parents=True, exist_ok=True)
            ignore_logs.parent.mkdir(parents=True, exist_ok=True)
            keep.write_text("{}\n", encoding="utf-8")
            ignore_obj.write_text("{}\n", encoding="utf-8")
            ignore_logs.write_text("{}\n", encoding="utf-8")

            actual = env_preflight._discover_packages_lock_files(root)

        self.assertEqual([keep], actual)

    def test_build_utf8_checked_files_should_include_checklist_once(self) -> None:
        errors: list[str] = []
        files = env_preflight._build_utf8_checked_files(
            task_json_rel="logs/ci/2026-03-20/task-0001.json",
            checklist_rel="docs/acceptance-check-list.md",
            date="2026-03-20",
            errors=errors,
        )

        self.assertEqual(1, files.count("docs/acceptance-check-list.md"))
        self.assertEqual([], errors)

    def test_build_utf8_checked_files_should_append_missing_checklist_error_once(self) -> None:
        errors: list[str] = []
        files = env_preflight._build_utf8_checked_files(
            task_json_rel="logs/ci/2026-03-20/task-0001.json",
            checklist_rel="",
            date="2026-03-20",
            errors=errors,
        )

        self.assertEqual(0, files.count(""))
        self.assertEqual(["missing_acceptance_checklist"], errors)


if __name__ == "__main__":
    unittest.main()
