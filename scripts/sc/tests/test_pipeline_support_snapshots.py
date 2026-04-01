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

import _pipeline_support as pipeline_support  # noqa: E402


class PipelineSupportSnapshotTests(unittest.TestCase):
    def test_run_step_should_snapshot_child_artifacts_under_pipeline_out_dir(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pipeline_out_dir = root / "logs" / "ci" / "2026-03-31" / "sc-review-pipeline-task-56-run-a"
            pipeline_out_dir.mkdir(parents=True, exist_ok=True)
            child_out_dir = root / "logs" / "ci" / "2026-03-31" / "sc-acceptance-check-task-56"
            child_out_dir.mkdir(parents=True, exist_ok=True)
            (child_out_dir / "summary.json").write_text(json.dumps({"status": "fail"}), encoding="utf-8")
            (child_out_dir / "report.md").write_text("# report\n", encoding="utf-8")

            with (
                mock.patch.object(pipeline_support, "repo_root", return_value=root),
                mock.patch.object(
                    pipeline_support,
                    "run_cmd",
                    return_value=(1, f"SC_ACCEPTANCE status=fail out={child_out_dir}\n"),
                ),
            ):
                step = pipeline_support.run_step(
                    out_dir=pipeline_out_dir,
                    name="sc-acceptance-check",
                    cmd=["py", "-3", "scripts/sc/acceptance_check.py"],
                    timeout_sec=60,
                )

            snapshot_dir = pipeline_out_dir / "child-artifacts" / "sc-acceptance-check"
            self.assertEqual(str(snapshot_dir), step["reported_out_dir"])
            self.assertEqual(str(snapshot_dir / "summary.json"), step["summary_file"])
            self.assertTrue((snapshot_dir / "summary.json").exists())
            self.assertTrue((snapshot_dir / "report.md").exists())

    def test_run_step_should_not_recursively_snapshot_existing_pipeline_child_dir(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pipeline_out_dir = root / "logs" / "ci" / "2026-03-31" / "sc-review-pipeline-task-56-run-a"
            child_dir = pipeline_out_dir / "child-artifacts" / "sc-acceptance-check"
            child_dir.mkdir(parents=True, exist_ok=True)
            (child_dir / "summary.json").write_text(json.dumps({"status": "ok"}), encoding="utf-8")

            with (
                mock.patch.object(pipeline_support, "repo_root", return_value=root),
                mock.patch.object(
                    pipeline_support,
                    "run_cmd",
                    return_value=(0, f"SC_ACCEPTANCE status=ok out={child_dir}\n"),
                ),
            ):
                step = pipeline_support.run_step(
                    out_dir=pipeline_out_dir,
                    name="sc-acceptance-check",
                    cmd=["py", "-3", "scripts/sc/acceptance_check.py"],
                    timeout_sec=60,
                )

            self.assertEqual(str(child_dir.resolve()), step["reported_out_dir"])
            self.assertEqual(str((child_dir / "summary.json").resolve()), step["summary_file"])


if __name__ == "__main__":
    unittest.main()
