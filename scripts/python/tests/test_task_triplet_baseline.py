#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON_DIR = REPO_ROOT / "scripts" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))


def _load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class TaskTripletBaselineTests(unittest.TestCase):
    def test_run_task_triplet_baseline_should_write_unified_summary(self) -> None:
        mod = _load_module("run_task_triplet_baseline_test", "scripts/python/run_task_triplet_baseline.py")

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_path = root / "logs" / "ci" / "2026-05-12" / "task-generation" / "summary.json"

            def fake_repo_root() -> Path:
                return root

            def fake_run_step(*, name: str, command: list[str], cwd: Path, summary_path: Path | None = None):
                if summary_path is not None:
                    summary_path.parent.mkdir(parents=True, exist_ok=True)
                    summary_path.write_text(json.dumps({"status": "ok"}) + "\n", encoding="utf-8")
                return {
                    "name": name,
                    "command": command,
                    "returncode": 0,
                    "status": "ok",
                    "stdout": "ok",
                    "stderr": "",
                    **({"summary_path": summary_path.as_posix()} if summary_path is not None else {}),
                }

            with mock.patch.object(mod, "_repo_root", side_effect=fake_repo_root), \
                 mock.patch.object(mod, "_run_step", side_effect=fake_run_step), \
                 mock.patch.object(sys, "argv", ["run_task_triplet_baseline.py", "--out", str(out_path)]):
                rc = mod.main()

            self.assertEqual(0, rc)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual("task-generation.baseline-summary.v1", payload["schema"])
            self.assertEqual("ok", payload["status"])
            self.assertEqual("3.8-3.9", payload["chapter"])
            self.assertEqual(
                [
                    "task_links_validate",
                    "check_tasks_all_refs",
                    "validate_task_master_triplet",
                ],
                [step["name"] for step in payload["steps"]],
            )
            self.assertEqual(
                "logs/ci/2026-05-12/task-generation/task-links-validate-summary.json",
                payload["artifacts"]["task_links_validate"],
            )


if __name__ == "__main__":
    unittest.main()
