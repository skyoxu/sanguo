#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
PYTHON_DIR = REPO_ROOT / "scripts" / "python"
for candidate in (SC_DIR, PYTHON_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))


def _load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


inspect_run = _load_module("inspect_run_compact_contract_module", "scripts/python/inspect_run.py")
resume_task = _load_module("resume_task_compact_contract_module", "scripts/python/resume_task.py")
sidecar_schema = _load_module("sidecar_schema_compact_contract_module", "scripts/sc/_sidecar_schema.py")


class RecoveryCompactContractTests(unittest.TestCase):
    def _assert_matches_schema(self, payload: dict[str, str]) -> None:
        schema = sidecar_schema._load_schema(
            REPO_ROOT / "scripts" / "sc" / "schemas" / "sc-recovery-compact.schema.json",
            "sc-recovery-compact",
        )
        if sidecar_schema.jsonschema is not None:
            errors = sidecar_schema._validate_with_jsonschema(payload, schema)
            self.assertEqual([], errors)
        else:
            self.assertEqual(set(schema["required"]), set(payload))
            self.assertFalse(bool(schema.get("additionalProperties")))
            self.assertRegex(payload["turn_count"], r"^[0-9]+$")

    def test_compact_example_should_match_schema(self) -> None:
        example_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-recovery-compact.example.json"
        import json

        payload = json.loads(example_path.read_text(encoding="utf-8"))
        self._assert_matches_schema(payload)
        self.assertEqual("pause", payload["approval_recommended_action"])
        self.assertEqual("run-15:turn-2", payload["latest_turn"])

    def test_inspect_and_resume_compact_payload_should_match_schema_and_shared_shape(self) -> None:
        payload = {
            "task_id": "15",
            "run_id": "run-15",
            "recommended_action": "needs-fix-fast",
            "recommended_command": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 15 --max-rounds 1",
            "forbidden_commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 15"],
            "failure": {"code": "review-needs-fix"},
            "latest_summary_signals": {"reason": "rerun_blocked:repeat_review_needs_fix"},
            "chapter6_hints": {
                "next_action": "needs-fix-fast",
                "blocked_by": "rerun_guard",
            },
            "approval": {
                "status": "pending",
                "recommended_action": "pause",
                "allowed_actions": ["inspect", "pause"],
                "blocked_actions": ["fork", "resume", "rerun"],
            },
            "run_event_summary": {
                "latest_turn_id": "run-15:turn-2",
                "turn_count": 2,
            },
        }

        inspect_compact = inspect_run._compact_recommendation_payload(payload)
        resume_compact = resume_task._compact_recommendation_payload(payload)

        self.assertEqual(inspect_compact, resume_compact)

        self._assert_matches_schema(inspect_compact)
        self.assertEqual("pause", inspect_compact["approval_recommended_action"])
        self.assertEqual("run-15:turn-2", inspect_compact["latest_turn"])
        self.assertEqual("2", inspect_compact["turn_count"])

    def test_local_hard_checks_compact_example_should_match_schema(self) -> None:
        example_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-local-hard-checks-compact.example.json"
        import json

        payload = json.loads(example_path.read_text(encoding="utf-8"))

        self._assert_matches_schema(payload)
        self.assertEqual("repo", payload["task_id"])
        self.assertEqual("rerun", payload["recommended_action"])
        self.assertEqual("not-needed", payload["approval_status"])
        self.assertEqual("0", payload["turn_count"])

    def test_pipeline_compact_example_should_match_schema(self) -> None:
        example_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-pipeline-compact.example.json"
        import json

        payload = json.loads(example_path.read_text(encoding="utf-8"))

        self._assert_matches_schema(payload)
        self.assertEqual("15", payload["task_id"])
        self.assertEqual("pause", payload["recommended_action"])
        self.assertEqual("approval_pending", payload["blocked_by"])
        self.assertEqual("0", payload["turn_count"])


if __name__ == "__main__":
    unittest.main()
