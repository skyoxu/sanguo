from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON_DIR = REPO_ROOT / "scripts" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from impact_analysis_handoff import validate_handoff


class ImpactAnalysisHandoffTests(unittest.TestCase):
    def test_all_missing_arguments_preserve_legacy_opt_out(self) -> None:
        result = validate_handoff(None, None, None, repo_root=Path.cwd())
        self.assertTrue(result.ok)

    def test_partial_arguments_fail_closed(self) -> None:
        result = validate_handoff("context.json", None, "a" * 40, repo_root=Path.cwd())
        self.assertFalse(result.ok)
        self.assertEqual("invalid_kcp_binding", result.code)
        self.assertEqual(11, result.exit_code)

    def test_valid_binding_uses_exact_file_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frozen_path = root / "frozen.json"
            report_path = root / "report.json"
            revision = "a" * 40
            frozen = {
                "schema_version": "newrouge.knowledge-frozen-context.v1",
                "freeze_state": "frozen",
                "consumer": "chapter6",
                "snapshot": {"commit": revision},
            }
            frozen_path.write_text(json.dumps(frozen), encoding="utf-8")
            import hashlib
            frozen_hash = hashlib.sha256(frozen_path.read_bytes()).hexdigest()
            report = {
                "schema_version": "newrouge.impact-analysis.v1",
                "status": "ok",
                "repository_revision": revision,
                "index_id": "idx-test",
                "index_sha256": "sha-index",
                "target": {"kind": "file", "identity": "x"},
                "risk_level": "unknown",
                "knowledge_binding": {
                    "consumer": "chapter6",
                    "task_id": "15",
                    "frozen_context_path": "frozen.json",
                    "frozen_context_sha256": frozen_hash,
                    "decision_set_sha256": "sha-decision",
                    "freeze_point": "before-red",
                    "publication_generation": "gen",
                    "publication_sha256": "sha-publication",
                },
            }
            report_path.write_text(json.dumps(report), encoding="utf-8")
            result = validate_handoff(
                "frozen.json", "report.json", revision,
                repo_root=root, consumer="chapter6", task_id="15",
            )
            self.assertTrue(result.ok)
            self.assertEqual(revision, result.identity["revision"])
            self.assertEqual("idx-test", result.identity["index_id"])

    def test_binding_evidence_revision_mismatch_fails_closed(self):
        result = validate_handoff("missing.json", "missing-report.json", "a" * 40, repo_root=Path.cwd(), binding_evidence="sidecar.json")
        self.assertFalse(result.ok)


if __name__ == "__main__":
    unittest.main()
