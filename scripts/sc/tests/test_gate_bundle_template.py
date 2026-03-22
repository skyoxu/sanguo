#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "python" / "run_gate_bundle.py"


class GateBundleTemplateTests(unittest.TestCase):
    def test_hard_mode_should_skip_template_missing_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_root = Path(td) / "gate-bundle"
            missing_back = Path(td) / "missing_tasks_back.json"
            missing_gameplay = Path(td) / "missing_tasks_gameplay.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--mode",
                    "hard",
                    "--out-dir",
                    str(out_root),
                    "--task-files",
                    str(missing_back),
                    str(missing_gameplay),
                    "--skip-prune-runs",
                ],
                cwd=str(REPO_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore",
            )
            self.assertEqual(0, proc.returncode, proc.stdout)
            summary_path = out_root / "hard" / "summary.json"
            self.assertTrue(summary_path.exists(), proc.stdout)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            gates = {str(item.get("name")): item for item in (summary.get("gates") or [])}

            self.assertEqual("missing_prd_gdd_consistency_config", gates["prd_gdd_semantic_consistency"].get("skip_reason"))
            self.assertTrue(gates["prd_gdd_semantic_consistency"].get("skipped"))

            self.assertEqual("missing_task_files", gates["overlay_task_drift"].get("skip_reason"))
            self.assertTrue(gates["overlay_task_drift"].get("skipped"))

            self.assertEqual("missing_task_files", gates["task_contract_refs_gate"].get("skip_reason"))
            self.assertTrue(gates["task_contract_refs_gate"].get("skipped"))

            self.assertEqual("missing_contract_interfaces_dir", gates["contract_interface_docs"].get("skip_reason"))
            self.assertTrue(gates["contract_interface_docs"].get("skipped"))

            self.assertIn("validate_recovery_docs", gates)
            self.assertFalse(gates["validate_recovery_docs"].get("skipped"))
            self.assertEqual(0, int(gates["validate_recovery_docs"].get("rc", -1)), gates["validate_recovery_docs"])

            self.assertEqual("missing_task_files", gates["obligations_reuse_regression"].get("skip_reason"))
            self.assertTrue(gates["obligations_reuse_regression"].get("skipped"))


if __name__ == "__main__":
    unittest.main()
