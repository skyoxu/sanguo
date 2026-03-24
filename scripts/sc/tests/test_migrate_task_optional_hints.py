#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PY_DIR = REPO_ROOT / "scripts" / "python"
sys.path.insert(0, str(PY_DIR))

import migrate_task_optional_hints_to_views as migrate_optional  # noqa: E402


class MigrateTaskOptionalHintsTests(unittest.TestCase):
    def test_is_optional_hint_line_requires_context_for_absolute_path(self) -> None:
        self.assertFalse(migrate_optional._is_optional_hint_line(r"C:\repo\logs\demo.txt"))
        self.assertTrue(migrate_optional._is_optional_hint_line(r"Hint path: C:\repo\logs\demo.txt"))

    def test_canonical_task_id_normalizes_numeric_and_preserves_named(self) -> None:
        self.assertEqual("54", migrate_optional._canonical_task_id("054"))
        self.assertEqual("54", migrate_optional._canonical_task_id(54))
        self.assertEqual("T54", migrate_optional._canonical_task_id("T54"))
        self.assertEqual("", migrate_optional._canonical_task_id(""))


if __name__ == "__main__":
    unittest.main()

