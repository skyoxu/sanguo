import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

import _sc_test_steps as MODULE  # noqa: E402


class ScTestSmokeEnvTests(unittest.TestCase):
    def test_run_smoke_should_enable_exit_on_ready_for_strict_mode(self) -> None:
        observed = {}

        def fake_run_cmd(cmd, *, cwd=None, timeout_sec=0):
            observed["cmd"] = list(cmd)
            observed["cwd"] = cwd
            observed["timeout_sec"] = timeout_sec
            observed["exit_on_ready"] = os.environ.get("GD_SMOKE_EXIT_ON_READY")
            observed["exit_delay"] = os.environ.get("GD_SMOKE_EXIT_DELAY_SEC")
            return 0, "SMOKE PASS (marker)"

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir)
            original_exit_on_ready = os.environ.get("GD_SMOKE_EXIT_ON_READY")
            original_exit_delay = os.environ.get("GD_SMOKE_EXIT_DELAY_SEC")
            os.environ.pop("GD_SMOKE_EXIT_ON_READY", None)
            os.environ.pop("GD_SMOKE_EXIT_DELAY_SEC", None)
            try:
                with patch.object(MODULE, "run_cmd", side_effect=fake_run_cmd):
                    result = MODULE.run_smoke(out_dir, "C:/Godot/Godot.exe", "res://Game.Godot/Scenes/Main.tscn", task_id="1")
            finally:
                if original_exit_on_ready is None:
                    os.environ.pop("GD_SMOKE_EXIT_ON_READY", None)
                else:
                    os.environ["GD_SMOKE_EXIT_ON_READY"] = original_exit_on_ready
                if original_exit_delay is None:
                    os.environ.pop("GD_SMOKE_EXIT_DELAY_SEC", None)
                else:
                    os.environ["GD_SMOKE_EXIT_DELAY_SEC"] = original_exit_delay

        self.assertEqual(0, result["rc"])
        self.assertEqual("1", observed.get("exit_on_ready"))
        self.assertEqual("0.25", observed.get("exit_delay"))
        self.assertIn("--strict", observed.get("cmd", []))
        self.assertNotIn("GD_SMOKE_EXIT_ON_READY", os.environ)
        self.assertNotIn("GD_SMOKE_EXIT_DELAY_SEC", os.environ)

    def test_run_smoke_should_not_force_exit_on_ready_when_not_strict(self) -> None:
        observed = {}

        def fake_run_cmd(cmd, *, cwd=None, timeout_sec=0):
            observed["cmd"] = list(cmd)
            observed["exit_on_ready"] = os.environ.get("GD_SMOKE_EXIT_ON_READY")
            observed["exit_delay"] = os.environ.get("GD_SMOKE_EXIT_DELAY_SEC")
            return 0, "SMOKE PASS (marker)"

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir)
            original_exit_on_ready = os.environ.get("GD_SMOKE_EXIT_ON_READY")
            original_exit_delay = os.environ.get("GD_SMOKE_EXIT_DELAY_SEC")
            os.environ.pop("GD_SMOKE_EXIT_ON_READY", None)
            os.environ.pop("GD_SMOKE_EXIT_DELAY_SEC", None)
            try:
                with patch.object(MODULE, "run_cmd", side_effect=fake_run_cmd):
                    result = MODULE.run_smoke(
                        out_dir,
                        "C:/Godot/Godot.exe",
                        "res://Game.Godot/Scenes/Main.tscn",
                        task_id="1",
                        strict=False,
                    )
            finally:
                if original_exit_on_ready is None:
                    os.environ.pop("GD_SMOKE_EXIT_ON_READY", None)
                else:
                    os.environ["GD_SMOKE_EXIT_ON_READY"] = original_exit_on_ready
                if original_exit_delay is None:
                    os.environ.pop("GD_SMOKE_EXIT_DELAY_SEC", None)
                else:
                    os.environ["GD_SMOKE_EXIT_DELAY_SEC"] = original_exit_delay

        self.assertEqual(0, result["rc"])
        self.assertEqual(None, observed.get("exit_on_ready"))
        self.assertEqual(None, observed.get("exit_delay"))
        self.assertNotIn("--strict", observed.get("cmd", []))
        self.assertNotIn("GD_SMOKE_EXIT_ON_READY", os.environ)
        self.assertNotIn("GD_SMOKE_EXIT_DELAY_SEC", os.environ)


if __name__ == "__main__":
    unittest.main()
