#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
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


llm_backend = _load_module("sc_llm_backend_module", "scripts/sc/_llm_backend.py")


class LlmBackendTests(unittest.TestCase):
    def test_run_llm_exec_should_fail_on_openai_backend_before_implementation(self) -> None:
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False), \
            mock.patch.object(llm_backend.importlib.util, "find_spec", return_value=None):
            rc, out, cmd = llm_backend.run_llm_exec(
                backend="openai-api",
                root=REPO_ROOT,
                prompt="hello",
                output_last_message=REPO_ROOT / "tmp.md",
                timeout_sec=10,
            )

        self.assertEqual(2, rc)
        self.assertIn("openai-api backend is not runnable", out)
        self.assertEqual(["openai-api"], cmd)

    def test_run_llm_exec_should_report_missing_codex(self) -> None:
        with mock.patch.object(llm_backend.shutil, "which", return_value=None):
            rc, out, cmd = llm_backend.run_llm_exec(
                backend="codex-cli",
                root=REPO_ROOT,
                prompt="hello",
                output_last_message=REPO_ROOT / "tmp.md",
                timeout_sec=10,
            )

        self.assertEqual(127, rc)
        self.assertIn("codex executable not found", out)
        self.assertEqual(["codex"], cmd)

    def test_run_llm_exec_should_invoke_codex_cli(self) -> None:
        proc = subprocess.CompletedProcess(args=["codex"], returncode=0, stdout="ok", stderr="")
        with mock.patch.object(llm_backend.shutil, "which", return_value="codex"), mock.patch.object(
            llm_backend.subprocess, "run", return_value=proc
        ) as run_mock:
            rc, out, cmd = llm_backend.run_llm_exec(
                backend="codex-cli",
                root=REPO_ROOT,
                prompt="hello",
                output_last_message=REPO_ROOT / "tmp.md",
                timeout_sec=10,
                codex_configs=['model_reasoning_effort="low"'],
            )

        self.assertEqual(0, rc)
        self.assertEqual("ok", out)
        self.assertIn("codex", cmd[0])
        self.assertIn("-c", cmd)
        self.assertIn('model_reasoning_effort="low"', cmd)
        run_mock.assert_called_once()

    def test_run_llm_exec_should_invoke_openai_backend_and_write_output(self) -> None:
        class _FakeResponses:
            def create(self, **kwargs):
                self.kwargs = dict(kwargs)
                return type("Response", (), {"id": "resp_123", "output_text": "review output"})()

        class _FakeClient:
            last_timeout = None

            def __init__(self, *, timeout):
                _FakeClient.last_timeout = timeout
                self.responses = _FakeResponses()

        fake_openai = type("FakeOpenAI", (), {"OpenAI": _FakeClient})
        with tempfile.TemporaryDirectory() as td, \
            mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "SC_OPENAI_MODEL": "gpt-5"}, clear=False), \
            mock.patch.object(llm_backend.importlib.util, "find_spec", return_value=object()), \
            mock.patch.dict(sys.modules, {"openai": fake_openai}):
            out_path = Path(td) / "review.md"
            rc, out, cmd = llm_backend.run_llm_exec(
                backend="openai-api",
                root=REPO_ROOT,
                prompt="hello",
                output_last_message=out_path,
                timeout_sec=15,
                codex_configs=['model_reasoning_effort="low"'],
            )

            self.assertEqual(0, rc)
            self.assertIn('"backend": "openai-api"', out)
            self.assertEqual(["openai-api", "gpt-5"], cmd)
            self.assertTrue(out_path.is_file())
            self.assertEqual("review output\n", out_path.read_text(encoding="utf-8"))
            self.assertEqual(15.0, _FakeClient.last_timeout)

    def test_run_llm_exec_should_surface_openai_request_failures(self) -> None:
        class _FailingResponses:
            def create(self, **kwargs):  # noqa: ARG002
                raise RuntimeError("boom")

        class _FailingClient:
            def __init__(self, *, timeout):  # noqa: ARG002
                self.responses = _FailingResponses()

        fake_openai = type("FakeOpenAI", (), {"OpenAI": _FailingClient})
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=False), \
            mock.patch.object(llm_backend.importlib.util, "find_spec", return_value=object()), \
            mock.patch.dict(sys.modules, {"openai": fake_openai}):
            rc, out, cmd = llm_backend.run_llm_exec(
                backend="openai-api",
                root=REPO_ROOT,
                prompt="hello",
                output_last_message=REPO_ROOT / "tmp.md",
                timeout_sec=15,
            )

        self.assertEqual(1, rc)
        self.assertIn("openai-api request failed", out)
        self.assertEqual(["openai-api"], cmd)


if __name__ == "__main__":
    unittest.main()
