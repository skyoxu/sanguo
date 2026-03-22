import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

import _overlay_generator_model as modelmod


class OverlayGeneratorModelTests(unittest.TestCase):
    def test_parse_existing_page_markdown_should_extract_front_matter_purpose_and_sections(self) -> None:
        text = """---
PRD-ID: PRD-TEMPLATE-V1
Title: Sample Page
Status: Accepted
ADR-Refs:
  - ADR-0004
Arch-Refs:
  - CH04
Test-Refs:
  - scripts/python/validate_task_overlays.py
---

# Sample Page

Sample purpose paragraph.

Task coverage:

- 66, 67

## Scope

- Bullet A
- Bullet B

## Task Binding

- Bullet C
"""

        page = modelmod.parse_existing_page_markdown(
            filename="08-sample.md",
            page_kind="feature",
            markdown_text=text,
        )

        self.assertEqual("08-sample.md", page["filename"])
        self.assertEqual("feature", page["page_kind"])
        self.assertEqual("Sample Page", page["title"])
        self.assertEqual("Sample purpose paragraph.", page["purpose"])
        self.assertEqual(["ADR-0004"], page["adr_refs"])
        self.assertEqual(["CH04"], page["arch_refs"])
        self.assertEqual(["scripts/python/validate_task_overlays.py"], page["test_refs"])
        self.assertEqual(["66", "67"], page["task_ids"])
        self.assertEqual(["Scope", "Task Binding"], [section["heading"] for section in page["sections"]])


if __name__ == "__main__":
    unittest.main()
