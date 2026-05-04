#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[3]
PY_DIR = REPO_ROOT / "scripts" / "python"
if str(PY_DIR) not in sys.path:
    sys.path.insert(0, str(PY_DIR))

import run_obligations_jitter_batch5x3 as jitter_batch  # noqa: E402
from _obligations_freeze_pipeline_steps import build_jitter_batch_command  # noqa: E402


class ObligationsFreezeCommandTests(unittest.TestCase):
    def test_jitter_extract_command_should_pass_delivery_profile_without_forcing_security_override(self) -> None:
        args = SimpleNamespace(
            timeout_sec=420,
            delivery_profile="standard",
            security_profile="",
            consensus_runs=1,
            min_obligations=0,
            garbled_gate="on",
            reuse_last_ok=False,
            explain_reuse_miss=False,
        )
        cmd = jitter_batch.build_extract_command(task_id=11, round_id="jitter-g1-r1", args=args)
        self.assertIn("--delivery-profile", cmd)
        self.assertIn("standard", cmd)
        self.assertNotIn("--security-profile", cmd)

    def test_jitter_extract_command_should_keep_explicit_security_override(self) -> None:
        args = SimpleNamespace(
            timeout_sec=420,
            delivery_profile="playable-ea",
            security_profile="strict",
            consensus_runs=1,
            min_obligations=0,
            garbled_gate="off",
            reuse_last_ok=True,
            explain_reuse_miss=True,
        )
        cmd = jitter_batch.build_extract_command(task_id=12, round_id="jitter-g1-r2", args=args)
        self.assertIn("--delivery-profile", cmd)
        self.assertIn("playable-ea", cmd)
        self.assertIn("--security-profile", cmd)
        self.assertIn("strict", cmd)
        self.assertIn("--reuse-last-ok", cmd)
        self.assertIn("--explain-reuse-miss", cmd)

    def test_pipeline_jitter_command_should_use_examples_tasks_file_when_real_taskmaster_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            examples_dir = root / "examples" / "taskmaster"
            examples_dir.mkdir(parents=True, exist_ok=True)
            for name, content in {
                "tasks.json": "{\"master\":{\"tasks\":[{\"id\":1}]}}\n".encode("utf-8").decode("unicode_escape"),
                "tasks_back.json": "[]\n".encode("utf-8").decode("unicode_escape"),
                "tasks_gameplay.json": "[]\n".encode("utf-8").decode("unicode_escape"),
            }.items():
                (examples_dir / name).write_text(content, encoding="utf-8")
            args = SimpleNamespace(
                task_ids="",
                tasks_file="",
                batch_size=5,
                rounds=3,
                start_group=1,
                end_group=0,
                timeout_sec=420,
                round_id_prefix="jitter",
                delivery_profile="fast-ship",
                security_profile="",
                consensus_runs=1,
                min_obligations=0,
                garbled_gate="on",
                auto_escalate="on",
                escalate_max_runs=3,
                max_schema_errors=5,
                reuse_last_ok=False,
                explain_reuse_miss=False,
            )
            raw_path = root / "logs" / "ci" / "2026-03-08" / "raw.json"
            cmd = build_jitter_batch_command(args, raw_path=raw_path, root=root)
        joined = " ".join(cmd)
        self.assertIn("examples/taskmaster/tasks.json", joined.replace(chr(92), "/"))
        self.assertIn("--delivery-profile", cmd)
        self.assertNotIn("--security-profile", cmd)


if __name__ == "__main__":
    unittest.main()
