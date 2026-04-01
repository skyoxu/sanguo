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


jitter = _load_module("obligations_jitter_batch_module", "scripts/python/run_obligations_jitter_batch5x3.py")
freeze = _load_module("obligations_freeze_pipeline_module", "scripts/python/run_obligations_freeze_pipeline.py")


class ObligationsFreezeDeliveryProfileTests(unittest.TestCase):
    def test_jitter_build_extract_command_should_forward_delivery_profile(self) -> None:
        args = mock.Mock()
        args.delivery_profile = "standard"
        args.security_profile = None
        args.consensus_runs = 1
        args.min_obligations = 0
        args.garbled_gate = "on"
        args.auto_escalate = "on"
        args.escalate_max_runs = 3
        args.max_schema_errors = 5
        args.reuse_last_ok = True
        args.explain_reuse_miss = True

        cmd = jitter.build_extract_command(
            task_id=42,
            timeout_sec=420,
            round_id="jitter-g01-r01-t42",
            args=args,
        )

        self.assertIn("--delivery-profile", cmd)
        self.assertEqual("standard", cmd[cmd.index("--delivery-profile") + 1])

    def test_freeze_main_should_forward_delivery_profile_to_jitter_step(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "freeze"
            captured_cmds: list[list[str]] = []

            def _fake_run_step(step_name: str, cmd: list[str], _out_dir: Path, timeout_sec: int):
                captured_cmds.append(list(cmd))
                return {
                    "name": step_name,
                    "status": "ok",
                    "rc": 0,
                    "cmd": list(cmd),
                    "log": str(_out_dir / f"{step_name}.log"),
                }

            argv = [
                "run_obligations_freeze_pipeline.py",
                "--out-dir",
                str(out_dir),
                "--task-ids",
                "1,2,3",
                "--delivery-profile",
                "standard",
            ]

            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(freeze, "run_step", side_effect=_fake_run_step), \
                mock.patch.object(freeze, "parse_eval_aggregate", return_value={"judgable": True, "freeze_gate_pass": True}):
                rc = freeze.main()

            self.assertEqual(0, rc)
            self.assertTrue(captured_cmds)
            jitter_cmd = captured_cmds[0]
            self.assertIn("--delivery-profile", jitter_cmd)
            self.assertEqual("standard", jitter_cmd[jitter_cmd.index("--delivery-profile") + 1])
            payload = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("standard", payload["delivery_profile"])


if __name__ == "__main__":
    unittest.main()
