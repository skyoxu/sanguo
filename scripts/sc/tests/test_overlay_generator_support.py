import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

import _overlay_generator_support as support


class OverlayGeneratorSupportTests(unittest.TestCase):
    def test_parse_prd_docs_csv_should_split_and_trim(self) -> None:
        result = support.parse_prd_docs_csv(" PRD_TRACEABILITY_MATRIX.md,PRD_RULES_FREEZE.md , ,PRD_ACCEPTANCE_ASSERTIONS.md ")

        self.assertEqual(
            [
                "PRD_TRACEABILITY_MATRIX.md",
                "PRD_RULES_FREEZE.md",
                "PRD_ACCEPTANCE_ASSERTIONS.md",
            ],
            result,
        )

    def test_infer_prd_id_should_pick_most_common_overlay_root(self) -> None:
        tasks_json = {
            "master": {
                "tasks": [
                    {
                        "id": 66,
                        "overlay": "docs/architecture/overlays/PRD-TEMPLATE-V1/08/_index.md",
                    },
                    {
                        "id": 67,
                        "overlay": "docs/architecture/overlays/PRD-TEMPLATE-V1/08/08-rules-freeze-and-assertion-routing.md",
                    },
                    {
                        "id": 1,
                        "overlay": "docs/architecture/overlays/PRD-LEGACY/08/_index.md",
                    },
                ]
            }
        }
        tasks_back = [
            {
                "taskmaster_id": 66,
                "overlay_refs": [
                    "docs/architecture/overlays/PRD-TEMPLATE-V1/08/_index.md",
                    "docs/architecture/overlays/PRD-TEMPLATE-V1/08/ACCEPTANCE_CHECKLIST.md",
                ],
            }
        ]
        tasks_gameplay = [
            {
                "taskmaster_id": 67,
                "overlay_refs": [
                    "docs/architecture/overlays/PRD-TEMPLATE-V1/08/08-rules-freeze-and-assertion-routing.md"
                ],
            }
        ]

        result = support.infer_prd_id(None, tasks_json, tasks_back, tasks_gameplay)

        self.assertEqual("PRD-TEMPLATE-V1", result)

    def test_discover_companion_docs_should_use_explicit_paths_and_stage_doc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            prd_path = root / "prd_template.md"
            prd_path.write_text("# PRD\n", encoding="utf-8")
            (root / "PRD_TRACEABILITY_MATRIX.md").write_text("# Traceability\n", encoding="utf-8")
            (root / "PRD_RULES_FREEZE.md").write_text("# Freeze\n", encoding="utf-8")
            (root / "PRD_ACCEPTANCE_ASSERTIONS.md").write_text("# Assertions\n", encoding="utf-8")
            (root / "CURRENT_STAGE_FOR_BMAD.md").write_text("# Stage\n", encoding="utf-8")

            result = support.discover_companion_docs(
                prd_path,
                repo_root=root,
                explicit_paths=[
                    "PRD_TRACEABILITY_MATRIX.md",
                    "PRD_RULES_FREEZE.md",
                    "PRD_ACCEPTANCE_ASSERTIONS.md",
                ],
            )

            relpaths = [path.relative_to(root).as_posix() for path in result]
            self.assertEqual(
                [
                    "CURRENT_STAGE_FOR_BMAD.md",
                    "PRD_ACCEPTANCE_ASSERTIONS.md",
                    "PRD_RULES_FREEZE.md",
                    "PRD_TRACEABILITY_MATRIX.md",
                ],
                relpaths,
            )

    def test_validate_required_prd_docs_should_fail_when_explicit_required_docs_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            docs = [
                root / "PRD_TRACEABILITY_MATRIX.md",
                root / "CURRENT_STAGE_FOR_BMAD.md",
            ]
            for path in docs:
                path.write_text("# Doc\n", encoding="utf-8")

            missing = support.validate_required_prd_docs(
                prd_id="PRD-TEMPLATE-V1",
                companion_paths=docs,
                expected_doc_names=[
                    "PRD_TRACEABILITY_MATRIX.md",
                    "PRD_RULES_FREEZE.md",
                    "PRD_ACCEPTANCE_ASSERTIONS.md",
                ],
            )

            self.assertEqual(
                [
                    "PRD_RULES_FREEZE.md",
                    "PRD_ACCEPTANCE_ASSERTIONS.md",
                ],
                missing,
            )

    def test_validate_required_prd_docs_should_pass_when_explicit_required_docs_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            docs = [
                root / "PRD_TRACEABILITY_MATRIX.md",
                root / "PRD_RULES_FREEZE.md",
                root / "PRD_ACCEPTANCE_ASSERTIONS.md",
                root / "CURRENT_STAGE_FOR_BMAD.md",
            ]
            for path in docs:
                path.write_text("# Doc\n", encoding="utf-8")

            missing = support.validate_required_prd_docs(
                prd_id="PRD-TEMPLATE-V1",
                companion_paths=docs,
                expected_doc_names=[
                    "PRD_TRACEABILITY_MATRIX.md",
                    "PRD_RULES_FREEZE.md",
                    "PRD_ACCEPTANCE_ASSERTIONS.md",
                ],
            )

            self.assertEqual([], missing)

    def test_render_page_markdown_should_keep_required_acceptance_sections(self) -> None:
        page = {
            "filename": "ACCEPTANCE_CHECKLIST.md",
            "page_kind": "acceptance-checklist",
            "title": "Acceptance Checklist",
            "purpose": "Checklist coverage",
            "adr_refs": ["ADR-0004", "ADR-0005"],
            "arch_refs": ["CH04", "CH07"],
            "test_refs": ["scripts/python/validate_task_overlays.py"],
            "task_ids": ["66", "67"],
            "sections": [
                {"heading": "一、文档完整性验收", "bullets": ["Checklist item A"]},
                {"heading": "二、架构设计验收", "bullets": ["Checklist item B"]},
                {"heading": "三、代码实现验收", "bullets": ["Checklist item C"]},
                {"heading": "四、测试框架验收", "bullets": ["Checklist item D"]},
            ],
        }

        text = support.render_page_markdown(page, prd_id="PRD-TEMPLATE-V1")

        self.assertIn("PRD-ID: PRD-TEMPLATE-V1", text)
        self.assertIn("一、文档完整性验收", text)
        self.assertIn("二、架构设计验收", text)
        self.assertIn("三、代码实现验收", text)
        self.assertIn("四、测试框架验收", text)


if __name__ == "__main__":
    unittest.main()
