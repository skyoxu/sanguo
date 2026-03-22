#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


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


red = _load_module("sc_acceptance_testgen_red_module", "scripts/sc/_acceptance_testgen_red.py")


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class AcceptanceTestgenRedTests(unittest.TestCase):
    def test_evaluate_red_verification_should_fail_on_unexpected_green(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out_dir = root / "logs" / "ci" / "2026-03-20" / "sc-llm-acceptance-tests"
            report = red.evaluate_red_verification(
                repo_root=root,
                out_dir=out_dir,
                verify_mode="unit",
                test_step={"status": "ok", "rc": 0, "cmd": ["py", "-3", "scripts/sc/test.py"]},
                verify_log_text="SC_TEST status=ok\n",
            )

        self.assertEqual("fail", report["status"])
        self.assertEqual("unexpected_green", report["reason"])

    def test_evaluate_red_verification_should_accept_unit_test_failure_without_compile_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out_dir = root / "logs" / "ci" / "2026-03-20" / "sc-llm-acceptance-tests"
            _write_json(
                root / "logs" / "unit" / "2026-03-20" / "summary.json",
                {
                    "status": "tests_failed",
                    "failure_excerpt": ["Expected: 2", "But was: 1"],
                },
            )

            report = red.evaluate_red_verification(
                repo_root=root,
                out_dir=out_dir,
                verify_mode="unit",
                test_step={"status": "fail", "rc": 1, "cmd": ["py", "-3", "scripts/sc/test.py"]},
                verify_log_text="SC_TEST status=fail\n",
            )

        self.assertEqual("ok", report["status"])
        self.assertEqual("unit_red", report["reason"])

    def test_evaluate_red_verification_should_fail_on_compile_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out_dir = root / "logs" / "ci" / "2026-03-20" / "sc-llm-acceptance-tests"
            _write_json(
                root / "logs" / "unit" / "2026-03-20" / "summary.json",
                {
                    "status": "tests_failed",
                    "failure_excerpt": ["error CS1002: ; expected"],
                },
            )

            report = red.evaluate_red_verification(
                repo_root=root,
                out_dir=out_dir,
                verify_mode="unit",
                test_step={"status": "fail", "rc": 1, "cmd": ["py", "-3", "scripts/sc/test.py"]},
                verify_log_text="Build FAILED.\nerror CS1002: ; expected\n",
            )

        self.assertEqual("fail", report["status"])
        self.assertEqual("compile_error", report["reason"])

    def test_evaluate_red_verification_should_accept_gdunit_failures_without_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out_dir = root / "logs" / "ci" / "2026-03-20" / "sc-llm-acceptance-tests"
            _write_json(
                root / "logs" / "e2e" / "2026-03-20" / "sc-test" / "gdunit-hard" / "run-summary.json",
                {
                    "results": {
                        "failures": 1,
                        "errors": 0,
                    }
                },
            )

            report = red.evaluate_red_verification(
                repo_root=root,
                out_dir=out_dir,
                verify_mode="all",
                test_step={"status": "fail", "rc": 1, "cmd": ["py", "-3", "scripts/sc/test.py"]},
                verify_log_text="SC_TEST status=fail\n",
            )

        self.assertEqual("ok", report["status"])
        self.assertEqual("gdunit_red", report["reason"])


if __name__ == "__main__":
    unittest.main()
