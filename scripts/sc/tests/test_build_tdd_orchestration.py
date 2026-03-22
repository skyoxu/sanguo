#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_BUILD_DIR = REPO_ROOT / "scripts" / "sc" / "build"
SC_DIR = REPO_ROOT / "scripts" / "sc"
for candidate in (SC_BUILD_DIR, SC_DIR):
    text = str(candidate)
    if text not in sys.path:
        sys.path.insert(0, text)


def _load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


tdd_script = _load_module("sc_build_tdd_module", "scripts/sc/build/tdd.py")


class _FakeTriplet:
    def __init__(self, task_id: str = "14", title: str = "Demo task", status: str = "in-progress") -> None:
        self.task_id = task_id
        self.master = {"title": title, "status": status}
        self.taskdoc_path = "docs/tasks/task-14.md"

    def adr_refs(self) -> list[str]:
        return ["ADR-0005"]

    def arch_refs(self) -> list[str]:
        return ["CH07"]

    def overlay(self) -> str:
        return "docs/architecture/overlays/PRD-demo/08/_index.md"


class BuildTddOrchestrationTests(unittest.TestCase):
    def test_red_should_stop_when_context_validation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "sc-build-tdd"
            argv = ["tdd.py", "--stage", "red", "--task-id", "14"]
            analyze_step = {"name": "sc-analyze", "rc": 0, "status": "ok", "log": str(out_dir / "sc-analyze.log")}
            ctx_step = {"name": "validate_task_context_required_fields", "rc": 1, "status": "fail", "log": str(out_dir / "ctx.log")}
            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(tdd_script, "ci_dir", return_value=out_dir), \
                mock.patch.object(tdd_script, "resolve_triplet", return_value=_FakeTriplet()), \
                mock.patch.object(tdd_script, "run_sc_analyze_task_context", return_value=analyze_step), \
                mock.patch.object(tdd_script, "validate_task_context_required_fields", return_value=ctx_step), \
                mock.patch.object(tdd_script, "run_dotnet_test_filtered") as filtered_mock, \
                mock.patch.object(tdd_script, "assert_no_new_contract_files", return_value=None):
                rc = tdd_script.main()

            self.assertEqual(1, rc)
            filtered_mock.assert_not_called()
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("fail", summary["status"])
            self.assertEqual(["sc-analyze", "validate_task_context_required_fields"], [item["name"] for item in summary["steps"]])

    def test_red_should_return_two_when_task_test_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "sc-build-tdd"
            argv = ["tdd.py", "--stage", "red", "--task-id", "14"]
            analyze_step = {"name": "sc-analyze", "rc": 0, "status": "ok", "log": str(out_dir / "sc-analyze.log")}
            ctx_step = {"name": "validate_task_context_required_fields", "rc": 0, "status": "ok", "log": str(out_dir / "ctx.log")}
            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(tdd_script, "ci_dir", return_value=out_dir), \
                mock.patch.object(tdd_script, "resolve_triplet", return_value=_FakeTriplet()), \
                mock.patch.object(tdd_script, "run_sc_analyze_task_context", return_value=analyze_step), \
                mock.patch.object(tdd_script, "validate_task_context_required_fields", return_value=ctx_step), \
                mock.patch.object(tdd_script, "ensure_red_test_exists", return_value=None), \
                mock.patch.object(tdd_script, "run_dotnet_test_filtered") as filtered_mock:
                rc = tdd_script.main()

            self.assertEqual(2, rc)
            filtered_mock.assert_not_called()
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("fail", summary["status"])
            self.assertEqual(["sc-analyze", "validate_task_context_required_fields"], [item["name"] for item in summary["steps"]])

    def test_green_should_append_coverage_hotspots_when_run_dotnet_returns_two(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "sc-build-tdd"
            argv = ["tdd.py", "--stage", "green", "--task-id", "14"]
            analyze_step = {"name": "sc-analyze", "rc": 0, "status": "ok", "log": str(out_dir / "sc-analyze.log")}
            ctx_step = {"name": "validate_task_context_required_fields", "rc": 0, "status": "ok", "log": str(out_dir / "ctx.log")}
            green_step = {"name": "run_dotnet", "rc": 2, "log": str(out_dir / "run_dotnet.log"), "stdout": "coverage out", "status": "fail"}
            hotspots_step = {"name": "coverage_hotspots", "rc": 0, "log": str(out_dir / "coverage-hotspots.txt"), "status": "ok"}
            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(tdd_script, "ci_dir", return_value=out_dir), \
                mock.patch.object(tdd_script, "resolve_triplet", return_value=_FakeTriplet()), \
                mock.patch.object(tdd_script, "run_sc_analyze_task_context", return_value=analyze_step), \
                mock.patch.object(tdd_script, "validate_task_context_required_fields", return_value=ctx_step), \
                mock.patch.object(tdd_script, "run_green_gate", return_value=green_step), \
                mock.patch.object(tdd_script, "write_coverage_hotspots", return_value=hotspots_step), \
                mock.patch.object(tdd_script, "assert_no_new_contract_files", return_value=None):
                rc = tdd_script.main()

            self.assertEqual(1, rc)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("fail", summary["status"])
            self.assertEqual(
                ["sc-analyze", "validate_task_context_required_fields", "run_dotnet", "coverage_hotspots"],
                [item["name"] for item in summary["steps"]],
            )

    def test_refactor_should_fail_when_any_check_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "sc-build-tdd"
            argv = ["tdd.py", "--stage", "refactor", "--task-id", "14"]
            analyze_step = {"name": "sc-analyze", "rc": 0, "status": "ok", "log": str(out_dir / "sc-analyze.log")}
            ctx_step = {"name": "validate_task_context_required_fields", "rc": 0, "status": "ok", "log": str(out_dir / "ctx.log")}
            checks = [
                {"name": "validate_task_test_refs", "rc": 0, "status": "ok", "log": str(out_dir / "task-test-refs.log")},
                {"name": "validate_acceptance_refs", "rc": 1, "status": "fail", "log": str(out_dir / "validate_acceptance_refs.log")},
            ]
            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(tdd_script, "ci_dir", return_value=out_dir), \
                mock.patch.object(tdd_script, "resolve_triplet", return_value=_FakeTriplet()), \
                mock.patch.object(tdd_script, "run_sc_analyze_task_context", return_value=analyze_step), \
                mock.patch.object(tdd_script, "validate_task_context_required_fields", return_value=ctx_step), \
                mock.patch.object(tdd_script, "run_refactor_checks", return_value=checks), \
                mock.patch.object(tdd_script, "assert_no_new_contract_files", return_value=None):
                rc = tdd_script.main()

            self.assertEqual(1, rc)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("fail", summary["status"])
            self.assertEqual(
                ["sc-analyze", "validate_task_context_required_fields", "validate_task_test_refs", "validate_acceptance_refs"],
                [item["name"] for item in summary["steps"]],
            )


if __name__ == "__main__":
    unittest.main()
