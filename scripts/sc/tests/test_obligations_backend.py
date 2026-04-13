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

import llm_extract_task_obligations as obligations_script  # noqa: E402
import _obligations_runtime_helpers as runtime_helpers  # noqa: E402


class ObligationsBackendTests(unittest.TestCase):
    def test_apply_delivery_profile_defaults_should_resolve_default_llm_backend(self) -> None:
        args = obligations_script.apply_delivery_profile_defaults(
            obligations_script.argparse.Namespace(
                delivery_profile="fast-ship",
                llm_backend=None,
                timeout_sec=None,
                max_prompt_chars=None,
                consensus_runs=None,
                garbled_gate=None,
            )
        )

        self.assertEqual("codex-cli", args.llm_backend)

    def test_apply_delivery_profile_defaults_should_keep_explicit_llm_backend(self) -> None:
        args = obligations_script.apply_delivery_profile_defaults(
            obligations_script.argparse.Namespace(
                delivery_profile="fast-ship",
                llm_backend="openai-api",
                timeout_sec=None,
                max_prompt_chars=None,
                consensus_runs=None,
                garbled_gate=None,
            )
        )

        self.assertEqual("openai-api", args.llm_backend)

    def test_run_consensus_rounds_should_forward_llm_backend(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            seen: list[str] = []

            def _fake_run_codex_exec(*, backend: str, prompt: str, out_last_message: Path, timeout_sec: int, repo_root_path: Path):
                _ = prompt, timeout_sec, repo_root_path
                seen.append(backend)
                out_last_message.write_text('{"task_id":"9","status":"ok","obligations":[],"uncovered_obligation_ids":[],"notes":[]}\n', encoding="utf-8")
                return 0, "trace", ["openai-api", "gpt-5"]

            with mock.patch.object(runtime_helpers, "run_codex_exec", side_effect=_fake_run_codex_exec):
                run_results, run_verdicts, cmd_ref, escalated, reasons = runtime_helpers.run_consensus_rounds(
                    prompt="hello",
                    out_dir=out_dir,
                    timeout_sec=30,
                    repo_root_path=REPO_ROOT,
                    llm_backend="openai-api",
                    configured_runs=1,
                    max_runs=1,
                    auto_escalate_enabled=False,
                    force_for_task=False,
                    max_schema_errors=3,
                    normalize_status=lambda value: str(value or "").strip().lower(),
                )

            self.assertEqual(["openai-api"], seen)
            self.assertEqual(1, len(run_results))
            self.assertEqual(1, len(run_verdicts))
            self.assertEqual(["openai-api", "gpt-5"], cmd_ref)
            self.assertFalse(escalated)
            self.assertEqual([], reasons)


if __name__ == "__main__":
    unittest.main()
