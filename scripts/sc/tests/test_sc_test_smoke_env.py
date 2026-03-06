import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "sc" / "test.py"
SPEC = importlib.util.spec_from_file_location("sc_test_script", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ScTestSmokeEnvTests(unittest.TestCase):
    def test_run_unit_should_forward_no_coverage_gate_env(self) -> None:
        observed = {}

        def fake_run_cmd(cmd, *, cwd=None, timeout_sec=0):
            observed["cmd"] = list(cmd)
            observed["skip_gate"] = os.environ.get("SC_ACCEPTANCE_NO_COVERAGE_GATE")
            return 0, "RUN_DOTNET status=ok"

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir)
            original_skip_gate = os.environ.get("SC_ACCEPTANCE_NO_COVERAGE_GATE")
            os.environ.pop("SC_ACCEPTANCE_NO_COVERAGE_GATE", None)
            try:
                with patch.object(MODULE, "run_cmd", side_effect=fake_run_cmd):
                    result = MODULE.run_unit(out_dir, "Game.sln", "Debug", run_id="run123", no_coverage_gate=True)
            finally:
                if original_skip_gate is None:
                    os.environ.pop("SC_ACCEPTANCE_NO_COVERAGE_GATE", None)
                else:
                    os.environ["SC_ACCEPTANCE_NO_COVERAGE_GATE"] = original_skip_gate

        self.assertEqual(0, result["rc"])
        self.assertEqual("1", observed.get("skip_gate"))
        self.assertNotIn("SC_ACCEPTANCE_NO_COVERAGE_GATE", os.environ)

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


if __name__ == "__main__":
    unittest.main()
