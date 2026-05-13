#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
TASKMASTER_DIR = REPO_ROOT / ".taskmaster" / "tasks"


class TaskmasterFixtureConcurrencyTests(unittest.TestCase):
    def test_staged_triplet_should_restore_real_taskmaster_dir_after_parallel_users_exit(self) -> None:
        snapshot = {
            path.name: path.read_text(encoding="utf-8")
            for path in TASKMASTER_DIR.iterdir()
            if path.is_file()
        }

        worker = textwrap.dedent(
            """
            import sys
            import time
            from pathlib import Path

            repo_root = Path(sys.argv[1])
            tests_dir = repo_root / "scripts" / "sc" / "tests"
            if str(tests_dir) not in sys.path:
                sys.path.insert(0, str(tests_dir))

            from _taskmaster_fixture import staged_taskmaster_triplet

            with staged_taskmaster_triplet(include_task1=True):
                time.sleep(0.75)
            """
        ).strip()

        with tempfile.TemporaryDirectory() as td:
            worker_path = Path(td) / "fixture_worker.py"
            worker_path.write_text(worker + "\n", encoding="utf-8", newline="\n")

            proc1 = subprocess.Popen([sys.executable, str(worker_path), str(REPO_ROOT)], cwd=str(REPO_ROOT))
            proc2 = subprocess.Popen([sys.executable, str(worker_path), str(REPO_ROOT)], cwd=str(REPO_ROOT))
            rc1 = proc1.wait(timeout=30)
            rc2 = proc2.wait(timeout=30)

        self.assertEqual(0, rc1)
        self.assertEqual(0, rc2)
        self.assertTrue(TASKMASTER_DIR.exists(), "real .taskmaster/tasks directory should be restored after parallel fixture users exit")

        current = {
            path.name: path.read_text(encoding="utf-8")
            for path in TASKMASTER_DIR.iterdir()
            if path.is_file()
        }
        self.assertEqual(snapshot, current)


if __name__ == "__main__":
    unittest.main()
