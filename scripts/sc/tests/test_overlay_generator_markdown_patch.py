import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

import _overlay_generator_markdown_patch as patchmod


class OverlayGeneratorMarkdownPatchTests(unittest.TestCase):
    def test_apply_scaffold_update_to_existing_markdown_should_preserve_rich_intro_and_nested_sections(self) -> None:
        current_markdown = """---

PRD-ID: PRD-TEMPLATE-V1

Title: 08 Feature Slice Index (V3 Campaign Mode)

Status: Accepted

ADR-Refs:

  - ADR-0003

---

# PRD-TEMPLATE-V1 Feature Slice Index

This directory is the V3 campaign overlay root. It is driven by:

- `prd_template.md`

Compatibility note:

Some filenames intentionally keep old T2-oriented names.

## Directory Role

- Provide stable overlay targets for `T66~T175`.

## Document Groups

### Rules Freeze and Assertion Routing

- `08-rules-freeze-and-assertion-routing.md`

### Governance Owner Pages

- `08-governance-freeze-change-control.md`
"""
        scaffold_update = {
            "purpose": "Rewritten purpose that should not replace rich intro.",
            "task_ids": ["66", "67"],
            "sections": [
                {"heading": "Directory Role", "bullets": ["Updated role bullet"]},
                {"heading": "Document Groups", "bullets": ["This should not flatten nested headings"]},
            ],
        }

        patched = patchmod.apply_scaffold_update_to_existing_markdown(
            current_markdown=current_markdown,
            scaffold_update=scaffold_update,
        )

        self.assertIn("Some filenames intentionally keep old T2-oriented names.", patched)
        self.assertIn("### Rules Freeze and Assertion Routing", patched)
        self.assertIn("- Updated role bullet", patched)
        self.assertNotIn("This should not flatten nested headings", patched)
        self.assertNotIn("Rewritten purpose that should not replace rich intro.", patched)

    def test_apply_scaffold_update_to_existing_markdown_should_replace_simple_task_coverage_block(self) -> None:
        current_markdown = """---
PRD-ID: PRD-TEMPLATE-V1
Title: Checklist
Status: Draft
---

# V3 Campaign Acceptance Checklist

Simple intro.

Task coverage:

- 66, 67

## One

- Keep me
"""
        scaffold_update = {
            "task_ids": ["66", "67", "68"],
            "sections": [],
        }

        patched = patchmod.apply_scaffold_update_to_existing_markdown(
            current_markdown=current_markdown,
            scaffold_update=scaffold_update,
        )

        self.assertIn("Task coverage:", patched)
        self.assertIn("- 66, 67, 68", patched)
        self.assertNotIn("- 66, 67\n", patched)

    def test_apply_scaffold_update_to_existing_markdown_should_reject_foreign_section_headings(self) -> None:
        current_markdown = """---
PRD-ID: PRD-TEMPLATE-V1
Title: Index
Status: Accepted
---

# Index

## Directory Role

- Keep role

## Document Groups

- Keep groups
"""
        scaffold_update = {
            "sections": [
                {"heading": "一、文档完整性验收", "bullets": ["Wrong page content"]},
                {"heading": "二、架构设计验收", "bullets": ["Wrong page content"]},
            ]
        }

        patched = patchmod.apply_scaffold_update_to_existing_markdown(
            current_markdown=current_markdown,
            scaffold_update=scaffold_update,
        )

        self.assertEqual(current_markdown, patched)


if __name__ == "__main__":
    unittest.main()
