#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

import llm_review_needs_fix_fast as needs_fix_fast  # noqa: E402


class NeedsFixFastDeterministicReuseTests(unittest.TestCase):
    def test_try_reuse_latest_deterministic_step_should_reuse_matching_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-03-31" / "sc-review-pipeline-task-56-run-a"
            out_dir.mkdir(parents=True, exist_ok=True)
            latest_dir = root / "logs" / "ci" / "2026-03-31" / "sc-review-pipeline-task-56"
            latest_dir.mkdir(parents=True, exist_ok=True)
            (latest_dir / "latest.json").write_text(
                json.dumps(
                    {
                        "task_id": "56",
                        "run_id": "run-a",
                        "status": "ok",
                        "latest_out_dir": str(out_dir),
                        "summary_path": str(out_dir / "summary.json"),
                        "execution_context_path": str(out_dir / "execution-context.json"),
                    }
                ),
                encoding="utf-8",
            )
            (out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "task_id": "56",
                        "status": "ok",
                        "steps": [
                            {"name": "sc-test", "status": "ok", "rc": 0},
                            {"name": "sc-acceptance-check", "status": "ok", "rc": 0},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (out_dir / "execution-context.json").write_text(
                json.dumps(
                    {
                        "security_profile": "host-safe",
                        "git": {
                            "head": "abc123",
                            "status_short": [" M scripts/sc/_acceptance_steps.py"],
                        },
                    }
                ),
                encoding="utf-8",
            )

            with (
                mock.patch.object(needs_fix_fast, "repo_root", return_value=root),
                mock.patch.object(needs_fix_fast, "today_str", return_value="2026-03-31"),
                mock.patch.object(
                    needs_fix_fast,
                    "current_git_fingerprint",
                    return_value={"head": "abc123", "status_short": [" M scripts/sc/_acceptance_steps.py"]},
                ),
            ):
                step = needs_fix_fast.try_reuse_latest_deterministic_step(
                    task_id="56",
                    security_profile="host-safe",
                    skip_sc_test=False,
                    planned_cmd=["py", "-3", "scripts/sc/run_review_pipeline.py"],
                    out_dir=root / "logs" / "ci" / "2026-03-31" / "sc-needs-fix-fast-task-56",
                    script_start=0.0,
                    budget_min=20,
                )

            self.assertIsNotNone(step)
            assert step is not None
            self.assertEqual("reused", step["status"])
            self.assertEqual(0, int(step["rc"]))
            self.assertEqual(str(out_dir), step["reported_out_dir"])
            self.assertEqual("run-a", step["reused_run_id"])

    def test_try_reuse_latest_deterministic_step_should_reject_git_snapshot_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-03-31" / "sc-review-pipeline-task-56-run-a"
            out_dir.mkdir(parents=True, exist_ok=True)
            latest_dir = root / "logs" / "ci" / "2026-03-31" / "sc-review-pipeline-task-56"
            latest_dir.mkdir(parents=True, exist_ok=True)
            (latest_dir / "latest.json").write_text(
                json.dumps(
                    {
                        "task_id": "56",
                        "run_id": "run-a",
                        "status": "ok",
                        "latest_out_dir": str(out_dir),
                        "summary_path": str(out_dir / "summary.json"),
                        "execution_context_path": str(out_dir / "execution-context.json"),
                    }
                ),
                encoding="utf-8",
            )
            (out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "task_id": "56",
                        "status": "ok",
                        "steps": [
                            {"name": "sc-test", "status": "ok", "rc": 0},
                            {"name": "sc-acceptance-check", "status": "ok", "rc": 0},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (out_dir / "execution-context.json").write_text(
                json.dumps(
                    {
                        "security_profile": "host-safe",
                        "git": {"head": "abc123", "status_short": [" M scripts/sc/_acceptance_steps.py"]},
                    }
                ),
                encoding="utf-8",
            )

            with (
                mock.patch.object(needs_fix_fast, "repo_root", return_value=root),
                mock.patch.object(needs_fix_fast, "today_str", return_value="2026-03-31"),
                mock.patch.object(
                    needs_fix_fast,
                    "current_git_fingerprint",
                    return_value={"head": "def456", "status_short": [" M scripts/sc/_acceptance_steps.py"]},
                ),
            ):
                step = needs_fix_fast.try_reuse_latest_deterministic_step(
                    task_id="56",
                    security_profile="host-safe",
                    skip_sc_test=False,
                    planned_cmd=["py", "-3", "scripts/sc/run_review_pipeline.py"],
                    out_dir=root / "logs" / "ci" / "2026-03-31" / "sc-needs-fix-fast-task-56",
                    script_start=0.0,
                    budget_min=20,
                )

            self.assertIsNone(step)


if __name__ == "__main__":
    unittest.main()
