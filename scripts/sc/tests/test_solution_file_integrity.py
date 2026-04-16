#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


class SolutionFileIntegrityTests(unittest.TestCase):
    def test_game_solution_should_start_with_header_on_first_line(self) -> None:
        path = REPO_ROOT / "Game.sln"
        text = path.read_text(encoding="utf-8-sig")
        first_line = text.splitlines()[0] if text.splitlines() else ""

        self.assertEqual(
            "Microsoft Visual Studio Solution File, Format Version 12.00",
            first_line,
        )


if __name__ == "__main__":
    unittest.main()
