import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

import _overlay_generator_diff as diffmod


class OverlayGeneratorDiffTests(unittest.TestCase):
    def test_build_diff_summary_should_classify_added_removed_modified_and_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            generated_dir = root / "generated"
            existing_dir = root / "existing"
            generated_dir.mkdir(parents=True, exist_ok=True)
            existing_dir.mkdir(parents=True, exist_ok=True)

            (generated_dir / "_index.md").write_text("# Same\n", encoding="utf-8")
            (existing_dir / "_index.md").write_text("# Same\n", encoding="utf-8")

            (generated_dir / "08-a.md").write_text("# New\nA\nB\n", encoding="utf-8")
            (existing_dir / "08-a.md").write_text("# Old\nA\nC\n", encoding="utf-8")

            (generated_dir / "08-added.md").write_text("# Added\n", encoding="utf-8")
            (existing_dir / "08-removed.md").write_text("# Removed\n", encoding="utf-8")

            summary = diffmod.build_diff_summary(generated_dir, existing_dir)

            self.assertEqual(3, summary["generated_count"])
            self.assertEqual(3, summary["existing_count"])
            self.assertEqual(1, summary["unchanged_count"])
            self.assertEqual(1, summary["modified_count"])
            self.assertEqual(1, summary["added_count"])
            self.assertEqual(1, summary["removed_count"])

            by_name = {item["filename"]: item for item in summary["files"]}
            self.assertEqual("unchanged", by_name["_index.md"]["status"])
            self.assertEqual("modified", by_name["08-a.md"]["status"])
            self.assertEqual("added", by_name["08-added.md"]["status"])
            self.assertEqual("removed", by_name["08-removed.md"]["status"])
            self.assertIn("-# Old", by_name["08-a.md"]["diff_excerpt"])

    def test_build_diff_summary_should_scope_to_selected_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            generated_dir = root / "generated"
            existing_dir = root / "existing"
            generated_dir.mkdir(parents=True, exist_ok=True)
            existing_dir.mkdir(parents=True, exist_ok=True)

            (generated_dir / "_index.md").write_text("# New\n", encoding="utf-8")
            (existing_dir / "_index.md").write_text("# Old\n", encoding="utf-8")
            (existing_dir / "08-other.md").write_text("# Other\n", encoding="utf-8")

            summary = diffmod.build_diff_summary(
                generated_dir,
                existing_dir,
                include_filenames={"_index.md"},
            )

            self.assertEqual(1, summary["generated_count"])
            self.assertEqual(1, summary["existing_count"])
            self.assertEqual(1, summary["modified_count"])
            self.assertEqual(0, summary["removed_count"])

    def test_render_diff_summary_markdown_should_include_counts_and_file_rows(self) -> None:
        summary = {
            "generated_count": 2,
            "existing_count": 2,
            "unchanged_count": 1,
            "modified_count": 1,
            "added_count": 0,
            "removed_count": 0,
            "files": [
                {
                    "filename": "_index.md",
                    "status": "unchanged",
                    "similarity_ratio": 1.0,
                    "generated_chars": 10,
                    "existing_chars": 10,
                    "diff_excerpt": "",
                },
                {
                    "filename": "08-a.md",
                    "status": "modified",
                    "similarity_ratio": 0.7,
                    "generated_chars": 20,
                    "existing_chars": 18,
                    "diff_excerpt": "--- existing/08-a.md\n+++ generated/08-a.md\n@@\n-old\n+new",
                },
            ],
        }

        text = diffmod.render_diff_summary_markdown(summary)

        self.assertIn("# Overlay Diff Summary", text)
        self.assertIn("- modified_count: 1", text)
        self.assertIn("| 08-a.md | modified |", text)
        self.assertIn("```diff", text)


if __name__ == "__main__":
    unittest.main()
