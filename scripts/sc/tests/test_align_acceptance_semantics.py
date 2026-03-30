#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from _taskmaster_fixture import staged_taskmaster_triplet


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
SCRIPT = SC_DIR / "llm_align_acceptance_semantics.py"
sys.path.insert(0, str(SC_DIR))

import _acceptance_semantics_runtime as runtime  # noqa: E402
import llm_align_acceptance_semantics as align_script  # noqa: E402


class AcceptanceSemanticsRuntimeRetryTests(unittest.TestCase):
    def test_should_retry_once_when_first_call_is_transient_failure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            task_out = Path(td)
            calls = {"n": 0}

            def fake_run_codex_exec(*, prompt: str, out_last_message: Path, timeout_sec: int) -> tuple[int, str]:  # noqa: ARG001
                calls["n"] += 1
                if calls["n"] == 1:
                    return 124, "timeout"
                out_last_message.write_text('{"task_id": 1, "mode": "rewrite-only"}', encoding="utf-8")
                return 0, "ok"

            with patch.object(runtime, "run_codex_exec", side_effect=fake_run_codex_exec):
                reason, out_obj, attempts = runtime._run_model_with_retry(prompt="p", task_out=task_out, timeout_sec=1)

            self.assertEqual("ok", reason)
            self.assertEqual(2, attempts)
            self.assertIsInstance(out_obj, dict)
            self.assertEqual(2, calls["n"])
            self.assertTrue((task_out / "trace-attempt-1.log").exists())
            self.assertTrue((task_out / "trace-attempt-2.log").exists())

    def test_should_retry_once_when_first_output_is_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            task_out = Path(td)
            calls = {"n": 0}

            def fake_run_codex_exec(*, prompt: str, out_last_message: Path, timeout_sec: int) -> tuple[int, str]:  # noqa: ARG001
                calls["n"] += 1
                if calls["n"] == 1:
                    out_last_message.write_text("{invalid", encoding="utf-8")
                    return 0, "ok"
                out_last_message.write_text('{"task_id": 1, "mode": "rewrite-only"}', encoding="utf-8")
                return 0, "ok"

            with patch.object(runtime, "run_codex_exec", side_effect=fake_run_codex_exec):
                reason, out_obj, attempts = runtime._run_model_with_retry(prompt="p", task_out=task_out, timeout_sec=1)

            self.assertEqual("ok", reason)
            self.assertEqual(2, attempts)
            self.assertIsInstance(out_obj, dict)
            self.assertEqual(2, calls["n"])

    def test_should_not_retry_when_failure_is_non_transient(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            task_out = Path(td)
            calls = {"n": 0}

            def fake_run_codex_exec(*, prompt: str, out_last_message: Path, timeout_sec: int) -> tuple[int, str]:  # noqa: ARG001
                calls["n"] += 1
                return 127, "codex executable not found"

            with patch.object(runtime, "run_codex_exec", side_effect=fake_run_codex_exec):
                reason, out_obj, attempts = runtime._run_model_with_retry(prompt="p", task_out=task_out, timeout_sec=1)

            self.assertEqual("codex_rc:127", reason)
            self.assertIsNone(out_obj)
            self.assertEqual(1, attempts)
            self.assertEqual(1, calls["n"])


class AcceptanceSemanticsRefsRestoreTests(unittest.TestCase):
    def _master(self, task_id: int = 7) -> runtime.MasterTaskInput:
        return runtime.MasterTaskInput(
            task_id=task_id,
            status="in-progress",
            title="Demo task",
            description="Demo description",
            details="Demo details",
            test_strategy="",
            subtasks=[],
        )

    def test_should_restore_existing_refs_before_validation(self) -> None:
        master_index = {7: self._master()}
        back = [
            {
                "taskmaster_id": 7,
                "description": "old",
                "acceptance": ["ACC:T7.1 old text. Refs: Game.Core.Tests/FooTests.cs"],
            }
        ]
        gameplay: list[dict[str, object]] = []
        out_obj = {
            "task_id": 7,
            "mode": "rewrite-only",
            "back": {
                "description": "old",
                "acceptance": ["ACC:T7.1 rewritten text. Refs: Game.Core.Tests/ChangedTests.cs"],
            },
            "gameplay": None,
            "notes": [],
        }

        with tempfile.TemporaryDirectory() as td:
            with patch.object(runtime, "_run_model_with_retry", return_value=("ok", out_obj, 1)):
                result = runtime.run_alignment_tasks(
                    task_ids=[7],
                    master_index=master_index,
                    semantic_hints={},
                    back=back,
                    gameplay=gameplay,
                    out_dir=Path(td),
                    apply=True,
                    timeout_sec=1,
                    delivery_profile_context="",
                    max_failures=0,
                    structural_for_not_done=False,
                    append_only_for_done=False,
                    align_view_descriptions_to_master=False,
                )

        self.assertEqual(0, result["failed"])
        self.assertEqual("ok", result["results"][0]["status"])
        self.assertEqual(1, result["results"][0]["refs_restored_count"])
        self.assertEqual(
            ["ACC:T7.1 rewritten text. Refs: Game.Core.Tests/FooTests.cs"],
            back[0]["acceptance"],
        )

    def test_should_still_fail_when_model_adds_new_refs_to_existing_item(self) -> None:
        master_index = {7: self._master()}
        back = [
            {
                "taskmaster_id": 7,
                "description": "old",
                "acceptance": ["ACC:T7.1 old text without refs."],
            }
        ]
        gameplay: list[dict[str, object]] = []
        out_obj = {
            "task_id": 7,
            "mode": "rewrite-only",
            "back": {
                "description": "old",
                "acceptance": ["ACC:T7.1 rewritten text. Refs: Game.Core.Tests/FooTests.cs"],
            },
            "gameplay": None,
            "notes": [],
        }

        with tempfile.TemporaryDirectory() as td:
            with patch.object(runtime, "_run_model_with_retry", return_value=("ok", out_obj, 1)):
                result = runtime.run_alignment_tasks(
                    task_ids=[7],
                    master_index=master_index,
                    semantic_hints={},
                    back=back,
                    gameplay=gameplay,
                    out_dir=Path(td),
                    apply=True,
                    timeout_sec=1,
                    delivery_profile_context="",
                    max_failures=0,
                    structural_for_not_done=False,
                    append_only_for_done=False,
                    align_view_descriptions_to_master=False,
                )

        self.assertEqual(1, result["failed"])
        self.assertEqual("fail", result["results"][0]["status"])
        self.assertEqual("back:unexpected_refs_added_at_1", result["results"][0]["reason"])


class AlignAcceptanceCliGuardTests(unittest.TestCase):
    def test_should_fail_when_missing_task_ids_in_scope_and_flag_enabled(self) -> None:
        with staged_taskmaster_triplet(include_task1=True):
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--task-ids",
                    "999999",
                    "--fail-on-missing-task-ids",
                    "--garbled-gate",
                    "off",
                    "--self-check",
                ],
                cwd=str(REPO_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore",
            )
        self.assertEqual(2, proc.returncode)
        self.assertIn("missing_task_ids_in_scope", proc.stdout or "")

    def test_should_allow_missing_task_ids_when_flag_disabled(self) -> None:
        with staged_taskmaster_triplet(include_task1=True):
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--task-ids",
                    "999999",
                    "--garbled-gate",
                    "off",
                    "--self-check",
                ],
                cwd=str(REPO_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore",
            )
        self.assertEqual(0, proc.returncode)
        self.assertIn("SC_ALIGN_ACCEPTANCE_SELF_CHECK status=ok", proc.stdout or "")

    def test_should_pass_strict_task_selection_for_known_task(self) -> None:
        with staged_taskmaster_triplet(include_task1=True):
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--task-ids",
                    "1",
                    "--strict-task-selection",
                    "--garbled-gate",
                    "off",
                    "--self-check",
                ],
                cwd=str(REPO_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore",
            )
        self.assertEqual(0, proc.returncode)
        self.assertIn("SC_ALIGN_ACCEPTANCE_SELF_CHECK status=ok", proc.stdout or "")

    def test_should_fail_strict_task_selection_for_unknown_task(self) -> None:
        with staged_taskmaster_triplet(include_task1=True):
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--task-ids",
                    "999999",
                    "--strict-task-selection",
                    "--garbled-gate",
                    "off",
                    "--self-check",
                ],
                cwd=str(REPO_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore",
            )
        self.assertEqual(2, proc.returncode)
        self.assertIn("missing_task_ids_in_scope", proc.stdout or "")


class AlignAcceptanceViewGuardTests(unittest.TestCase):
    def test_should_fail_when_missing_view_entries_and_flag_enabled(self) -> None:
        with (
            patch.object(align_script, "default_paths", return_value=("ignored", "back.json", "gameplay.json")),
            patch.object(align_script, "load_json", side_effect=[[], []]),
            patch.object(align_script, "load_master_index", return_value={1: object()}),
            patch.object(align_script, "load_semantic_hints", return_value={}),
            patch.object(
                sys,
                "argv",
                [
                    "llm_align_acceptance_semantics.py",
                    "--task-ids",
                    "1",
                    "--fail-on-missing-views",
                    "--self-check",
                    "--garbled-gate",
                    "off",
                ],
            ),
        ):
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = align_script.main()

        self.assertEqual(2, rc)
        self.assertIn("missing_view_entries", buf.getvalue())

    def test_should_pass_when_any_view_entry_exists_and_flag_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "ci-self-check"
            with (
                patch.object(align_script, "default_paths", return_value=("ignored", "back.json", "gameplay.json")),
                patch.object(align_script, "load_json", side_effect=[[{"taskmaster_id": 1, "acceptance": []}], []]),
                patch.object(align_script, "load_master_index", return_value={1: object()}),
                patch.object(align_script, "load_semantic_hints", return_value={}),
                patch.object(align_script, "ci_dir", return_value=out_dir),
                patch.object(align_script, "write_json", return_value=None),
                patch.object(
                    sys,
                    "argv",
                    [
                        "llm_align_acceptance_semantics.py",
                        "--task-ids",
                        "1",
                        "--fail-on-missing-views",
                        "--self-check",
                        "--garbled-gate",
                        "off",
                    ],
                ),
            ):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = align_script.main()

        self.assertEqual(0, rc)
        self.assertIn("SC_ALIGN_ACCEPTANCE_SELF_CHECK status=ok", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
