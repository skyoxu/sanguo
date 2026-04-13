#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

import llm_semantic_gate_all as semantic_gate_script  # noqa: E402


def _load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


semantic_gate_runtime = _load_module("sc_semantic_gate_runtime_module", "scripts/sc/_semantic_gate_all_runtime.py")


class SemanticGateAllBackendTests(unittest.TestCase):
    def test_load_task_maps_should_fallback_to_examples_taskmaster(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            examples = root / "examples" / "taskmaster"
            examples.mkdir(parents=True, exist_ok=True)
            (examples / "tasks.json").write_text(
                json.dumps({"master": {"tasks": [{"id": "11", "title": "Example task"}]}}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (examples / "tasks_back.json").write_text(
                json.dumps([{"taskmaster_id": 11, "acceptance": ["ACC back"]}], ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (examples / "tasks_gameplay.json").write_text(
                json.dumps([{"taskmaster_id": 11, "acceptance": ["ACC gameplay"]}], ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            with mock.patch.object(semantic_gate_runtime, "repo_root", return_value=root):
                all_ids, master_by_id, back_by_id, gameplay_by_id = semantic_gate_runtime.load_task_maps()

        self.assertEqual([11], all_ids)
        self.assertEqual("Example task", master_by_id[11]["title"])
        self.assertEqual(["ACC back"], back_by_id[11]["acceptance"])
        self.assertEqual(["ACC gameplay"], gameplay_by_id[11]["acceptance"])

    def test_apply_delivery_profile_defaults_should_resolve_default_llm_backend(self) -> None:
        args = semantic_gate_script.apply_delivery_profile_defaults(
            semantic_gate_script.argparse.Namespace(
                delivery_profile="fast-ship",
                llm_backend=None,
                timeout_sec=None,
                consensus_runs=None,
                model_reasoning_effort=None,
                max_prompt_chars=None,
                max_needs_fix=None,
                max_unknown=None,
                garbled_gate=None,
            )
        )

        self.assertEqual("codex-cli", args.llm_backend)

    def test_run_codex_exec_should_forward_backend_and_reasoning_effort(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_path = Path(td) / "out.tsv"

            with mock.patch.object(semantic_gate_script, "run_llm_exec", return_value=(0, "trace", ["openai-api", "gpt-5"])) as run_mock:
                rc, trace, cmd = semantic_gate_script._run_codex_exec(
                    backend="openai-api",
                    prompt="prompt",
                    out_path=out_path,
                    timeout_sec=30,
                    model_reasoning_effort="medium",
                )

        self.assertEqual(0, rc)
        self.assertEqual("trace", trace)
        self.assertEqual(["openai-api", "gpt-5"], cmd)
        run_mock.assert_called_once()
        kwargs = run_mock.call_args.kwargs
        self.assertEqual("openai-api", kwargs["backend"])
        self.assertEqual(['model_reasoning_effort="medium"'], kwargs["codex_configs"])

    def test_summary_should_record_explicit_llm_backend(self) -> None:
        with tempfile.TemporaryDirectory(dir=str(REPO_ROOT)) as td:
            out_dir = Path(td) / "semantic-gate"

            with (
                mock.patch.object(semantic_gate_script, "ci_dir", return_value=out_dir),
                mock.patch.object(semantic_gate_script, "load_task_maps", return_value=([1], {1: {"title": "Task 1", "description": "desc", "details": "details"}}, {1: {"acceptance": ["ACC:T1.1 done"]}}, {})),
                mock.patch.object(semantic_gate_script, "_run_codex_exec", return_value=(0, "trace", ["openai-api", "gpt-5"])),
                mock.patch.object(semantic_gate_script, "_parse_tsv_output", return_value=[semantic_gate_script.SemanticFinding(task_id=1, verdict="OK", reason="covered")]),
                mock.patch.object(sys, "argv", ["llm_semantic_gate_all.py", "--task-ids", "1", "--garbled-gate", "off", "--llm-backend", "openai-api"]),
            ):
                rc = semantic_gate_script.main()
                summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))

        self.assertEqual(0, rc)
        self.assertEqual("openai-api", summary["config"]["llm_backend"])
        self.assertEqual(["openai-api", "gpt-5"], summary["batch_meta"][0]["run_meta"][0]["cmd"])


if __name__ == "__main__":
    unittest.main()
