#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
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


artifact_schema = _load_module("artifact_schema_test_module", "scripts/sc/_artifact_schema.py")
inspect_run = _load_module("inspect_run_test_module", "scripts/python/inspect_run.py")

FIXTURE_ROOT = REPO_ROOT / "scripts" / "sc" / "tests" / "fixtures" / "run_replay"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class RunArtifactSchemaTests(unittest.TestCase):
    def test_pipeline_fixture_sidecars_should_validate(self) -> None:
        root = FIXTURE_ROOT / "pipeline_pass"
        latest_path = root / "logs" / "ci" / "2026-03-22" / "sc-review-pipeline-task-7" / "latest.json"
        latest = _read_json(latest_path)
        out_dir = root / latest["latest_out_dir"]
        artifact_schema.validate_pipeline_latest_index_payload(latest)
        artifact_schema.validate_pipeline_execution_context_payload(_read_json(out_dir / "execution-context.json"))
        artifact_schema.validate_pipeline_repair_guide_payload(_read_json(out_dir / "repair-guide.json"))

    def test_local_hard_fixture_sidecars_should_validate(self) -> None:
        root = FIXTURE_ROOT / "local_hard_fail"
        latest_path = root / "logs" / "ci" / "2026-03-22" / "local-hard-checks-latest.json"
        latest = _read_json(latest_path)
        out_dir = root / latest["out_dir"]
        artifact_schema.validate_local_hard_checks_latest_index_payload(latest)
        artifact_schema.validate_local_hard_checks_execution_context_payload(_read_json(out_dir / "execution-context.json"))
        artifact_schema.validate_local_hard_checks_repair_guide_payload(_read_json(out_dir / "repair-guide.json"))

    def test_pipeline_latest_index_should_reject_unbudgeted_field(self) -> None:
        root = FIXTURE_ROOT / "pipeline_pass"
        latest_path = root / "logs" / "ci" / "2026-03-22" / "sc-review-pipeline-task-7" / "latest.json"
        latest = _read_json(latest_path)
        latest["unexpected_field"] = "drift"
        with self.assertRaises(artifact_schema.ArtifactSchemaError):
            artifact_schema.validate_pipeline_latest_index_payload(latest)


class InspectRunTests(unittest.TestCase):
    def test_inspect_run_should_report_pipeline_fixture_ok(self) -> None:
        root = FIXTURE_ROOT / "pipeline_pass"
        latest = "logs/ci/2026-03-22/sc-review-pipeline-task-7/latest.json"
        rc, payload = inspect_run.inspect_run_artifacts(repo_root=root, latest=latest)
        self.assertEqual(0, rc)
        self.assertEqual("pipeline", payload["kind"])
        self.assertEqual("ok", payload["status"])
        self.assertEqual("ok", payload["failure"]["code"])
        self.assertEqual("7", payload["task_id"])
        self.assertEqual("not-needed", payload["repair_status"])

    def test_inspect_run_should_classify_local_hard_fail(self) -> None:
        root = FIXTURE_ROOT / "local_hard_fail"
        latest = "logs/ci/2026-03-22/local-hard-checks-latest.json"
        rc, payload = inspect_run.inspect_run_artifacts(repo_root=root, latest=latest)
        self.assertEqual(1, rc)
        self.assertEqual("local-hard-checks", payload["kind"])
        self.assertEqual("fail", payload["status"])
        self.assertEqual("step-failed", payload["failure"]["code"])
        self.assertEqual("run-dotnet", payload["failed_step"])

    def test_inspect_run_should_resolve_explicit_latest_bundle_outside_repo_root(self) -> None:
        latest = (
            "scripts/sc/tests/fixtures/run_replay/pipeline_pass/logs/ci/2026-03-22/"
            "sc-review-pipeline-task-7/latest.json"
        )
        rc, payload = inspect_run.inspect_run_artifacts(repo_root=REPO_ROOT, latest=latest)
        self.assertEqual(0, rc)
        self.assertEqual("ok", payload["failure"]["code"])


if __name__ == "__main__":
    unittest.main()
