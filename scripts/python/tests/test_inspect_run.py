#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON_DIR = REPO_ROOT / "scripts" / "python"
SC_DIR = REPO_ROOT / "scripts" / "sc"
for candidate in (PYTHON_DIR, SC_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))


def _load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


inspect_run = _load_module("inspect_run_module", "scripts/python/inspect_run.py")


class InspectRunTests(unittest.TestCase):
    def test_inspect_run_artifacts_should_surface_planned_only_recovery_hints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)

            latest = root / "logs" / "ci" / "2026-04-08" / "sc-review-pipeline-task-14" / "latest.json"
            out_dir = root / "logs" / "ci" / "2026-04-08" / "sc-review-pipeline-task-14-planned-run"
            _write_json(
                latest,
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": "planned-run",
                    "status": "ok",
                    "latest_out_dir": str(out_dir),
                    "summary_path": str(out_dir / "summary.json"),
                    "execution_context_path": str(out_dir / "execution-context.json"),
                    "repair_guide_json_path": str(out_dir / "repair-guide.json"),
                    "run_events_path": str(out_dir / "run-events.jsonl"),
                },
            )
            _write_json(
                out_dir / "summary.json",
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": "planned-run",
                    "status": "ok",
                    "run_type": "planned-only",
                    "reason": "pipeline_clean",
                    "steps": [
                        {"name": "sc-test", "status": "planned"},
                        {"name": "sc-acceptance-check", "status": "planned"},
                    ],
                    "finished_at_utc": "2026-04-08T10:00:00+00:00",
                },
            )
            _write_json(
                out_dir / "execution-context.json",
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": "planned-run",
                    "status": "ok",
                    "delivery_profile": "fast-ship",
                    "security_profile": "host-safe",
                    "diagnostics": {},
                },
            )
            _write_json(
                out_dir / "repair-guide.json",
                {
                    "status": "not-needed",
                    "task_id": "14",
                    "summary_status": "ok",
                    "failed_step": "",
                    "recommendations": [],
                },
            )
            (out_dir / "run-events.jsonl").write_text(
                json.dumps(
                    {
                        "event": "run_completed",
                        "task_id": "14",
                        "run_id": "planned-run",
                        "status": "ok",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
                newline="\n",
            )

            rc, payload = inspect_run.inspect_run_artifacts(repo_root=root, kind="pipeline", task_id="14")

            self.assertEqual(1, rc)
            self.assertEqual("fail", payload["status"])
            self.assertEqual("planned_only_incomplete", payload["latest_summary_signals"]["reason"])
            self.assertEqual("planned-only", payload["latest_summary_signals"]["run_type"])
            self.assertEqual("planned_only_incomplete", payload["latest_summary_signals"]["artifact_integrity_kind"])
            self.assertEqual("rerun", payload["chapter6_hints"]["next_action"])
            self.assertEqual("artifact_integrity", payload["chapter6_hints"]["blocked_by"])
            self.assertIn("planned-only evidence", payload["recommended_action_why"])
            self.assertIn("rerun 6.7", payload["recommended_action_why"])

    def test_resolve_latest_path_should_prefer_real_bundle_over_newer_dry_run_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)

            real_latest = root / "logs" / "ci" / "2026-04-07" / "sc-review-pipeline-task-14" / "latest.json"
            real_out_dir = root / "logs" / "ci" / "2026-04-07" / "sc-review-pipeline-task-14-real-run"
            _write_json(
                real_latest,
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": "real-run",
                    "status": "ok",
                    "latest_out_dir": str(real_out_dir),
                    "summary_path": str(real_out_dir / "summary.json"),
                },
            )
            _write_json(
                real_out_dir / "summary.json",
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": "real-run",
                    "status": "ok",
                    "run_type": "full",
                    "reason": "pipeline_clean",
                    "steps": [{"name": "sc-test", "status": "ok"}],
                    "finished_at_utc": "2026-04-07T10:00:00+00:00",
                },
            )

            dry_latest = root / "logs" / "ci" / "2026-04-08" / "sc-review-pipeline-task-14" / "latest.json"
            dry_out_dir = root / "logs" / "ci" / "2026-04-08" / "sc-review-pipeline-task-14-dry-run"
            _write_json(
                dry_latest,
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": "dry-run",
                    "status": "fail",
                    "latest_out_dir": str(dry_out_dir),
                    "summary_path": str(dry_out_dir / "summary.json"),
                },
            )
            _write_json(
                dry_out_dir / "summary.json",
                {
                    "cmd": "sc-review-pipeline",
                    "task_id": "14",
                    "run_id": "dry-run",
                    "status": "fail",
                    "run_type": "planned-only",
                    "reason": "planned_only_incomplete",
                    "steps": [
                        {"name": "sc-test", "status": "planned"},
                        {"name": "sc-acceptance-check", "status": "planned"},
                    ],
                    "finished_at_utc": "2026-04-08T10:00:00+00:00",
                },
            )

            os.utime(real_latest, (1712560000, 1712560000))
            os.utime(dry_latest, (1712646400, 1712646400))

            resolved = inspect_run._resolve_latest_path(root, latest="", kind="pipeline", task_id="14", run_id="")
            self.assertEqual(real_latest.resolve(), resolved)


if __name__ == "__main__":
    unittest.main()
