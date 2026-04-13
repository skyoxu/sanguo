#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

import llm_check_subtasks_coverage as subtasks_script  # noqa: E402


class SubtasksCoverageBackendTests(unittest.TestCase):
    def test_apply_delivery_profile_defaults_should_resolve_default_llm_backend(self) -> None:
        args = subtasks_script.apply_delivery_profile_defaults(
            subtasks_script.argparse.Namespace(
                delivery_profile="fast-ship",
                llm_backend=None,
                timeout_sec=None,
                max_prompt_chars=None,
                consensus_runs=None,
                garbled_gate=None,
            )
        )

        self.assertEqual("codex-cli", args.llm_backend)

    def test_main_should_forward_explicit_llm_backend(self) -> None:
        with tempfile.TemporaryDirectory(dir=str(REPO_ROOT)) as td:
            out_dir = Path(td) / "subtasks-coverage"
            triplet = SimpleNamespace(
                task_id="17",
                master={
                    "title": "Task17",
                    "subtasks": [{"id": "17.1", "title": "Subtask A", "details": "Need semantic coverage"}],
                },
                back={"acceptance": ["ACC:T17.1 cover subtask a."]},
                gameplay=None,
            )
            seen: list[str] = []

            def _fake_run_codex_exec(*, backend: str = "codex-cli", prompt: str, out_last_message: Path, timeout_sec: int, repo_root_path: Path):  # noqa: ARG001
                seen.append(backend)
                out_last_message.write_text(
                    json.dumps(
                        {
                            "task_id": "17",
                            "status": "ok",
                            "subtasks": [
                                {
                                    "id": "17.1",
                                    "title": "Subtask A",
                                    "covered": True,
                                    "matches": [{"view": "back", "acceptance_index": 1, "acceptance_excerpt": "ACC:T17.1 cover subtask a."}],
                                    "reason": "covered",
                                }
                            ],
                            "uncovered_subtask_ids": [],
                            "notes": [],
                        },
                        ensure_ascii=False,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                return 0, "trace", ["openai-api", "gpt-5"]

            argv = [
                "llm_check_subtasks_coverage.py",
                "--task-id",
                "17",
                "--garbled-gate",
                "off",
                "--llm-backend",
                "openai-api",
            ]
            with (
                patch.object(subtasks_script, "resolve_triplet", return_value=triplet),
                patch.object(subtasks_script, "ci_dir", return_value=out_dir),
                patch.object(subtasks_script, "run_codex_exec", side_effect=_fake_run_codex_exec),
                patch.object(sys, "argv", argv),
            ):
                rc = subtasks_script.main()
                summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))

            self.assertEqual(0, rc)
            self.assertEqual(["openai-api"], seen)
            self.assertEqual("openai-api", summary["llm_backend"])


if __name__ == "__main__":
    unittest.main()
