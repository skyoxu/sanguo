from __future__ import annotations

import hashlib
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

    def _write_valid_handoff(self, root: Path) -> tuple[str, Path, Path]:
        frozen_path = root / "frozen.json"
        report_path = root / "report.json"
        manifest_path = root / "run-manifest.v1.json"
        revision = "a" * 40
        frozen = {
            "schema_version": "newrouge.knowledge-frozen-context.v1",
            "freeze_state": "frozen",
            "consumer": "chapter6",
            "snapshot": {"commit": revision},
        }
        frozen_path.write_text(json.dumps(frozen), encoding="utf-8")
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
        manifest = {
            "schema_version": "newrouge.impact-analysis-run-manifest.v1",
            "run_id": "test-run",
            "report_path": "report.json",
            "report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
            "repository_revision": revision,
            "status": "ok",
        }
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return revision, report_path, manifest_path

    def test_valid_binding_uses_exact_file_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            revision, _, _ = self._write_valid_handoff(root)
            result = validate_handoff(
                "frozen.json", "report.json", revision,
                repo_root=root, consumer="chapter6", task_id="15",
            )
            self.assertTrue(result.ok)
            self.assertEqual(revision, result.identity["revision"])
            self.assertEqual("idx-test", result.identity["index_id"])

    def test_run_manifest_rebinds_report_bytes_path_revision_and_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            revision, report_path, manifest_path = self._write_valid_handoff(root)
            report_bytes = report_path.read_bytes()
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            tampered_report = json.loads(report_bytes.decode("utf-8"))
            tampered_report["consumer_note"] = "tampered"
            report_path.write_text(json.dumps(tampered_report), encoding="utf-8")
            result = validate_handoff("frozen.json", "report.json", revision, repo_root=root)
            self.assertFalse(result.ok)
            self.assertEqual("impact report hash manifest mismatch", result.reason)
            report_path.write_bytes(report_bytes)

            manifest_path.unlink()
            result = validate_handoff("frozen.json", "report.json", revision, repo_root=root)
            self.assertFalse(result.ok)
            self.assertEqual("impact run manifest is missing or invalid", result.reason)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            for field, value, code, reason in [
                ("report_sha256", "0" * 64, "invalid_kcp_binding", "impact report hash manifest mismatch"),
                ("report_path", "logs/ci/other-report.json", "invalid_kcp_binding", "impact report path manifest mismatch"),
                ("repository_revision", "b" * 40, "revision_mismatch", "impact report revision manifest mismatch"),
                ("status", "failed", "invalid_kcp_binding", "impact report status manifest mismatch"),
            ]:
                with self.subTest(field=field):
                    changed = dict(manifest)
                    changed[field] = value
                    manifest_path.write_text(json.dumps(changed), encoding="utf-8")
                    result = validate_handoff("frozen.json", "report.json", revision, repo_root=root)
                    self.assertFalse(result.ok)
                    self.assertEqual(code, result.code)
                    self.assertEqual(reason, result.reason)

    def test_binding_evidence_revision_mismatch_fails_closed(self):
        result = validate_handoff("missing.json", "missing-report.json", "a" * 40, repo_root=Path.cwd(), binding_evidence="sidecar.json")
        self.assertFalse(result.ok)


if __name__ == "__main__":
    unittest.main()
