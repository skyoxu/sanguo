import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

import _overlay_generator_support as support

SCRIPT_PATH = REPO_ROOT / "scripts" / "sc" / "llm_generate_overlays_from_prd.py"
SPEC = importlib.util.spec_from_file_location("llm_generate_overlays_from_prd_script", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
SCRIPT_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCRIPT_MODULE)


class OverlayGeneratorFlowTests(unittest.TestCase):
    def test_parser_should_accept_prd_docs_csv_argument(self) -> None:
        parser = SCRIPT_MODULE._build_parser()

        args = parser.parse_args(
            [
                "--prd",
                "prd_template.md",
                "--prd-docs",
                "PRD_TRACEABILITY_MATRIX.md,PRD_RULES_FREEZE.md,PRD_ACCEPTANCE_ASSERTIONS.md",
            ]
        )

        self.assertEqual("prd_template.md", args.prd)
        self.assertEqual(
            "PRD_TRACEABILITY_MATRIX.md,PRD_RULES_FREEZE.md,PRD_ACCEPTANCE_ASSERTIONS.md",
            args.prd_docs,
        )

    def test_parser_should_accept_dry_run_flag(self) -> None:
        parser = SCRIPT_MODULE._build_parser()

        args = parser.parse_args(
            [
                "--prd",
                "prd_template.md",
                "--prd-docs",
                "PRD_TRACEABILITY_MATRIX.md,PRD_RULES_FREEZE.md,PRD_ACCEPTANCE_ASSERTIONS.md",
                "--dry-run",
            ]
        )

        self.assertTrue(bool(args.dry_run))

    def test_parser_should_accept_page_filter_csv(self) -> None:
        parser = SCRIPT_MODULE._build_parser()

        args = parser.parse_args(
            [
                "--prd",
                "prd_template.md",
                "--prd-docs",
                "PRD_TRACEABILITY_MATRIX.md,PRD_RULES_FREEZE.md,PRD_ACCEPTANCE_ASSERTIONS.md",
                "--page-filter",
                "_index.md,ACCEPTANCE_CHECKLIST.md",
            ]
        )

        self.assertEqual("_index.md,ACCEPTANCE_CHECKLIST.md", args.page_filter)

    def test_parser_should_accept_page_mode(self) -> None:
        parser = SCRIPT_MODULE._build_parser()

        args = parser.parse_args(
            [
                "--prd",
                "prd_template.md",
                "--prd-docs",
                "PRD_TRACEABILITY_MATRIX.md,PRD_RULES_FREEZE.md,PRD_ACCEPTANCE_ASSERTIONS.md",
                "--page-mode",
                "patch",
            ]
        )

        self.assertEqual("patch", args.page_mode)

    def test_parser_should_default_page_mode_to_scaffold(self) -> None:
        parser = SCRIPT_MODULE._build_parser()

        args = parser.parse_args(
            [
                "--prd",
                "prd_template.md",
                "--prd-docs",
                "PRD_TRACEABILITY_MATRIX.md,PRD_RULES_FREEZE.md,PRD_ACCEPTANCE_ASSERTIONS.md",
            ]
        )

        self.assertEqual("scaffold", args.page_mode)

    def test_parser_should_accept_page_family(self) -> None:
        parser = SCRIPT_MODULE._build_parser()

        args = parser.parse_args(
            [
                "--prd",
                "prd_template.md",
                "--prd-docs",
                "PRD_TRACEABILITY_MATRIX.md,PRD_RULES_FREEZE.md,PRD_ACCEPTANCE_ASSERTIONS.md",
                "--page-family",
                "core",
            ]
        )

        self.assertEqual("core", args.page_family)

    def test_parser_should_accept_run_suffix(self) -> None:
        parser = SCRIPT_MODULE._build_parser()

        args = parser.parse_args(
            [
                "--prd",
                "prd_template.md",
                "--prd-docs",
                "PRD_TRACEABILITY_MATRIX.md,PRD_RULES_FREEZE.md,PRD_ACCEPTANCE_ASSERTIONS.md",
                "--run-suffix",
                "batch-a",
            ]
        )

        self.assertEqual("batch-a", args.run_suffix)

    def test_build_output_dir_name_should_use_explicit_run_suffix(self) -> None:
        name = SCRIPT_MODULE._build_output_dir_name("PRD-TEMPLATE-V1", "batch-a")

        self.assertEqual("sc-llm-overlay-gen-prd-template-v1--batch-a", name)

    def test_build_output_dir_name_should_generate_default_unique_suffix(self) -> None:
        with patch.object(SCRIPT_MODULE, "_default_run_suffix", return_value="auto-123456"):
            name = SCRIPT_MODULE._build_output_dir_name("PRD-TEMPLATE-V1", "")

        self.assertEqual("sc-llm-overlay-gen-prd-template-v1--auto-123456", name)

    def test_reset_dir_should_remove_stale_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            target = Path(tmp_dir) / "generated"
            target.mkdir(parents=True, exist_ok=True)
            (target / "stale.md").write_text("old\n", encoding="utf-8")

            SCRIPT_MODULE._reset_dir(target)

            self.assertTrue(target.exists())
            self.assertEqual([], list(target.iterdir()))

    def test_discover_profile_and_compare_should_report_expected_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            existing_dir = root / "docs" / "architecture" / "overlays" / "PRD-TEMPLATE-V1" / "08"
            existing_dir.mkdir(parents=True, exist_ok=True)
            (existing_dir / "_index.md").write_text("# Existing Index\n", encoding="utf-8")
            (existing_dir / "ACCEPTANCE_CHECKLIST.md").write_text("# Existing Checklist\n", encoding="utf-8")

            profile = support.discover_existing_overlay_profile(root, "PRD-TEMPLATE-V1")

            self.assertEqual(["ACCEPTANCE_CHECKLIST.md", "_index.md"], sorted(item["filename"] for item in profile))

            generated_dir = root / "logs" / "generated" / "PRD-TEMPLATE-V1" / "08"
            generated_dir.mkdir(parents=True, exist_ok=True)
            for page in [
                {
                    "filename": "_index.md",
                    "page_kind": "index",
                    "title": "Generated Index",
                    "purpose": "Index",
                    "adr_refs": ["ADR-0004"],
                    "arch_refs": ["CH04"],
                    "test_refs": ["scripts/python/validate_task_overlays.py"],
                    "task_ids": ["66"],
                    "sections": [{"heading": "Directory Role", "bullets": ["Index body"]}],
                },
                {
                    "filename": "ACCEPTANCE_CHECKLIST.md",
                    "page_kind": "acceptance-checklist",
                    "title": "Generated Checklist",
                    "purpose": "Checklist",
                    "adr_refs": ["ADR-0004"],
                    "arch_refs": ["CH04"],
                    "test_refs": ["scripts/python/validate_task_overlays.py"],
                    "task_ids": ["66"],
                    "sections": [
                        {"heading": "一、文档完整性验收", "bullets": ["A"]},
                        {"heading": "二、架构设计验收", "bullets": ["B"]},
                        {"heading": "三、代码实现验收", "bullets": ["C"]},
                        {"heading": "四、测试框架验收", "bullets": ["D"]},
                    ],
                },
            ]:
                (generated_dir / page["filename"]).write_text(
                    support.render_page_markdown(page, prd_id="PRD-TEMPLATE-V1"),
                    encoding="utf-8",
                )

            comparison = support.compare_overlay_dirs(generated_dir, existing_dir)

            self.assertEqual(2, comparison["generated_count"])
            self.assertEqual(2, comparison["existing_count"])
            self.assertEqual(2, comparison["filename_overlap"])
            self.assertEqual([], comparison["missing_in_generated"])
            self.assertEqual([], comparison["extra_in_generated"])

    def test_compare_overlay_dirs_should_scope_to_selected_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            generated_dir = root / "generated"
            existing_dir = root / "existing"
            generated_dir.mkdir(parents=True, exist_ok=True)
            existing_dir.mkdir(parents=True, exist_ok=True)
            (generated_dir / "_index.md").write_text("# Generated\n", encoding="utf-8")
            (existing_dir / "_index.md").write_text("# Existing\n", encoding="utf-8")
            (existing_dir / "08-other.md").write_text("# Other\n", encoding="utf-8")

            comparison = support.compare_overlay_dirs(
                generated_dir,
                existing_dir,
                include_filenames={"_index.md"},
            )

            self.assertEqual(1, comparison["generated_count"])
            self.assertEqual(1, comparison["existing_count"])
            self.assertEqual(1, comparison["filename_overlap"])
            self.assertEqual([], comparison["missing_in_generated"])

    def test_prepare_page_runtime_state_should_keep_distinct_current_page_text_per_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            current_dir = root / "docs" / "architecture" / "overlays" / "PRD-TEMPLATE-V1" / "08"
            current_dir.mkdir(parents=True, exist_ok=True)
            (current_dir / "_index.md").write_text("# Index Page\n", encoding="utf-8")
            (current_dir / "ACCEPTANCE_CHECKLIST.md").write_text("# Checklist Page\n", encoding="utf-8")

            selected_pages = [
                {"filename": "_index.md", "page_kind": "index", "current_title": "Index", "headings": []},
                {
                    "filename": "ACCEPTANCE_CHECKLIST.md",
                    "page_kind": "acceptance-checklist",
                    "current_title": "Checklist",
                    "headings": [],
                },
            ]

            state = SCRIPT_MODULE._prepare_page_runtime_state(
                selected_pages=selected_pages,
                current_dir=current_dir,
                task_digest={"overlay_clusters": []},
            )

            self.assertEqual("# Index Page\n", state["_index.md"]["current_page_text"])
            self.assertEqual("# Checklist Page\n", state["ACCEPTANCE_CHECKLIST.md"]["current_page_text"])


if __name__ == "__main__":
    unittest.main()
