import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

import _overlay_generator_patch as patchmod


class OverlayGeneratorPatchTests(unittest.TestCase):
    def test_merge_page_patch_should_replace_selected_fields_only(self) -> None:
        base_page = {
            "filename": "_index.md",
            "page_kind": "index",
            "title": "Old Title",
            "purpose": "Old purpose",
            "adr_refs": ["ADR-0003"],
            "arch_refs": ["CH03"],
            "test_refs": ["old-test"],
            "task_ids": ["1"],
            "sections": [
                {"heading": "Directory Role", "bullets": ["Old bullet"]},
            ],
        }
        patch_payload = {
            "title": "New Title",
            "purpose": "New purpose",
            "adr_refs": ["ADR-0004", "ADR-0005"],
            "arch_refs": ["CH04"],
            "test_refs": ["scripts/python/validate_task_overlays.py"],
            "task_ids": ["66"],
            "sections": [
                {"heading": "Directory Role", "bullets": ["New bullet"]},
                {"heading": "Document Groups", "bullets": ["Extra bullet"]},
            ],
        }

        merged = patchmod.merge_page_patch(base_page, patch_payload)

        self.assertEqual("_index.md", merged["filename"])
        self.assertEqual("index", merged["page_kind"])
        self.assertEqual("New Title", merged["title"])
        self.assertEqual("New purpose", merged["purpose"])
        self.assertEqual(["ADR-0004", "ADR-0005"], merged["adr_refs"])
        self.assertEqual(2, len(merged["sections"]))

    def test_build_base_page_from_profile_should_preserve_filename_and_kind(self) -> None:
        profile_page = {
            "filename": "ACCEPTANCE_CHECKLIST.md",
            "page_kind": "acceptance-checklist",
            "current_title": "Checklist",
            "headings": ["一、文档完整性验收", "二、架构设计验收"],
        }
        page_context = {
            "master_task_ids": ["74"],
            "back_task_ids": ["74"],
            "gameplay_task_ids": [],
        }

        base_page = patchmod.build_base_page_from_profile(profile_page, page_context)

        self.assertEqual("ACCEPTANCE_CHECKLIST.md", base_page["filename"])
        self.assertEqual("acceptance-checklist", base_page["page_kind"])
        self.assertEqual(["74"], base_page["task_ids"])
        self.assertEqual(2, len(base_page["sections"]))


if __name__ == "__main__":
    unittest.main()
