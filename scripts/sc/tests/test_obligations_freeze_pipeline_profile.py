#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[3]
PY_DIR = REPO_ROOT / "scripts" / "python"
if str(PY_DIR) not in sys.path:
    sys.path.insert(0, str(PY_DIR))

import run_obligations_freeze_pipeline as pipeline_script  # noqa: E402


class ObligationsFreezePipelineProfileTests(unittest.TestCase):
    def test_init_pipeline_payload_should_include_delivery_and_security_profile(self) -> None:
        payload = pipeline_script._init_pipeline_payload(
            Path("out"),
            Path("raw.json"),
            Path("summary.json"),
            Path("summary.md"),
            Path("refreshed.json"),
            Path("refreshed.md"),
            Path("draft.json"),
            Path("draft.md"),
            Path("eval"),
            Path("promote.md"),
            delivery_profile="standard",
            security_profile="strict",
            security_override=False,
        )
        self.assertEqual("standard", payload.get("delivery_profile"))
        self.assertEqual("strict", payload.get("security_profile"))
        self.assertFalse(bool(payload.get("security_override")))

    def test_main_should_write_resolved_profiles_into_summary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-03-08" / "freeze-pipeline"
            raw_path = out_dir / "raw.json"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(json.dumps({"meta": {}, "rows": []}, ensure_ascii=False) + "\n", encoding="utf-8")

            def fake_run_step(step_name: str, cmd: list[str], out_dir_arg: Path, *, root: Path, timeout_sec: int) -> dict:
                if step_name == "evaluate":
                    eval_dir = out_dir_arg / "freeze-eval"
                    eval_dir.mkdir(parents=True, exist_ok=True)
                    (eval_dir / "summary.json").write_text(
                        json.dumps({"aggregate": {"judgable": True, "freeze_gate_pass": True}}, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                return {"name": step_name, "status": "ok", "rc": 0, "cmd": cmd, "log": str(out_dir_arg / f"{step_name}.log")}

            argv = [
                "run_obligations_freeze_pipeline.py",
                "--skip-jitter",
                "--raw",
                str(raw_path),
                "--out-dir",
                str(out_dir),
                "--delivery-profile",
                "playable-ea",
            ]
            with (
                patch.object(pipeline_script, "repo_root", return_value=root),
                patch.object(pipeline_script, "today_str", return_value="2026-03-08"),
                patch.object(pipeline_script, "run_step", side_effect=fake_run_step),
                patch.object(sys, "argv", argv),
            ):
                rc = pipeline_script.main()

            self.assertEqual(0, rc)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("playable-ea", summary.get("delivery_profile"))
            self.assertEqual("host-safe", summary.get("security_profile"))
            self.assertFalse(bool(summary.get("security_override")))


if __name__ == "__main__":
    unittest.main()
