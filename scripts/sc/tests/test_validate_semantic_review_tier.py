#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import sys
import unittest
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON_DIR = REPO_ROOT / "scripts" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))
TEST_TMP_ROOT = REPO_ROOT / "logs" / "test-temp"
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)

import backfill_semantic_review_tier as backfill_module  # noqa: E402
import validate_semantic_review_tier as validate_module  # noqa: E402


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


class ValidateSemanticReviewTierTests(unittest.TestCase):
    def _fresh_root(self, name: str) -> Path:
        root = TEST_TMP_ROOT / f"{name}-{uuid.uuid4().hex}"
        if root.exists():
            shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        return root

    def _create_repo(self, root: Path) -> tuple[Path, Path, Path]:
        tasks_json_path = root / "taskmaster" / "tasks" / "tasks.json"
        tasks_back_path = root / "taskmaster" / "tasks" / "tasks_back.json"
        tasks_gameplay_path = root / "taskmaster" / "tasks" / "tasks_gameplay.json"

        tasks_json = {
            "master": {
                "tasks": [
                    {
                        "id": 1,
                        "title": "Tune reward values",
                        "priority": "P1",
                        "details": "Balance gameplay rewards and round pacing.",
                    },
                    {
                        "id": 2,
                        "title": "Harden workflows and pipelines",
                        "priority": "P2",
                        "details": "Improve observability, rollback handling, and release safety.",
                    },
                ]
            }
        }
        tasks_back = [
            {
                "taskmaster_id": 1,
                "title": "Tune reward values",
                "priority": "P1",
                "layer": "gameplay",
            },
            {
                "taskmaster_id": 2,
                "title": "Harden workflows and pipelines",
                "priority": "P2",
                "layer": "ci",
                "contractRefs": ["Game.Core/Contracts/Tasks/TaskUpdated.cs"],
            },
        ]
        tasks_gameplay = [
            {
                "taskmaster_id": 1,
                "title": "Tune reward values",
                "priority": "P1",
                "layer": "gameplay",
            },
            {
                "taskmaster_id": 2,
                "title": "Harden workflows and pipelines",
                "priority": "P2",
                "layer": "ci",
                "contractRefs": ["Game.Core/Contracts/Tasks/TaskUpdated.cs"],
            },
        ]
        _write_json(tasks_json_path, tasks_json)
        _write_json(tasks_back_path, tasks_back)
        _write_json(tasks_gameplay_path, tasks_gameplay)
        return tasks_json_path, tasks_back_path, tasks_gameplay_path

    def test_validator_should_pass_after_conservative_backfill(self) -> None:
        root = self._fresh_root("validate-pass")
        tasks_json_path, tasks_back_path, tasks_gameplay_path = self._create_repo(root)
        backfill_summary = root / "backfill-summary.json"
        validate_summary = root / "validate-summary.json"

        backfill_rc = backfill_module.main(
            [
                "--tasks-json-path",
                str(tasks_json_path),
                "--tasks-back-path",
                str(tasks_back_path),
                "--tasks-gameplay-path",
                str(tasks_gameplay_path),
                "--summary-path",
                str(backfill_summary),
                "--write",
            ]
        )
        validate_rc = validate_module.main(
            [
                "--tasks-json-path",
                str(tasks_json_path),
                "--tasks-back-path",
                str(tasks_back_path),
                "--tasks-gameplay-path",
                str(tasks_gameplay_path),
                "--summary-path",
                str(validate_summary),
            ]
        )

        self.assertEqual(0, backfill_rc)
        self.assertEqual(0, validate_rc)
        summary = json.loads(validate_summary.read_text(encoding="utf-8"))
        self.assertEqual("ok", summary["status"])
        self.assertEqual(0, summary["error_count"])

    def test_validator_should_fail_when_field_missing(self) -> None:
        root = self._fresh_root("validate-missing")
        tasks_json_path, tasks_back_path, tasks_gameplay_path = self._create_repo(root)
        summary_path = root / "validate-summary.json"

        rc = validate_module.main(
            [
                "--tasks-json-path",
                str(tasks_json_path),
                "--tasks-back-path",
                str(tasks_back_path),
                "--tasks-gameplay-path",
                str(tasks_gameplay_path),
                "--summary-path",
                str(summary_path),
            ]
        )

        self.assertEqual(1, rc)
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        rules = {item["rule"] for item in summary["errors"]}
        self.assertIn("missing_semantic_review_tier", rules)

    def test_validator_should_fail_when_value_mismatches_computed_tier(self) -> None:
        root = self._fresh_root("validate-mismatch")
        tasks_json_path, tasks_back_path, tasks_gameplay_path = self._create_repo(root)
        back_payload = json.loads(tasks_back_path.read_text(encoding="utf-8"))
        gameplay_payload = json.loads(tasks_gameplay_path.read_text(encoding="utf-8"))
        back_payload[1]["semantic_review_tier"] = "auto"
        gameplay_payload[1]["semantic_review_tier"] = "auto"
        _write_json(tasks_back_path, back_payload)
        _write_json(tasks_gameplay_path, gameplay_payload)
        summary_path = root / "validate-summary.json"

        rc = validate_module.main(
            [
                "--tasks-json-path",
                str(tasks_json_path),
                "--tasks-back-path",
                str(tasks_back_path),
                "--tasks-gameplay-path",
                str(tasks_gameplay_path),
                "--summary-path",
                str(summary_path),
            ]
        )

        self.assertEqual(1, rc)
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        rules = {item["rule"] for item in summary["errors"]}
        self.assertIn("semantic_review_tier_mismatch", rules)

    def test_validator_should_fail_on_legacy_camel_case_field(self) -> None:
        root = self._fresh_root("validate-camel")
        tasks_json_path, tasks_back_path, tasks_gameplay_path = self._create_repo(root)
        back_payload = json.loads(tasks_back_path.read_text(encoding="utf-8"))
        gameplay_payload = json.loads(tasks_gameplay_path.read_text(encoding="utf-8"))
        back_payload[0]["semanticReviewTier"] = "auto"
        gameplay_payload[0]["semanticReviewTier"] = "auto"
        _write_json(tasks_back_path, back_payload)
        _write_json(tasks_gameplay_path, gameplay_payload)
        summary_path = root / "validate-summary.json"

        rc = validate_module.main(
            [
                "--tasks-json-path",
                str(tasks_json_path),
                "--tasks-back-path",
                str(tasks_back_path),
                "--tasks-gameplay-path",
                str(tasks_gameplay_path),
                "--summary-path",
                str(summary_path),
                "--allow-missing",
            ]
        )

        self.assertEqual(1, rc)
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        rules = {item["rule"] for item in summary["errors"]}
        self.assertIn("legacy_camel_case_field", rules)

    def test_validator_should_fail_when_views_drift(self) -> None:
        root = self._fresh_root("validate-cross-view-drift")
        tasks_json_path, tasks_back_path, tasks_gameplay_path = self._create_repo(root)
        backfill_module.main(
            [
                "--tasks-json-path",
                str(tasks_json_path),
                "--tasks-back-path",
                str(tasks_back_path),
                "--tasks-gameplay-path",
                str(tasks_gameplay_path),
                "--write",
            ]
        )
        back_payload = json.loads(tasks_back_path.read_text(encoding="utf-8"))
        gameplay_payload = json.loads(tasks_gameplay_path.read_text(encoding="utf-8"))
        back_payload[1]["semantic_review_tier"] = "full"
        gameplay_payload[1]["semantic_review_tier"] = "auto"
        _write_json(tasks_back_path, back_payload)
        _write_json(tasks_gameplay_path, gameplay_payload)
        summary_path = root / "validate-summary.json"

        rc = validate_module.main(
            [
                "--tasks-json-path",
                str(tasks_json_path),
                "--tasks-back-path",
                str(tasks_back_path),
                "--tasks-gameplay-path",
                str(tasks_gameplay_path),
                "--summary-path",
                str(summary_path),
            ]
        )

        self.assertEqual(1, rc)
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        rules = {item["rule"] for item in summary["errors"]}
        self.assertIn("cross_view_tier_mismatch", rules)


if __name__ == "__main__":
    unittest.main()
