#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

import _acceptance_steps_quality as quality_steps  # noqa: E402


class AcceptanceStepsQualityTests(unittest.TestCase):
    def test_step_perf_budget_should_use_latest_log_with_perf_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            older_dir = root / "logs" / "ci" / "2026-03-31" / "smoke" / "older"
            newer_dir = root / "logs" / "ci" / "2026-03-31" / "smoke" / "newer"
            older_dir.mkdir(parents=True, exist_ok=True)
            newer_dir.mkdir(parents=True, exist_ok=True)
            out_dir = root / "logs" / "ci" / "2026-03-31" / "sc-acceptance-check-task-56"
            out_dir.mkdir(parents=True, exist_ok=True)

            older_log = older_dir / "headless.log"
            older_log.write_text(
                "[TEMPLATE_SMOKE_READY]\n"
                "[PERF] frames=128 avg_ms=7.83 p50_ms=6.90 p95_ms=6.94 p99_ms=16.05\n",
                encoding="utf-8",
            )
            newer_log = newer_dir / "headless.log"
            newer_log.write_text("[TEMPLATE_SMOKE_READY]\n", encoding="utf-8")

            os.utime(older_log, (1_000, 1_000))
            os.utime(newer_log, (2_000, 2_000))

            with mock.patch.object(quality_steps, "repo_root", return_value=root):
                step = quality_steps.step_perf_budget(out_dir, max_p95_ms=33)

            self.assertEqual("ok", step.status)
            self.assertEqual("logs/ci/2026-03-31/smoke/older/headless.log", step.details["headless_log"])
            self.assertEqual(6.94, step.details["p95_ms"])


if __name__ == "__main__":
    unittest.main()
