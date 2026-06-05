#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

from _unit_metrics import collect_unit_metrics  # noqa: E402


TRX = """<?xml version="1.0" encoding="utf-8"?>
<TestRun xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010">
  <Results>
    <UnitTestResult testName="Game.Core.Tests.Tasks.ExampleTests.ShouldPass" outcome="Passed" />
  </Results>
  <ResultSummary outcome="Completed">
    <Counters total="1" executed="1" passed="1" failed="0" />
  </ResultSummary>
</TestRun>
"""


class UnitMetricsTests(unittest.TestCase):
    def test_collect_unit_metrics_prefers_stable_copied_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            unit_dir = root / "logs" / "unit" / "2026-06-04"
            source_dir = root / "Game.Core.Tests" / "TestResults"
            unit_dir.mkdir(parents=True)
            source_dir.mkdir(parents=True)

            stable_trx = unit_dir / "tests.trx"
            source_trx = source_dir / "tests.trx"
            stable_trx.write_text(TRX, encoding="utf-8")
            source_trx.write_text("<TestRun />", encoding="utf-8")
            stable_coverage = unit_dir / "coverage.cobertura.xml"
            source_coverage = source_dir / "coverage.cobertura.xml"
            stable_coverage.write_text("<coverage />", encoding="utf-8")
            source_coverage.write_text("<coverage />", encoding="utf-8")
            (unit_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "threshold_ok": True,
                        "coverage": {"line_pct": 90.0, "branch_pct": 80.0},
                        "artifacts_selected": {
                            "trx": str(source_trx),
                            "coverage": str(source_coverage),
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            metrics = collect_unit_metrics(tests_all_log=None, fallback_unit_dir=unit_dir)

        self.assertIsNotNone(metrics)
        self.assertEqual(str(stable_trx), metrics["trx"])
        self.assertEqual(str(stable_coverage), metrics["coverage_cobertura"])
        self.assertEqual(1, metrics["tests"]["executed"])


if __name__ == "__main__":
    unittest.main()
