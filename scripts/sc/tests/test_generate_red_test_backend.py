#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))


def _load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


red_test_script = _load_module("sc_llm_generate_red_test_module", "scripts/sc/llm_generate_red_test.py")


class GenerateRedTestBackendTests(unittest.TestCase):
    def test_run_codex_exec_should_forward_backend(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_last = Path(td) / "last.txt"
            with mock.patch.object(red_test_script, "run_llm_exec", return_value=(0, "trace", ["openai-api", "gpt-5"])) as run_mock:
                rc, trace, cmd = red_test_script._run_codex_exec(
                    backend="openai-api",
                    prompt="prompt",
                    out_last_message=out_last,
                    timeout_sec=30,
                )

        self.assertEqual(0, rc)
        self.assertEqual("trace", trace)
        self.assertEqual(["openai-api", "gpt-5"], cmd)
        self.assertEqual("openai-api", run_mock.call_args.kwargs["backend"])

    def test_main_should_record_explicit_llm_backend_in_meta(self) -> None:
        with tempfile.TemporaryDirectory(dir=str(REPO_ROOT)) as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-04-12" / "sc-llm-red-test"
            analyze_dir = root / "logs" / "ci" / "2026-04-12" / "sc-analyze"
            analyze_dir.mkdir(parents=True, exist_ok=True)
            (analyze_dir / "task_context.11.json").write_text(
                json.dumps(
                    {
                        "master": {"title": "Task 11", "overlay": "overlay/path", "adrRefs": [], "archRefs": []},
                        "back": {"test_strategy": [], "acceptance": ["ACC:T11.1 something"]},
                        "gameplay": {"test_strategy": [], "acceptance": ["ACC:T11.2 something"]},
                        "taskdoc_markdown": "taskdoc",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            def fake_run_cmd(cmd: list[str], cwd: Path, timeout_sec: int):  # noqa: ARG001
                cmd_text = " ".join(cmd)
                if "validate_acceptance_refs.py" in cmd_text:
                    return 0, "acceptance refs ok\n"
                if "scripts/sc/analyze.py" in cmd_text:
                    return 0, "analyze ok\n"
                raise AssertionError(f"unexpected command: {cmd}")

            def fake_run_codex_exec(*, backend: str = "codex-cli", prompt: str, out_last_message: Path, timeout_sec: int):  # noqa: ARG001
                out_last_message.parent.mkdir(parents=True, exist_ok=True)
                out_last_message.write_text(
                    json.dumps(
                        {
                            "file_path": "Game.Core.Tests/Tasks/Task11RedTests.cs",
                            "content": "using Xunit;\npublic sealed class Task11RedTests {}\n",
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                return 0, "trace ok\n", ["openai-api", "gpt-5"]

            triplet = SimpleNamespace(task_id="11", back={"acceptance": ["ACC:T11.1 something"]}, gameplay={"acceptance": ["ACC:T11.2 something"]})
            argv = ["llm_generate_red_test.py", "--task-id", "11", "--llm-backend", "openai-api"]

            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(red_test_script, "repo_root", return_value=root),
                mock.patch.object(red_test_script, "ci_dir", return_value=out_dir),
                mock.patch.object(red_test_script, "run_cmd", side_effect=fake_run_cmd),
                mock.patch.object(red_test_script, "resolve_triplet", return_value=triplet),
                mock.patch.object(red_test_script, "_run_codex_exec", side_effect=fake_run_codex_exec),
            ):
                rc = red_test_script.main()
                meta = json.loads((out_dir / "meta-11.json").read_text(encoding="utf-8"))

        self.assertEqual(0, rc)
        self.assertEqual("openai-api", meta["llm_backend"])
        self.assertEqual(["openai-api", "gpt-5"], meta["cmd"])


if __name__ == "__main__":
    unittest.main()
