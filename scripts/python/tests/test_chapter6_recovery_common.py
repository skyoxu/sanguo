#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON_DIR = REPO_ROOT / "scripts" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))


def _load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


recovery_common = _load_module("chapter6_recovery_common_module", "scripts/python/_chapter6_recovery_common.py")


class Chapter6RecoveryCommonTests(unittest.TestCase):
    def test_should_infer_artifact_integrity_from_planned_only_reason_without_blocked_by(self) -> None:
        note = recovery_common.chapter6_stop_loss_note(
            {},
            {"reason": "planned_only_incomplete", "artifact_integrity_kind": "planned_only_incomplete"},
        )
        self.assertIn("planned-only terminal run", note)

    def test_should_keep_generic_artifact_integrity_note_for_non_planned_only_kind(self) -> None:
        note = recovery_common.chapter6_stop_loss_note(
            {"blocked_by": "artifact_integrity"},
            {"reason": "latest_bundle_incomplete", "artifact_integrity_kind": "missing_summary"},
        )
        self.assertIn("incomplete or stale", note)

    def test_should_keep_rerun_guard_priority_over_other_inference(self) -> None:
        note = recovery_common.chapter6_stop_loss_note(
            {},
            {"reason": "rerun_blocked:deterministic_green_llm_not_clean", "artifact_integrity_kind": "planned_only_incomplete"},
        )
        self.assertIn("Deterministic evidence is already green", note)


if __name__ == "__main__":
    unittest.main()
