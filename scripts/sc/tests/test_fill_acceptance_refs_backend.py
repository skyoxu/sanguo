#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

import llm_fill_acceptance_refs as fill_refs_script  # noqa: E402


class FillAcceptanceRefsBackendTests(unittest.TestCase):
    def test_run_consensus_for_task_should_forward_explicit_llm_backend(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            seen: list[str] = []

            def _fake_run_codex_exec(*, backend: str = "codex-cli", root: Path, prompt: str, out_last_message: Path, timeout_sec: int):  # noqa: ARG001
                seen.append(backend)
                out_last_message.write_text(
                    '{"items":[{"view":"back","index":0,"paths":["Game.Core.Tests/Tasks/Task9AcceptanceTests.cs"]}]}\n',
                    encoding="utf-8",
                )
                return 0, "trace", ["openai-api", "gpt-5"]

            with mock.patch.object(fill_refs_script, "run_codex_exec", side_effect=_fake_run_codex_exec):
                ok, mapping, run_results, cmd_ref = fill_refs_script._run_consensus_for_task(
                    root=REPO_ROOT,
                    out_dir=out_dir,
                    task_id=9,
                    prompt="prompt",
                    timeout_sec=30,
                    max_refs_per_item=2,
                    consensus_runs=1,
                    llm_backend="openai-api",
                )

        self.assertTrue(ok)
        self.assertEqual(["openai-api"], seen)
        self.assertEqual(["openai-api", "gpt-5"], cmd_ref)
        self.assertEqual(["Game.Core.Tests/Tasks/Task9AcceptanceTests.cs"], mapping["back"][0])
        self.assertEqual("ok", run_results[0]["status"])


if __name__ == "__main__":
    unittest.main()
