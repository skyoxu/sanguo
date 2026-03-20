import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

import _overlay_generator_scaffold as scaffoldmod


class OverlayGeneratorScaffoldTests(unittest.TestCase):
    def test_build_scaffold_base_page_should_prefer_current_page_model(self) -> None:
        current_page = {
            "filename": "_index.md",
            "page_kind": "index",
            "title": "Current Index",
            "purpose": "Current purpose",
            "adr_refs": ["ADR-0003"],
            "arch_refs": ["CH03"],
            "test_refs": ["scripts/python/validate_task_overlays.py"],
            "task_ids": ["1"],
            "sections": [{"heading": "Directory Role", "bullets": ["Old"]}],
        }
        profile_page = {
            "filename": "_index.md",
            "page_kind": "index",
            "current_title": "Profile Index",
            "headings": ["Directory Role", "Document Groups"],
        }
        page_context = {"master_task_ids": ["66"], "back_task_ids": [], "gameplay_task_ids": []}

        base_page = scaffoldmod.build_scaffold_base_page(profile_page, page_context, current_page=current_page)

        self.assertEqual("Current Index", base_page["title"])
        self.assertEqual("Current purpose", base_page["purpose"])
        self.assertEqual(["ADR-0003"], base_page["adr_refs"])
        self.assertEqual(["1"], base_page["task_ids"])
        self.assertEqual(1, len(base_page["sections"]))

    def test_merge_scaffold_update_should_preserve_title_and_section_headings_when_not_overridden(self) -> None:
        base_page = {
            "filename": "_index.md",
            "page_kind": "index",
            "title": "Current Index",
            "purpose": "Current purpose",
            "adr_refs": ["ADR-0003"],
            "arch_refs": ["CH03"],
            "test_refs": ["old-test"],
            "task_ids": ["1"],
            "sections": [
                {"heading": "Directory Role", "bullets": ["Old bullet"]},
                {"heading": "Document Groups", "bullets": ["Old group"]},
            ],
        }
        update = {
            "purpose": "Updated purpose",
            "task_ids": ["66"],
            "sections": [
                {"heading": "Directory Role", "bullets": ["New bullet"]},
                {"heading": "Document Groups", "bullets": ["New group"]},
            ],
        }

        merged = scaffoldmod.merge_scaffold_update(base_page, update)

        self.assertEqual("Current Index", merged["title"])
        self.assertEqual("Updated purpose", merged["purpose"])
        self.assertEqual(["66"], merged["task_ids"])
        self.assertEqual(["Directory Role", "Document Groups"], [section["heading"] for section in merged["sections"]])

    def test_select_pages_by_family_should_group_profile_entries(self) -> None:
        profile = [
            {"filename": "_index.md", "page_kind": "index"},
            {"filename": "ACCEPTANCE_CHECKLIST.md", "page_kind": "acceptance-checklist"},
            {"filename": "08-rules-freeze-and-assertion-routing.md", "page_kind": "routing"},
            {"filename": "08-Contracts-Security.md", "page_kind": "contracts"},
            {"filename": "08-t52-turn-window-and-event-ordering.md", "page_kind": "feature"},
            {"filename": "08-governance-freeze-change-control.md", "page_kind": "governance"},
        ]

        core = scaffoldmod.select_pages_by_family(profile, "core")
        contracts = scaffoldmod.select_pages_by_family(profile, "contracts")

        self.assertEqual(
            ["_index.md", "ACCEPTANCE_CHECKLIST.md", "08-rules-freeze-and-assertion-routing.md"],
            [item["filename"] for item in core],
        )
        self.assertEqual(["08-Contracts-Security.md"], [item["filename"] for item in contracts])


if __name__ == "__main__":
    unittest.main()
