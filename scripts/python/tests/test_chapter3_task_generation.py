#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON_DIR = REPO_ROOT / "scripts" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))


def _load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class Chapter3TaskGenerationTests(unittest.TestCase):
    def test_requirement_extraction_should_skip_reference_only_blocks(self) -> None:
        mod = _load_module("extract_requirement_anchors_for_noise_test", "scripts/python/extract_requirement_anchors.py")

        self.assertFalse(mod.is_requirement_like("- docs/gdd/ui-gdd-flow.md ADR-Refs:"))
        self.assertFalse(mod.is_requirement_like("- Game.Core.Tests/Tasks/Task1WindowsPlatformGateTests.cs"))
        self.assertFalse(mod.is_requirement_like("- T42 `Independent performance gates workflow`"))
        self.assertTrue(mod.is_requirement_like("- Startup smoke must verify all required autoloads load without startup errors."))

    def test_task_intents_should_split_large_source_groups_by_topic_and_size(self) -> None:
        mod = _load_module("normalize_task_intents_for_split_test", "scripts/python/normalize_task_intents.py")
        anchors = []
        for idx in range(1, 13):
            anchors.append(
                {
                    "requirement_id": f"REQ-COMBAT-{idx:04d}",
                    "source_path": "docs/gdd/ui-gdd-flow.md",
                    "line": idx,
                    "kind": "gdd",
                    "priority": "P1",
                    "text": f"Combat enemy attack damage targeting requirement {idx} must be implemented.",
                    "refs": [],
                }
            )
        for idx in range(1, 5):
            anchors.append(
                {
                    "requirement_id": f"REQ-UI-{idx:04d}",
                    "source_path": "docs/gdd/ui-gdd-flow.md",
                    "line": 100 + idx,
                    "kind": "gdd",
                    "priority": "P2",
                    "text": f"UI HUD surface display requirement {idx} should be implemented.",
                    "refs": [],
                }
            )

        result = mod.build_intents(
            {
                "schema": "task-generation.requirements-index.v1",
                "anchors": anchors,
            },
            mode="init",
            id_prefix="TST",
            max_anchors_per_intent=5,
            split_profile="compact",
        )

        self.assertEqual("task-generation.task-intents.v1", result["schema"])
        self.assertEqual(16, result["source_anchor_count"])
        self.assertEqual(4, result["intent_count"])
        self.assertEqual(
            sorted(anchor["requirement_id"] for anchor in anchors),
            sorted(rid for intent in result["intents"] for rid in intent["requirement_ids"]),
        )
        self.assertLessEqual(max(intent["covered_anchor_count"] for intent in result["intents"]), 5)
        self.assertIn("combat-loop", {intent["topic"] for intent in result["intents"]})
        self.assertIn("ui-hud", {intent["topic"] for intent in result["intents"]})
        self.assertTrue(any(intent["title"].startswith("Implement ") for intent in result["intents"]))
        self.assertTrue(any(intent["title"].startswith("Create ") for intent in result["intents"]))
        self.assertTrue(any("Red:" in " ".join(intent["test_strategy"]) for intent in result["intents"]))
        self.assertTrue(any(intent["depends_on"] for intent in result["intents"]))

    def test_task_intent_titles_should_deprioritize_traceability_noise(self) -> None:
        mod = _load_module("normalize_task_intents_for_title_noise_test", "scripts/python/normalize_task_intents.py")
        result = mod.build_intents(
            {
                "schema": "task-generation.requirements-index.v1",
                "anchors": [
                    {
                        "requirement_id": "REQ-NOISE-0001",
                        "source_path": "docs/gdd/a.md",
                        "line": 1,
                        "kind": "gdd",
                        "priority": "P2",
                        "text": "- ADR-0033 Test-Refs: Default save slot must gate Continue by valid metadata.",
                        "refs": [],
                    },
                    {
                        "requirement_id": "REQ-NOISE-0002",
                        "source_path": "docs/gdd/a.md",
                        "line": 2,
                        "kind": "gdd",
                        "priority": "P2",
                        "text": "- Default save slot must gate Continue by valid metadata.",
                        "refs": [],
                    },
                ],
            },
            mode="init",
            id_prefix="TST",
            max_anchors_per_intent=8,
        )

        title = result["intents"][0]["title"].lower()
        self.assertIn("save", title)
        self.assertNotIn("test", title)
        self.assertNotIn("adr", title)

    def test_task_intent_titles_should_fallback_to_source_name_not_generic_topic(self) -> None:
        mod = _load_module("normalize_task_intents_for_source_fallback_test", "scripts/python/normalize_task_intents.py")
        result = mod.build_intents(
            {
                "schema": "task-generation.requirements-index.v1",
                "anchors": [
                    {
                        "requirement_id": "REQ-SOURCE-0001",
                        "source_path": "docs/gdd/m1-playable-setup.md",
                        "line": 1,
                        "kind": "acceptance",
                        "priority": "P2",
                        "text": "- ADR-0033 Test-Refs: tests must pass.",
                        "refs": [],
                    },
                ],
            },
            mode="init",
            id_prefix="TST",
            max_anchors_per_intent=8,
        )

        title = result["intents"][0]["title"].lower()
        self.assertIn("playable", title)
        self.assertNotEqual("add test coverage for testing", title)

    def test_balanced_split_profile_should_split_gameplay_groups_more_finely_than_compact(self) -> None:
        mod = _load_module("normalize_task_intents_for_profile_test", "scripts/python/normalize_task_intents.py")
        anchors = [
            {
                "requirement_id": f"REQ-RUN-{idx:04d}",
                "source_path": "docs/gdd/run-loop.md",
                "line": idx,
                "kind": "gdd",
                "priority": "P2",
                "text": f"Run state turn cycle win lose terminal behavior requirement {idx} must be implemented.",
                "refs": [],
            }
            for idx in range(1, 9)
        ]

        compact = mod.build_intents(
            {"schema": "task-generation.requirements-index.v1", "anchors": anchors},
            mode="init",
            id_prefix="TST",
            max_anchors_per_intent=8,
            split_profile="compact",
        )
        balanced = mod.build_intents(
            {"schema": "task-generation.requirements-index.v1", "anchors": anchors},
            mode="init",
            id_prefix="TST",
            max_anchors_per_intent=8,
            split_profile="balanced",
        )

        self.assertEqual(1, compact["intent_count"])
        self.assertEqual(2, balanced["intent_count"])
        self.assertEqual(
            sorted(anchor["requirement_id"] for anchor in anchors),
            sorted(rid for intent in balanced["intents"] for rid in intent["requirement_ids"]),
        )

    def test_split_titles_should_put_part_number_before_shared_focus(self) -> None:
        mod = _load_module("normalize_task_intents_for_title_part_test", "scripts/python/normalize_task_intents.py")
        anchors = [
            {
                "requirement_id": f"REQ-GATE-{idx:04d}",
                "source_path": "docs/gdd/audit.md",
                "line": idx,
                "kind": "gdd",
                "priority": "P2",
                "text": f"Validation gate closure deterministic state requirement {idx} must be visible.",
                "refs": [],
            }
            for idx in range(1, 9)
        ]

        result = mod.build_intents(
            {"schema": "task-generation.requirements-index.v1", "anchors": anchors},
            mode="init",
            id_prefix="TST",
            max_anchors_per_intent=8,
            split_profile="balanced",
        )

        titles = [intent["title"] for intent in result["intents"]]
        self.assertTrue(any("part 1 validation" in title.lower() for title in titles))
        self.assertTrue(any("part 2 validation" in title.lower() for title in titles))

    def test_duplicate_titles_should_be_disambiguated_with_source_focus(self) -> None:
        mod = _load_module("normalize_task_intents_for_title_disambiguation_test", "scripts/python/normalize_task_intents.py")
        anchors = [
            {
                "requirement_id": "REQ-COPY-0001",
                "source_path": "docs/prd/narrative-style-guide.md",
                "line": 10,
                "kind": "prd",
                "priority": "P2",
                "text": "Screen specs must define visible copy.",
                "refs": [],
            },
            {
                "requirement_id": "REQ-COPY-0002",
                "source_path": "docs/prd/playtest-script.md",
                "line": 10,
                "kind": "prd",
                "priority": "P2",
                "text": "Screen specs must define visible copy.",
                "refs": [],
            },
        ]

        result = mod.build_intents(
            {"schema": "task-generation.requirements-index.v1", "anchors": anchors},
            mode="init",
            id_prefix="TST",
            max_anchors_per_intent=8,
            split_profile="balanced",
        )

        titles = [intent["title"] for intent in result["intents"]]
        self.assertEqual(len(titles), len(set(titles)))

    def test_duplicate_single_source_titles_should_get_line_qualifier(self) -> None:
        mod = _load_module("normalize_task_intents_for_line_disambiguation_test", "scripts/python/normalize_task_intents.py")
        anchors = [
            {
                "requirement_id": "REQ-LINE-0001",
                "source_path": "docs/prd/main-prd.md",
                "line": 13,
                "kind": "requirement",
                "priority": "P2",
                "text": "The product name must be visible.",
                "refs": [],
            },
            {
                "requirement_id": "REQ-LINE-0002",
                "source_path": "docs/prd/main-prd.md",
                "line": 147,
                "kind": "prd",
                "priority": "P2",
                "text": "The product name must be visible.",
                "refs": [],
            },
        ]

        result = mod.build_intents(
            {"schema": "task-generation.requirements-index.v1", "anchors": anchors},
            mode="init",
            id_prefix="TST",
            max_anchors_per_intent=8,
            split_profile="balanced",
        )

        titles = [intent["title"] for intent in result["intents"]]
        self.assertTrue(any("line 13" in title for title in titles))
        self.assertTrue(any("line 147" in title for title in titles))

    def test_intent_titles_should_collapse_repeated_adjacent_words(self) -> None:
        mod = _load_module("normalize_task_intents_for_repeated_word_test", "scripts/python/normalize_task_intents.py")

        self.assertEqual("Implement newrouge", mod.intent_title("newrouge-0001", "newrouge"))
        self.assertEqual("Document playable setup", mod.collapse_repeated_words("Document playable setup playable setup"))

    def test_candidate_generation_should_prefer_task_intents_when_present(self) -> None:
        mod = _load_module("generate_task_candidates_for_intent_test", "scripts/python/generate_task_candidates_from_sources.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "task-generation"
            out_dir.mkdir(parents=True)
            (out_dir / "requirements.index.json").write_text(
                json.dumps(
                    {
                        "schema": "task-generation.requirements-index.v1",
                        "anchors": [
                            {
                                "requirement_id": "REQ-OLD-0001",
                                "source_path": "docs/prd/a.md",
                                "line": 1,
                                "kind": "prd",
                                "priority": "P2",
                                "text": "Old source grouping should not be used.",
                                "refs": [],
                            }
                        ],
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (out_dir / "task-intents.normalized.json").write_text(
                json.dumps(
                    {
                        "schema": "task-generation.task-intents.v1",
                        "intents": [
                            {
                                "id": "INT-0001",
                                "title": "Implement combat loop",
                                "description": "Combat loop intent.",
                                "details": ["Do combat work."],
                                "priority": "P1",
                                "layer": "core",
                                "owner": "gameplay",
                                "labels": ["combat-loop"],
                                "requirement_ids": ["REQ-NEW-0001", "REQ-NEW-0002"],
                                "source_refs": ["docs/gdd/a.md:10", "docs/gdd/a.md:11"],
                                "covered_anchor_count": 2,
                            }
                        ],
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            rc = mod.main(["--repo-root", str(root), "--mode", "init", "--id-prefix", "GEN"])
            payload = json.loads((out_dir / "task-candidates.normalized.json").read_text(encoding="utf-8"))

        self.assertEqual(0, rc)
        self.assertEqual("task-generation.task-intents.v1", payload["source_schema"])
        self.assertEqual(1, payload["candidate_count"])
        self.assertEqual("INT-0001", payload["candidates"][0]["id"])
        self.assertEqual(["REQ-NEW-0001", "REQ-NEW-0002"], payload["candidates"][0]["requirement_ids"])

    def test_task_intent_quality_audit_should_report_generic_and_noisy_titles(self) -> None:
        mod = _load_module("audit_task_intents_quality_test", "scripts/python/audit_task_intents_quality.py")
        result = mod.audit(
            {
                "schema": "task-generation.task-intents.v1",
                "intents": [
                    {
                        "id": "INT-0001",
                        "title": "Add test coverage for testing",
                        "covered_anchor_count": 2,
                        "requirement_ids": ["REQ-1"],
                        "source_refs": ["docs/gdd/a.md:1"],
                    },
                    {
                        "id": "INT-0002",
                        "title": "Implement tasks.json refs",
                        "covered_anchor_count": 9,
                        "requirement_ids": [],
                        "source_refs": [],
                    },
                ],
            },
            max_anchors_per_intent=8,
        )

        self.assertEqual("review", result["status"])
        self.assertEqual(2, result["issue_count"])
        self.assertIn("generic_title", result["issue_counts"])
        self.assertIn("metadata_noise_in_title", result["issue_counts"])
        self.assertIn("too_many_anchors", result["issue_counts"])
        self.assertIn("missing_traceability", result["issue_counts"])

    def test_task_intent_quality_audit_should_treat_part_numbers_as_disambiguators(self) -> None:
        mod = _load_module("audit_task_intents_quality_part_key_test", "scripts/python/audit_task_intents_quality.py")
        result = mod.audit(
            {
                "schema": "task-generation.task-intents.v1",
                "intents": [
                    {
                        "id": "INT-0001",
                        "title": "Validate gdd part 1 closure deterministic draft state missing",
                        "covered_anchor_count": 4,
                        "requirement_ids": ["REQ-1"],
                        "source_refs": ["docs/gdd/a.md:1"],
                    },
                    {
                        "id": "INT-0002",
                        "title": "Validate gdd part 4 closure deterministic draft state missing",
                        "covered_anchor_count": 4,
                        "requirement_ids": ["REQ-2"],
                        "source_refs": ["docs/gdd/a.md:4"],
                    },
                ],
            },
            max_anchors_per_intent=8,
        )

        self.assertEqual("ok", result["status"])

    def test_regression_check_should_filter_back_only_and_post_ch3_tasks(self) -> None:
        mod = _load_module("run_chapter3_regression_check_test", "scripts/python/run_chapter3_regression_check.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            task_dir = root / ".taskmaster" / "tasks"
            task_dir.mkdir(parents=True)
            (task_dir / "tasks.json").write_text(
                json.dumps(
                    {
                        "master": {
                            "tasks": [
                                {"id": 1, "title": "Shared gameplay task", "labels": []},
                                {"id": 2, "title": "Back only task", "labels": []},
                                {"id": 3, "title": "Wire UI: Chapter 7 task", "labels": ["chapter7-ui"]},
                            ]
                        }
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (task_dir / "tasks_back.json").write_text(
                json.dumps(
                    [
                        {"id": "B-1", "taskmaster_id": 1, "title": "Shared gameplay task"},
                        {"id": "B-2", "taskmaster_id": 2, "title": "Back only task"},
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (task_dir / "tasks_gameplay.json").write_text(
                json.dumps([{"id": "G-1", "taskmaster_id": 1, "title": "Shared gameplay task"}]) + "\n",
                encoding="utf-8",
            )

            filtered = mod.filtered_tasks_json(root)

        self.assertEqual([1], [task["id"] for task in filtered])


if __name__ == "__main__":
    unittest.main()
