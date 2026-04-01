#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


validate_task_overlays = _load_module("validate_task_overlays_scope_module", "scripts/python/validate_task_overlays.py")


class ValidateTaskOverlaysScopeTests(unittest.TestCase):
    def test_validate_task_file_should_only_check_requested_task_id(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            adr_dir = root / "docs" / "adr"
            adr_dir.mkdir(parents=True, exist_ok=True)
            (adr_dir / "ADR-0001-sample.md").write_text("# ADR-0001\n", encoding="utf-8")

            overlay_dir = root / "docs" / "architecture" / "overlays" / "PRD-X" / "08"
            overlay_dir.mkdir(parents=True, exist_ok=True)
            (overlay_dir / "_index.md").write_text("# Overlay\n", encoding="utf-8")
            (overlay_dir / "ACCEPTANCE_CHECKLIST.md").write_text(
                "---\n"
                "PRD-ID: PRD-X\n"
                "Title: Sample\n"
                "Status: Draft\n"
                "ADR-Refs:\n"
                "- ADR-0001\n"
                "Test-Refs:\n"
                "- scripts/python/validate_task_overlays.py\n"
                "---\n\n"
                "一、文档完整性验收\n"
                "二、架构设计验收\n"
                "三、代码实现验收\n"
                "四、测试框架验收\n",
                encoding="utf-8",
            )

            task_file = root / "tasks_back.json"
            task_file.write_text(
                json.dumps(
                    [
                        {
                            "taskmaster_id": 1,
                            "overlay_refs": [
                                "docs/architecture/overlays/PRD-X/08/_index.md",
                                "docs/architecture/overlays/PRD-X/08/ACCEPTANCE_CHECKLIST.md",
                            ],
                        },
                        {
                            "taskmaster_id": 2,
                            "overlay_refs": [],
                        },
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            checked, passed = validate_task_overlays.validate_task_file(
                root,
                task_file,
                "tasks_back.json",
                {"ADR-0001"},
                task_id="1",
            )

            self.assertEqual(1, checked)
            self.assertEqual(1, passed)


if __name__ == "__main__":
    unittest.main()
