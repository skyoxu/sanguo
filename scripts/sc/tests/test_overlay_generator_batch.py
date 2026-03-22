import importlib.util
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

import _overlay_generator_batch as batchmod

SCRIPT_PATH = REPO_ROOT / "scripts" / "sc" / "llm_generate_overlays_batch.py"
SPEC = importlib.util.spec_from_file_location("llm_generate_overlays_batch_script", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
SCRIPT_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCRIPT_MODULE)


class OverlayGeneratorBatchTests(unittest.TestCase):
    def test_parser_should_accept_pages_and_batch_suffix(self) -> None:
        parser = SCRIPT_MODULE._build_parser()

        args = parser.parse_args(
            [
                "--prd",
                "prd_template.md",
                "--prd-docs",
                "PRD_TRACEABILITY_MATRIX.md,PRD_RULES_FREEZE.md,PRD_ACCEPTANCE_ASSERTIONS.md",
                "--pages",
                "_index.md,ACCEPTANCE_CHECKLIST.md",
                "--batch-suffix",
                "nightly-a",
            ]
        )

        self.assertEqual("_index.md,ACCEPTANCE_CHECKLIST.md", args.pages)
        self.assertEqual("nightly-a", args.batch_suffix)

    def test_build_page_run_suffix_should_include_batch_and_page_slug(self) -> None:
        suffix = batchmod.build_page_run_suffix("nightly-a", "08-rules-freeze-and-assertion-routing.md")

        self.assertEqual("nightly-a--08-rules-freeze-and-assertion-routing-md", suffix)

    def test_render_batch_report_markdown_should_include_table_rows(self) -> None:
        summary = {
            "status": "ok",
            "prd_id": "PRD-TEMPLATE-V1",
            "page_count": 2,
            "success_count": 2,
            "failure_count": 0,
            "results": [
                {
                    "page": "_index.md",
                    "child_status": "ok",
                    "failure_type": "",
                    "diff_status": "unchanged",
                    "similarity_ratio": 1.0,
                    "child_out_dir": "logs/ci/2026-03-20/run-a",
                },
                {
                    "page": "ACCEPTANCE_CHECKLIST.md",
                    "child_status": "ok",
                    "failure_type": "",
                    "diff_status": "modified",
                    "similarity_ratio": 0.93,
                    "child_out_dir": "logs/ci/2026-03-20/run-b",
                },
            ],
        }

        text = batchmod.render_batch_report_markdown(summary)

        self.assertIn("| Page | Child Status | Failure Type | Diff Status | Similarity | Output |", text)
        self.assertIn("| _index.md | ok |  | unchanged | 1.0000 | logs/ci/2026-03-20/run-a |", text)
        self.assertIn("| ACCEPTANCE_CHECKLIST.md | ok |  | modified | 0.9300 | logs/ci/2026-03-20/run-b |", text)

    def test_classify_child_failure_should_mark_timeout(self) -> None:
        result = batchmod.classify_child_failure(
            rc=1,
            child_status="fail",
            child_summary={"error": "codex_exec_failed", "rc": 124},
        )

        self.assertEqual("timeout", result["failure_type"])
        self.assertEqual("codex_exec_failed", result["child_error"])

    def test_classify_child_failure_should_mark_model_error(self) -> None:
        result = batchmod.classify_child_failure(
            rc=1,
            child_status="fail",
            child_summary={"error": "invalid_page_output", "detail": "bad json"},
        )

        self.assertEqual("model_error", result["failure_type"])
        self.assertEqual("invalid_page_output", result["child_error"])

    def test_classify_child_failure_should_mark_script_error(self) -> None:
        result = batchmod.classify_child_failure(
            rc=1,
            child_status="fail",
            child_summary={"error": "prd_not_found"},
        )

        self.assertEqual("script_error", result["failure_type"])
        self.assertEqual("prd_not_found", result["child_error"])


if __name__ == "__main__":
    unittest.main()
