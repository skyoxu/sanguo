#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON_DIR = REPO_ROOT / "scripts" / "python"
SC_DIR = REPO_ROOT / "scripts" / "sc"

for candidate in (PYTHON_DIR, SC_DIR):
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


run_dotnet = _load_module("run_dotnet_delivery_profile_module", "scripts/python/run_dotnet.py")


class RunDotnetDeliveryProfileTests(unittest.TestCase):
    def test_should_use_fast_ship_thresholds_by_default(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            payload = run_dotnet.resolve_coverage_thresholds()

        self.assertEqual("fast-ship", payload["delivery_profile"])
        self.assertTrue(payload["coverage_gate"])
        self.assertFalse(payload["skip_coverage_gate"])
        self.assertEqual(70.0, payload["lines_min"])
        self.assertEqual(60.0, payload["branches_min"])
        self.assertEqual("delivery-profile", payload["threshold_source"]["lines_min"])
        self.assertEqual("delivery-profile", payload["threshold_source"]["branches_min"])

    def test_should_use_standard_thresholds_when_requested(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            payload = run_dotnet.resolve_coverage_thresholds(delivery_profile="standard")

        self.assertEqual("standard", payload["delivery_profile"])
        self.assertEqual(90.0, payload["lines_min"])
        self.assertEqual(85.0, payload["branches_min"])

    def test_should_disable_gate_for_playable_ea(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            payload = run_dotnet.resolve_coverage_thresholds(delivery_profile="playable-ea")

        self.assertEqual("playable-ea", payload["delivery_profile"])
        self.assertFalse(payload["coverage_gate"])
        self.assertTrue(payload["skip_coverage_gate"])
        self.assertEqual(0.0, payload["lines_min"])
        self.assertEqual(0.0, payload["branches_min"])
        self.assertEqual("delivery-profile-skip", payload["threshold_source"]["lines_min"])
        self.assertEqual("delivery-profile-skip", payload["threshold_source"]["branches_min"])

    def test_env_overrides_should_win_over_delivery_profile_defaults(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "DELIVERY_PROFILE": "fast-ship",
                "COVERAGE_LINES_MIN": "88",
                "COVERAGE_BRANCHES_MIN": "77",
            },
            clear=True,
        ):
            payload = run_dotnet.resolve_coverage_thresholds()

        self.assertEqual("fast-ship", payload["delivery_profile"])
        self.assertEqual(88.0, payload["lines_min"])
        self.assertEqual(77.0, payload["branches_min"])
        self.assertEqual("env", payload["threshold_source"]["lines_min"])
        self.assertEqual("env", payload["threshold_source"]["branches_min"])


if __name__ == "__main__":
    unittest.main()
