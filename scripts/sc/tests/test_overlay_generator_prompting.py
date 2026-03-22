import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

import _overlay_generator_prompting as prompting


class OverlayGeneratorPromptingTests(unittest.TestCase):
    def test_compact_companion_docs_should_preserve_paths_and_shrink_excerpts(self) -> None:
        companion_docs = [
            {
                "path": "PRD_TRACEABILITY_MATRIX.md",
                "excerpt": "A" * 5000,
            },
            {
                "path": "PRD_RULES_FREEZE.md",
                "excerpt": "B" * 5000,
            },
        ]

        compacted = prompting.compact_companion_docs(companion_docs, excerpt_chars=120)

        self.assertEqual(2, len(compacted))
        self.assertEqual("PRD_TRACEABILITY_MATRIX.md", compacted[0]["path"])
        self.assertLessEqual(len(compacted[0]["excerpt"]), 120)
        self.assertLessEqual(len(compacted[1]["excerpt"]), 120)

    def test_compact_task_digest_should_keep_clusters_and_reduce_noise(self) -> None:
        task_digest = {
            "prd_id": "PRD-TEMPLATE-V1",
            "master_tasks": [
                {
                    "id": "66",
                    "title": "Task 66",
                    "status": "pending",
                    "priority": "high",
                    "complexity": 8,
                    "overlay": "docs/architecture/overlays/PRD-TEMPLATE-V1/08/08-a.md",
                    "adr_refs": ["ADR-0004"],
                    "arch_refs": ["CH04"],
                    "subtasks_count": 3,
                }
            ],
            "tasks_back": [{"id": "SG-0001", "taskmaster_id": "66", "title": "Back 66"}],
            "tasks_gameplay": [{"id": "GM-0001", "taskmaster_id": "66", "title": "Gameplay 66"}],
            "overlay_clusters": [
                {
                    "overlay_path": "docs/architecture/overlays/PRD-TEMPLATE-V1/08/08-a.md",
                    "master_task_ids": ["66"],
                    "back_task_ids": ["66"],
                    "gameplay_task_ids": ["66"],
                    "titles": ["Task 66", "Back 66", "Gameplay 66"],
                }
            ],
        }

        compacted = prompting.compact_task_digest(task_digest)

        self.assertEqual("PRD-TEMPLATE-V1", compacted["prd_id"])
        self.assertIn("overlay_clusters", compacted)
        self.assertEqual(1, len(compacted["overlay_clusters"]))
        self.assertNotIn("tasks_back", compacted)
        self.assertNotIn("tasks_gameplay", compacted)

    def test_build_overlay_prompt_should_stay_within_budget_for_large_inputs(self) -> None:
        profile = [
            {
                "filename": f"08-page-{index:02d}.md",
                "page_kind": "feature",
                "current_title": f"Page {index}",
                "headings": [f"Heading {index}-1", f"Heading {index}-2"],
                "path": f"docs/architecture/overlays/PRD-TEMPLATE-V1/08/08-page-{index:02d}.md",
            }
            for index in range(25)
        ]
        companion_docs = [
            {"path": f"doc-{index}.md", "excerpt": "X" * 8000}
            for index in range(4)
        ]
        task_digest = {
            "prd_id": "PRD-TEMPLATE-V1",
            "master_tasks": [
                {
                    "id": str(index),
                    "title": f"Task {index}",
                    "status": "pending",
                    "priority": "high",
                    "complexity": 8,
                    "overlay": profile[min(index, 24)]["path"],
                    "adr_refs": ["ADR-0004"],
                    "arch_refs": ["CH04"],
                    "subtasks_count": 3,
                }
                for index in range(1, 40)
            ],
            "overlay_clusters": [
                {
                    "overlay_path": item["path"],
                    "master_task_ids": [str(idx)],
                    "back_task_ids": [str(idx)],
                    "gameplay_task_ids": [str(idx)],
                    "titles": [f"Task {idx}"],
                }
                for idx, item in enumerate(profile, start=1)
            ],
        }

        prompt = prompting.build_overlay_prompt(
            prd_path=Path("prd_template.md"),
            prd_text="P" * 40000,
            prd_id="PRD-TEMPLATE-V1",
            companion_docs=companion_docs,
            task_digest=task_digest,
            profile=profile,
            profile_locked=True,
        )

        self.assertLessEqual(len(prompt), 45000)

    def test_build_overlay_page_prompt_should_include_current_page_excerpt(self) -> None:
        page = {
            "filename": "08-t52-turn-window-and-event-ordering.md",
            "page_kind": "feature",
            "current_title": "Turn Window",
            "headings": ["Scope", "Task Binding"],
            "path": "docs/architecture/overlays/PRD-TEMPLATE-V1/08/08-t52-turn-window-and-event-ordering.md",
        }
        prompt = prompting.build_overlay_page_prompt(
            prd_path=Path("prd_template.md"),
            prd_text="Primary PRD body",
            prd_id="PRD-TEMPLATE-V1",
            companion_docs=[
                {"path": "PRD_RULES_FREEZE.md", "excerpt": "Freeze body"},
            ],
            page=page,
            page_context={
                "overlay_path": page["path"],
                "master_task_ids": ["52"],
                "back_task_ids": ["52"],
                "gameplay_task_ids": ["52"],
                "titles": ["Turn ordering"],
            },
            current_page_text="# Existing Page\n\n## Scope\n\nOld body\n",
        )

        self.assertIn("Target overlay page: 08-t52-turn-window-and-event-ordering.md", prompt)
        self.assertIn("Current page excerpt:", prompt)
        self.assertIn("# Existing Page", prompt)

    def test_parse_and_validate_page_should_require_expected_filename(self) -> None:
        raw_output = """
        {
          "filename": "08-t52-turn-window-and-event-ordering.md",
          "page_kind": "feature",
          "title": "Turn Window",
          "purpose": "Describe turn ordering",
          "adr_refs": ["ADR-0004"],
          "arch_refs": ["CH04"],
          "test_refs": ["scripts/python/quality_gates.py"],
          "task_ids": ["52"],
          "sections": [
            {"heading": "Scope", "bullets": ["One"]},
            {"heading": "Task Binding", "bullets": ["Two"]}
          ]
        }
        """

        page = prompting.parse_and_validate_page(
            raw_output=raw_output,
            expected_filename="08-t52-turn-window-and-event-ordering.md",
            expected_page_kind="feature",
        )

        self.assertEqual("08-t52-turn-window-and-event-ordering.md", page["filename"])
        self.assertEqual("feature", page["page_kind"])

    def test_build_overlay_page_patch_prompt_should_request_patch_object(self) -> None:
        page = {
            "filename": "_index.md",
            "page_kind": "index",
            "current_title": "Index",
            "headings": ["Directory Role"],
            "path": "docs/architecture/overlays/PRD-TEMPLATE-V1/08/_index.md",
        }
        prompt = prompting.build_overlay_page_patch_prompt(
            prd_path=Path("prd_template.md"),
            prd_text="Primary PRD body",
            prd_id="PRD-TEMPLATE-V1",
            companion_docs=[{"path": "PRD_TRACEABILITY_MATRIX.md", "excerpt": "Trace"}],
            page=page,
            page_context={"titles": ["Index task"]},
            current_page_text="# Existing Index\n",
        )

        self.assertIn('"patch"', prompt)
        self.assertIn("minimal structured patch", prompt)
        self.assertIn("Current page excerpt:", prompt)

    def test_parse_and_validate_page_patch_should_extract_patch_payload(self) -> None:
        raw_output = """
        {
          "filename": "_index.md",
          "patch": {
            "title": "Updated Index",
            "purpose": "Keep current structure with refreshed routing.",
            "adr_refs": ["ADR-0004", "ADR-0005"],
            "arch_refs": ["CH04", "CH07"],
            "test_refs": ["scripts/python/validate_task_overlays.py"],
            "task_ids": ["66"],
            "sections": [
              {"heading": "Directory Role", "bullets": ["One"]},
              {"heading": "Document Groups", "bullets": ["Two"]}
            ]
          }
        }
        """

        patch_payload = prompting.parse_and_validate_page_patch(
            raw_output=raw_output,
            expected_filename="_index.md",
        )

        self.assertEqual("Updated Index", patch_payload["title"])
        self.assertEqual(["ADR-0004", "ADR-0005"], patch_payload["adr_refs"])

    def test_run_codex_exec_should_create_output_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_last_message = Path(tmp_dir) / "nested" / "page.output.json"

            class FakeCompletedProcess:
                def __init__(self) -> None:
                    self.returncode = 0
                    self.stdout = "ok"

            with (
                patch.object(prompting.shutil, "which", return_value="C:/fake/codex.cmd"),
                patch.object(prompting.subprocess, "run", return_value=FakeCompletedProcess()),
            ):
                rc, trace_out, cmd = prompting.run_codex_exec(
                    repo_root=Path(tmp_dir),
                    prompt="{}",
                    out_last_message=out_last_message,
                    timeout_sec=30,
                )

            self.assertEqual(0, rc)
            self.assertEqual("ok", trace_out)
            self.assertTrue(out_last_message.parent.exists())
            self.assertIn(str(out_last_message), cmd)


if __name__ == "__main__":
    unittest.main()
