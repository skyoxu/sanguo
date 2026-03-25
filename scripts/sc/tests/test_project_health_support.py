#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


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


project_health = _load_module("project_health_support_test_module", "scripts/python/_project_health_support.py")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class ProjectHealthSupportTests(unittest.TestCase):
    def test_detect_project_stage_should_flag_examples_only_triplet(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write(root / "project.godot", "[application]\nconfig/name=\"Demo\"\n")
            _write(root / "README.md", "# Demo\n")
            _write(root / "AGENTS.md", "# Demo\n")
            _write(root / "examples" / "taskmaster" / "tasks.json", "{}\n")
            _write(root / "examples" / "taskmaster" / "tasks_back.json", "{}\n")
            _write(root / "examples" / "taskmaster" / "tasks_gameplay.json", "{}\n")

            payload = project_health.detect_project_stage(root)

            self.assertEqual("triplet-missing", payload["stage"])
            self.assertEqual("warn", payload["status"])
            self.assertFalse(payload["signals"]["real_task_triplet"])
            self.assertTrue(payload["signals"]["example_task_triplet"])

    def test_doctor_project_should_report_missing_real_triplet_as_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write(root / "project.godot", "[application]\nconfig/name=\"Demo\"\n")
            _write(root / "README.md", "# Demo\n")
            _write(root / "AGENTS.md", "# Demo\n")
            _write(root / "Game.sln", "Microsoft Visual Studio Solution File, Format Version 12.00\n")
            _write(root / "Game.Core.Tests" / "Game.Core.Tests.csproj", "<Project />\n")
            _write(root / "workflow.md", "# Workflow\n")
            _write(root / "DELIVERY_PROFILE.md", "# Delivery\n")
            _write(root / "examples" / "taskmaster" / "tasks.json", "{}\n")
            _write(root / "examples" / "taskmaster" / "tasks_back.json", "{}\n")
            _write(root / "examples" / "taskmaster" / "tasks_gameplay.json", "{}\n")

            payload = project_health.doctor_project(root)

            self.assertEqual("warn", payload["status"])
            checks = {item["id"]: item for item in payload["checks"]}
            self.assertEqual("warn", checks["task-triplet-real"]["status"])
            self.assertEqual("ok", checks["task-triplet-example"]["status"])
            self.assertIn("create", checks["task-triplet-real"]["recommendation"])

    def test_doctor_project_should_treat_example_triplet_as_optional_when_real_triplet_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write(root / "project.godot", "[application]\nconfig/name=\"Demo\"\n")
            _write(root / "README.md", "# Demo\n")
            _write(root / "AGENTS.md", "# Demo\n")
            _write(root / "Game.sln", "Microsoft Visual Studio Solution File, Format Version 12.00\n")
            _write(root / "Game.Core.Tests" / "Game.Core.Tests.csproj", "<Project />\n")
            _write(root / ".taskmaster" / "tasks" / "tasks.json", "{\"tasks\": []}\n")
            _write(root / ".taskmaster" / "tasks" / "tasks_back.json", "{\"tasks\": []}\n")
            _write(root / ".taskmaster" / "tasks" / "tasks_gameplay.json", "{\"tasks\": []}\n")
            _write(root / "docs" / "workflows" / "run-protocol.md", "# run protocol\n")
            _write(root / "docs" / "workflows" / "local-hard-checks.md", "# local hard checks\n")

            payload = project_health.doctor_project(root)
            checks = {item["id"]: item for item in payload["checks"]}

            self.assertEqual("ok", checks["task-triplet-real"]["status"])
            self.assertEqual("ok", checks["task-triplet-example"]["status"])
            self.assertIn("optional", checks["task-triplet-example"]["summary"])
            self.assertEqual("ok", checks["workflow-docs"]["status"])

    def test_check_directory_boundaries_should_detect_core_and_base_violations(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write(root / "Game.Core" / "Foo.cs", "using Godot;\npublic sealed class Foo {}\n")
            _write(root / "Game.Core" / "Contracts" / "Bar.cs", "public sealed class Bar { public Godot.Node? Node { get; set; } }\n")
            _write(root / "docs" / "architecture" / "base" / "01-introduction.md", "This file leaked PRD-demo.\n")

            payload = project_health.check_directory_boundaries(root)

            self.assertEqual("fail", payload["status"])
            violations = {item["rule_id"]: item for item in payload["violations"]}
            self.assertIn("game-core-no-godot", violations)
            self.assertIn("contracts-no-godot", violations)
            self.assertIn("base-docs-no-prd-leak", violations)

    def test_check_directory_boundaries_should_skip_taskdoc_warning_when_real_triplet_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write(root / ".taskmaster" / "tasks" / "tasks.json", "{\"tasks\": []}\n")
            _write(root / ".taskmaster" / "tasks" / "tasks_back.json", "{\"tasks\": []}\n")
            _write(root / ".taskmaster" / "tasks" / "tasks_gameplay.json", "{\"tasks\": []}\n")

            with mock.patch.dict(
                project_health.check_directory_boundaries.__globals__,
                {"git_tracked_matches": lambda *_args, **_kwargs: ["taskdoc/2.md"]},
            ):
                payload = project_health.check_directory_boundaries(root)

            self.assertEqual("ok", payload["status"])
            self.assertFalse(
                any(item["rule_id"] == "root-taskdoc-not-tracked" for item in payload.get("warnings", []))
            )

    def test_check_directory_boundaries_should_warn_taskdoc_when_real_triplet_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            with mock.patch.dict(
                project_health.check_directory_boundaries.__globals__,
                {"git_tracked_matches": lambda *_args, **_kwargs: ["taskdoc/2.md"]},
            ):
                payload = project_health.check_directory_boundaries(root)

            self.assertEqual("warn", payload["status"])
            self.assertTrue(any(item["rule_id"] == "root-taskdoc-not-tracked" for item in payload["warnings"]))

    def test_write_project_health_record_should_refresh_dashboard_and_latest_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_health.write_project_health_record(
                root=root,
                kind="detect-project-stage",
                payload={"kind": "detect-project-stage", "status": "warn", "summary": "triplet missing"},
            )
            project_health.write_project_health_record(
                root=root,
                kind="doctor-project",
                payload={"kind": "doctor-project", "status": "ok", "summary": "doctor ok"},
            )
            project_health.write_project_health_record(
                root=root,
                kind="check-directory-boundaries",
                payload={"kind": "check-directory-boundaries", "status": "fail", "summary": "boundary fail"},
            )

            latest_index = json.loads(
                (root / "logs" / "ci" / "project-health" / "latest.json").read_text(encoding="utf-8")
            )
            latest_html = (root / "logs" / "ci" / "project-health" / "latest.html").read_text(encoding="utf-8")

            self.assertEqual(3, len(latest_index["records"]))
            self.assertIn("triplet missing", latest_html)
            self.assertIn("doctor ok", latest_html)
            self.assertIn("boundary fail", latest_html)


if __name__ == "__main__":
    unittest.main()
