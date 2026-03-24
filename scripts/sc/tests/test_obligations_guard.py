#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
sys.path.insert(0, str(SC_DIR))

from _obligations_guard import apply_deterministic_guards, _contains_excerpt  # noqa: E402


class ObligationsGuardTests(unittest.TestCase):
    def test_contains_excerpt_direct_match(self) -> None:
        raw = "Create main menu scene with new run and continue options."
        norm = " ".join(raw.split())
        matched, stripped = _contains_excerpt(raw, raw, norm)
        self.assertTrue(matched)
        self.assertFalse(stripped)

    def test_contains_excerpt_prefix_stripped_match_for_long_english(self) -> None:
        raw = "Create main menu scene with new run and continue options."
        norm = " ".join(raw.split())
        excerpt = "Task: T14 Create main menu scene with new run and continue options."
        matched, stripped = _contains_excerpt(excerpt, raw, norm)
        self.assertTrue(matched)
        self.assertTrue(stripped)

    def test_contains_excerpt_prefix_stripped_rejects_short_excerpt(self) -> None:
        raw = "menu continue"
        norm = " ".join(raw.split())
        excerpt = "Task: T14 menu continue"
        matched, stripped = _contains_excerpt(excerpt, raw, norm)
        self.assertFalse(matched)
        self.assertFalse(stripped)

    def test_contains_excerpt_prefix_stripped_match_for_long_chinese(self) -> None:
        raw = "\u5b9e\u73b0\u654c\u4eba\u610f\u56fe\u663e\u793a\u548c\u9884\u89c8\u754c\u9762\u5e76\u66f4\u65b0\u56de\u5408\u6570\u636e\u3002"
        norm = " ".join(raw.split())
        excerpt = "\u4efb\u52a1\uff1aT41 \u5b9e\u73b0\u654c\u4eba\u610f\u56fe\u663e\u793a\u548c\u9884\u89c8\u754c\u9762\u5e76\u66f4\u65b0\u56de\u5408\u6570\u636e\u3002"
        matched, stripped = _contains_excerpt(excerpt, raw, norm)
        self.assertTrue(matched)
        self.assertTrue(stripped)

    def test_apply_deterministic_guards_counts_prefix_stripped_matches(self) -> None:
        obj = {
            "status": "ok",
            "obligations": [
                {
                    "id": "O1",
                    "source": "master",
                    "kind": "godot",
                    "text": "Main menu options must exist.",
                    "source_excerpt": "Task: T14 Create main menu scene with new run and continue options.",
                    "covered": True,
                }
            ],
            "notes": [],
        }
        source_blocks = ["Create main menu scene with new run and continue options."]
        out, det_issues, hard_uncovered, advisory_uncovered = apply_deterministic_guards(
            obj=obj,
            subtasks=[],
            min_obligations=0,
            source_text_blocks=source_blocks,
            security_profile="host-safe",
        )
        self.assertEqual("ok", out.get("status"))
        self.assertEqual([], det_issues)
        self.assertEqual([], hard_uncovered)
        self.assertEqual([], advisory_uncovered)
        self.assertEqual(1, out.get("source_excerpt_prefix_stripped_matches"))


if __name__ == "__main__":
    unittest.main()

