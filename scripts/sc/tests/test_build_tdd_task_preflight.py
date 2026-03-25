#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_BUILD_DIR = REPO_ROOT / "scripts" / "sc" / "build"
SC_DIR = REPO_ROOT / "scripts" / "sc"
for candidate in (SC_BUILD_DIR, SC_DIR):
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


tdd_steps = _load_module("sc_build_tdd_steps_module", "scripts/sc/build/_tdd_steps.py")


class _FakeTriplet:
    def __init__(self, *, overlay: str, back: dict | None = None, gameplay: dict | None = None) -> None:
        self.task_id = "14"
        self.master = {
            "title": "Demo task",
            "status": "in-progress",
            "overlay": overlay,
        }
        self.back = back
        self.gameplay = gameplay
        self.taskdoc_path = None

    def adr_refs(self) -> list[str]:
        return ["ADR-0005"]

    def arch_refs(self) -> list[str]:
        return ["CH07"]

    def overlay(self) -> str:
        return str(self.master["overlay"])


class BuildTddTaskPreflightTests(unittest.TestCase):
    def test_run_task_preflight_should_pass_when_overlay_and_contract_refs_resolve(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out_dir = root / "logs" / "ci" / "2026-03-24" / "sc-build-tdd"
            overlay_index = root / "docs" / "architecture" / "overlays" / "PRD-demo" / "08" / "_index.md"
            overlay_checklist = root / "docs" / "architecture" / "overlays" / "PRD-demo" / "08" / "ACCEPTANCE_CHECKLIST.md"
            contract = root / "Game.Core" / "Contracts" / "Tasks" / "TaskUpdated.cs"
            for path in (overlay_index, overlay_checklist, contract):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("ok\n", encoding="utf-8")
            triplet = _FakeTriplet(
                overlay="docs/architecture/overlays/PRD-demo/08/_index.md",
                back={
                    "overlay_refs": [
                        "docs/architecture/overlays/PRD-demo/08/_index.md",
                        "docs/architecture/overlays/PRD-demo/08/ACCEPTANCE_CHECKLIST.md",
                    ],
                    "contractRefs": ["Game.Core/Contracts/Tasks/TaskUpdated.cs"],
                },
                gameplay={
                    "overlay_refs": [
                        "docs/architecture/overlays/PRD-demo/08/_index.md",
                    ],
                },
            )

            with mock.patch.object(tdd_steps, "repo_root", return_value=root):
                step = tdd_steps.run_task_preflight(triplet=triplet, out_dir=out_dir)

            self.assertEqual(0, step["rc"])
            self.assertEqual("ok", step["status"])
            report = json.loads((out_dir / "task-preflight.json").read_text(encoding="utf-8"))
            self.assertEqual([], report["errors"])
            self.assertEqual([], report["missing_contract_refs"])

    def test_run_task_preflight_should_fail_when_overlay_or_contract_path_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out_dir = root / "logs" / "ci" / "2026-03-24" / "sc-build-tdd"
            overlay_index = root / "docs" / "architecture" / "overlays" / "PRD-demo" / "08" / "_index.md"
            overlay_index.parent.mkdir(parents=True, exist_ok=True)
            overlay_index.write_text("ok\n", encoding="utf-8")
            triplet = _FakeTriplet(
                overlay="docs/architecture/overlays/PRD-demo/08/_index.md",
                back={
                    "overlay_refs": [
                        "docs/architecture/overlays/PRD-demo/08/_index.md",
                        "docs/architecture/overlays/PRD-demo/08/ACCEPTANCE_CHECKLIST.md",
                    ],
                    "contractRefs": ["Game.Core/Contracts/Tasks/MissingContract.cs"],
                },
            )

            with mock.patch.object(tdd_steps, "repo_root", return_value=root):
                step = tdd_steps.run_task_preflight(triplet=triplet, out_dir=out_dir)

            self.assertEqual(1, step["rc"])
            self.assertEqual("fail", step["status"])
            report = json.loads((out_dir / "task-preflight.json").read_text(encoding="utf-8"))
            self.assertTrue(any("ACCEPTANCE_CHECKLIST.md" in item for item in report["errors"]))
            self.assertTrue(any("MissingContract.cs" in item for item in report["errors"]))


if __name__ == "__main__":
    unittest.main()
