#!/usr/bin/env python3
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


sync_overlay_refs = _load_module("sync_task_overlay_refs_module", "scripts/python/sync_task_overlay_refs.py")


class SyncTaskOverlayRefsTests(unittest.TestCase):
    def test_skip_done_should_preserve_done_tasks_and_view_rows(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tasks_dir = root / ".taskmaster" / "tasks"
            tasks_dir.mkdir(parents=True, exist_ok=True)
            tasks_json = tasks_dir / "tasks.json"
            tasks_back = tasks_dir / "tasks_back.json"

            tasks_json.write_text(
                json.dumps(
                    {
                        "master": {
                            "tasks": [
                                {"id": 1, "status": "done", "overlay": "docs/old.md"},
                                {"id": 2, "status": "in-progress", "overlay": "docs/old.md"},
                            ]
                        }
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            tasks_back.write_text(
                json.dumps(
                    [
                        {"taskmaster_id": 1, "status": "todo", "overlay_refs": ["docs/old.md"]},
                        {"taskmaster_id": "2", "status": "todo", "overlay_refs": ["docs/old.md"]},
                    ],
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            paths = sync_overlay_refs.OverlayPaths(
                prd_id="PRD-X",
                base="docs/architecture/overlays/PRD-X/08",
                manifest=None,
                index="docs/architecture/overlays/PRD-X/08/_index.md",
                feature="docs/architecture/overlays/PRD-X/08/08-feature-slice.md",
                contracts=None,
                testing=None,
                observability=None,
                acceptance="docs/architecture/overlays/PRD-X/08/ACCEPTANCE_CHECKLIST.md",
            )

            master_payload, master_result = sync_overlay_refs.sync_master(tasks_json, paths, skip_done=True)
            done_ids = sync_overlay_refs._done_master_task_ids(master_payload)
            view_payload, view_result = sync_overlay_refs.sync_view(
                tasks_back,
                paths,
                skip_done=True,
                master_done_task_ids=done_ids,
            )

            self.assertEqual("docs/old.md", master_payload["master"]["tasks"][0]["overlay"])
            self.assertEqual(paths.index, master_payload["master"]["tasks"][1]["overlay"])
            self.assertEqual(["docs/old.md"], view_payload[0]["overlay_refs"])
            self.assertEqual(sync_overlay_refs._refs_for_task(paths), view_payload[1]["overlay_refs"])
            self.assertEqual(1, master_result.skipped_done_tasks)
            self.assertEqual(1, view_result.skipped_done_tasks)


    def test_stale_contract_ref_blocks_semantic_backlink_sync(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            view = root / "tasks_back.json"
            view.write_text(
                json.dumps([{
                    "taskmaster_id": 7,
                    "semantic_refs": ["FR-7"],
                    "contractRefs": ["core.missing.event"],
                }], ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            paths = sync_overlay_refs.OverlayPaths(
                prd_id="PRD-X",
                base="docs/architecture/overlays/PRD-X/08",
                manifest=None,
                index="docs/architecture/overlays/PRD-X/08/_index.md",
                feature=None,
                contracts=None,
                testing=None,
                observability=None,
                acceptance="docs/architecture/overlays/PRD-X/08/ACCEPTANCE_CHECKLIST.md",
            )
            with self.assertRaisesRegex(ValueError, "stale contract refs"):
                sync_overlay_refs.sync_view(
                    view,
                    paths,
                    skip_done=False,
                    master_done_task_ids=set(),
                    active_requirement_ids={"FR-7"},
                    allowed_contract_refs={"core.valid.event"},
                )

    def test_nonexistent_overlay_ref_fails_fast_before_sync(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            view = root / "tasks_back.json"
            view.write_text(
                json.dumps([{
                    "taskmaster_id": 10,
                    "overlay_refs": ["docs/architecture/overlays/OLD/08/missing.md"],
                    "semantic_refs": [],
                    "contractRefs": [],
                }], ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            paths = sync_overlay_refs.OverlayPaths(
                prd_id="PRD-X",
                base="docs/architecture/overlays/PRD-X/08",
                manifest=None,
                index="docs/architecture/overlays/PRD-X/08/_index.md",
                feature=None,
                contracts=None,
                testing=None,
                observability=None,
                acceptance="docs/architecture/overlays/PRD-X/08/ACCEPTANCE_CHECKLIST.md",
            )
            with self.assertRaisesRegex(ValueError, "stale overlay refs"):
                sync_overlay_refs.sync_view(
                    view,
                    paths,
                    skip_done=False,
                    master_done_task_ids=set(),
                    active_requirement_ids=set(),
                    allowed_contract_refs=set(),
                    repo_root=root,
                )

    def test_stale_contract_ref_blocks_even_without_semantic_refs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            view = root / "tasks_gameplay.json"
            view.write_text(
                json.dumps([{
                    "taskmaster_id": 9,
                    "semantic_refs": [],
                    "contractRefs": ["core.missing.event"],
                }], ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            paths = sync_overlay_refs.OverlayPaths(
                prd_id="PRD-X",
                base="docs/architecture/overlays/PRD-X/08",
                manifest=None,
                index="docs/architecture/overlays/PRD-X/08/_index.md",
                feature=None,
                contracts=None,
                testing=None,
                observability=None,
                acceptance="docs/architecture/overlays/PRD-X/08/ACCEPTANCE_CHECKLIST.md",
            )
            with self.assertRaisesRegex(ValueError, "stale contract refs"):
                sync_overlay_refs.sync_view(
                    view,
                    paths,
                    skip_done=False,
                    master_done_task_ids=set(),
                    active_requirement_ids=set(),
                    allowed_contract_refs={"core.valid.event"},
                )

    def test_chapter4_gap_report_is_machine_readable_and_blocks_missing_backlinks(self) -> None:
        report = sync_overlay_refs.build_chapter4_gap_report(
            [{
                "taskmaster_id": 8,
                "semantic_refs": ["FR-8"],
                "overlay_refs": ["docs/architecture/overlays/X/08/_index.md"],
                "overlay_requirement_refs": {},
                "contractRefs": ["core.valid.event"],
                "contract_requirement_refs": {},
            }],
            [],
        )
        self.assertEqual("newrouge.chapter4-semantic-gap-report.v1", report["schema_version"])
        self.assertEqual("blocked", report["status"])
        self.assertEqual(
            {"semantic_gap", "architecture_gap"},
            {row["gap_type"] for row in report["gaps"]},
        )

    def test_skip_done_flag_should_be_exposed_in_summary(self) -> None:
        result = sync_overlay_refs.FileSyncResult(
            file="tasks.json",
            total_tasks=5,
            changed_tasks=2,
            changed_ids=["2", "3"],
            skipped_done_tasks=1,
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tasks_dir = root / ".taskmaster" / "tasks"
            tasks_dir.mkdir(parents=True, exist_ok=True)
            out_path = sync_overlay_refs._write_summary(
                root=root,
                dry_run=True,
                status="dry-run",
                reason=None,
                paths=None,
                results=[result],
                missing=[],
                tasks_dir=tasks_dir,
            )

            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(1, payload["files"][0]["skipped_done_tasks"])


if __name__ == "__main__":
    unittest.main()
