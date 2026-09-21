#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON_DIR = REPO_ROOT / "scripts" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

import attest_chapter3_triplet_baseline as triplet_attest_mod
import audit_task_candidate_coverage as coverage_mod
import build_source_ledger as ledger_mod
import dev_cli as dev_cli_mod
import enrich_task_candidates as enrich_mod
import normalize_task_intents as intents_mod
import project_semantics_from_sources as projection_mod
import run_chapter3_guarded as guarded_mod
import run_chapter3_regression_check as regression_mod
import refresh_chapter_knowledge as refresh_mod
import validate_semantic_conservation as conservation_mod
from _semantic_topology import load_workspace_topology


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class Chapter3SemanticConservationTests(unittest.TestCase):
    def test_triplet_attestation_binds_current_task_file_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tasks_dir = root / ".taskmaster/tasks"
            write_json(tasks_dir / "tasks.json", {"master": {"tasks": []}})
            write_json(tasks_dir / "tasks_back.json", [])
            write_json(tasks_dir / "tasks_gameplay.json", [])

            with patch.object(
                triplet_attest_mod,
                "run_check",
                side_effect=lambda _root, name, _args: {
                    "name": name,
                    "status": "passed",
                    "returncode": 0,
                },
            ), patch.object(triplet_attest_mod, "git_revision", return_value="a" * 40):
                payload = triplet_attest_mod.attest(root)

            self.assertEqual("passed", payload["status"])
            ok, reason = refresh_mod.verify_triplet_attestation(root, payload)
            self.assertTrue(ok, reason)

            write_json(tasks_dir / "tasks_back.json", [{"id": "changed"}])
            ok, reason = refresh_mod.verify_triplet_attestation(root, payload)
            self.assertFalse(ok)
            self.assertIn("triplet_file_hash_mismatch", reason)

    def test_full_ledger_keeps_chinese_and_long_blocks_before_filtering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gdd = root / "docs/gdd/game.md"
            gdd.parent.mkdir(parents=True)
            long_text = "长文本" * 800
            gdd.write_text(
                "# 商店规则\n\n"
                "商店不得升级卡牌，但可以移除诅咒。\n\n"
                "| 行为 | 规则 |\n| --- | --- |\n| Continue | 失败时必须阻断 |\n\n"
                + long_text + "\n",
                encoding="utf-8",
            )
            manifest, ledger = ledger_mod.build_ledger(
                root, ["docs/gdd/*.md"], "init", explicit=True
            )
            raw = "\n".join(str(row["raw_text"]) for row in ledger["blocks"])
            self.assertIn("商店不得升级卡牌", raw)
            self.assertIn("失败时必须阻断", raw)
            self.assertIn(long_text, raw)
            self.assertEqual(manifest["block_count"], len(ledger["blocks"]))
            self.assertTrue(any(row["block_type"] == "table_row" for row in ledger["blocks"]))
            self.assertTrue(any(row["requirement_like_hint"] for row in ledger["blocks"]))

    def test_json_ledger_preserves_exact_source_slice_and_precise_span(self) -> None:
        text = (
            "{\n"
            "  \"rule\": {\n"
            "    \"message\": \"必须保持  原始空格\",\n"
            "    \"items\": [1, 2]\n"
            "  },\n"
            "  \"plain\": \"值\"\n"
            "}\n"
        )
        source_sha = ledger_mod.sha256_text(text)
        blocks = ledger_mod.parse_json("docs/gdd/rules.json", source_sha, text)
        by_pointer = {row["json_pointer"]: row for row in blocks}

        rule = by_pointer["/rule"]
        expected = (
            "\"rule\": {\n"
            "    \"message\": \"必须保持  原始空格\",\n"
            "    \"items\": [1, 2]\n"
            "  }"
        )
        self.assertEqual(expected, rule["raw_text"])
        self.assertEqual((2, 5), (rule["line_start"], rule["line_end"]))
        self.assertEqual(
            expected,
            text[rule["source_char_start"]:rule["source_char_end_exclusive"]],
        )
        self.assertEqual(
            "sha256:" + ledger_mod.sha256_text(expected),
            rule["content_hash"],
        )

        plain = by_pointer["/plain"]
        self.assertEqual("\"plain\": \"值\"", plain["raw_text"])
        self.assertEqual((6, 6), (plain["line_start"], plain["line_end"]))
        self.assertEqual(
            plain["raw_text"],
            text[plain["source_char_start"]:plain["source_char_end_exclusive"]],
        )

        compact = '{"rule":{"message":"必须保持  原始空格","items":[1,2]},"plain":"值"}'
        compact_blocks = ledger_mod.parse_json(
            "docs/gdd/rules.json",
            ledger_mod.sha256_text(compact),
            compact,
        )
        compact_rule = next(
            row for row in compact_blocks if row["json_pointer"] == "/rule"
        )
        self.assertEqual(
            json.loads(text)["rule"],
            json.loads("{" + compact_rule["raw_text"] + "}")["rule"],
        )
        self.assertNotEqual(rule["raw_text"], compact_rule["raw_text"])
        self.assertEqual((1, 1), (compact_rule["line_start"], compact_rule["line_end"]))
        self.assertEqual(
            compact_rule["raw_text"],
            compact[
                compact_rule["source_char_start"]:
                compact_rule["source_char_end_exclusive"]
            ],
        )

    def test_chinese_normative_and_implicit_rules_enter_semantic_review_without_keyword_filtering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gdd = root / "docs/gdd/rules.md"
            gdd.parent.mkdir(parents=True)
            samples = [
                "玩家必须保留当前生命值。",
                "商店不得升级卡牌。",
                "奖励只能从当前 Act 池选择。",
                "牌组至少保留一张牌。",
                "事件不可跳过结算。",
                "系统允许移除诅咒。",
                "目标是在三回合内完成教学。",
                "禁止预览操作推进 RNG。",
            ]
            implicit = "升级为同一张卡的升级态。"
            gdd.write_text(
                "# 规则\n\n" + "\n\n".join([*samples, implicit]) + "\n",
                encoding="utf-8",
            )
            _manifest, ledger = ledger_mod.build_ledger(
                root, ["docs/gdd/rules.md"], "init", explicit=True
            )
            raw_blocks = {row["raw_text"]: row for row in ledger["blocks"]}
            for sample in samples:
                self.assertIn(sample, raw_blocks)
                self.assertTrue(raw_blocks[sample]["requirement_like_hint"])
            self.assertIn(implicit, raw_blocks)
            implicit_block = raw_blocks[implicit]
            self.assertFalse(implicit_block["requirement_like_hint"])

            batch_index, candidate = projection_mod.prepare(
                ledger, 40, root / "batches", max_chars=24000
            )
            for summary in candidate["batch_summaries"]:
                summary["output_accounted_count"] = summary["input_block_count"]
            for result in candidate["block_results"]:
                if result["block_id"] == implicit_block["block_id"]:
                    result.update({
                        "delivery_potential": True,
                        "disposition": "atomized",
                        "atoms": [{
                            "requirement_id": "FR-UPGRADE-FORM",
                            "kind": "functional",
                            "statement": implicit,
                            "source_block_ids": [implicit_block["block_id"]],
                            "delivery_relevant": True,
                        }],
                    })
                else:
                    result.update({
                        "delivery_potential": False,
                        "disposition": "context",
                        "atoms": [],
                    })

            semantics, _caps, _edges = projection_mod.compile_projection(
                ledger, batch_index, candidate
            )
            requirement = next(
                row for row in semantics["requirements"]
                if row["requirement_id"] == "FR-UPGRADE-FORM"
            )
            self.assertEqual(implicit, requirement["statement"])
            report, _ = conservation_mod.validate(
                root, ledger, semantics, "projection"
            )
            self.assertEqual("passed", report["status"])

    def test_default_source_discovery_includes_optional_bmad_gdd_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs_gdd = root / "docs/gdd/game.md"
            docs_gdd.parent.mkdir(parents=True)
            docs_gdd.write_text("Docs GDD rule.\n", encoding="utf-8")
            bmad_gdd = root / "_bmad-output/gdd.md"
            bmad_gdd.parent.mkdir(parents=True)
            bmad_gdd.write_text("BMAD GDD rule.\n", encoding="utf-8")
            args = type("Args", (), {
                "prd_path": [], "gdd_path": [], "epics_path": [],
                "stories_path": [], "source_glob": [],
            })()
            patterns, explicit = ledger_mod.collect_patterns(root, args)
            manifest, ledger = ledger_mod.build_ledger(
                root, patterns, "init", explicit=explicit
            )
            paths = {row["path"] for row in manifest["sources"]}
            self.assertIn("docs/gdd/game.md", paths)
            self.assertIn("_bmad-output/gdd.md", paths)
            raw = "\n".join(row["raw_text"] for row in ledger["blocks"])
            self.assertIn("BMAD GDD rule.", raw)

    def test_authoritative_source_invalid_utf8_is_fail_fast(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "docs/gdd/bad.md"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"valid-prefix\xffinvalid")
            with self.assertRaisesRegex(ValueError, "not valid UTF-8"):
                ledger_mod.build_ledger(
                    root, ["docs/gdd/bad.md"], "init", explicit=True
                )

    def test_declared_missing_source_is_fail_fast(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, "matched no supported files"):
                ledger_mod.build_ledger(root, ["docs/gdd/missing.md"], "init", explicit=True)

    def test_add_mode_reports_changed_and_unchanged_stable_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gdd = root / "docs/gdd/game.md"
            gdd.parent.mkdir(parents=True)
            gdd.write_text("# H\n\nA paragraph.\n\nB paragraph.\n", encoding="utf-8")
            _manifest, first = ledger_mod.build_ledger(root, ["docs/gdd/*.md"], "init", explicit=True)
            gdd.write_text("# H\n\nA paragraph changed.\n\nB paragraph.\n", encoding="utf-8")
            _manifest, second = ledger_mod.build_ledger(
                root, ["docs/gdd/*.md"], "add", explicit=True, previous_ledger=first
            )
            self.assertGreaterEqual(len(second["delta"]["changed"]), 1)
            self.assertGreaterEqual(len(second["delta"]["unchanged"]), 1)

    def test_add_mode_preserves_unchanged_ids_when_block_is_inserted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gdd = root / "docs/gdd/game.md"
            gdd.parent.mkdir(parents=True)
            gdd.write_text("# H\n\nA paragraph.\n\nB paragraph.\n", encoding="utf-8")
            _manifest, first = ledger_mod.build_ledger(
                root, ["docs/gdd/*.md"], "init", explicit=True
            )
            old_by_text = {
                row["raw_text"]: row["block_id"]
                for row in first["blocks"]
                if row["block_type"] == "paragraph"
            }
            gdd.write_text(
                "# H\n\nInserted paragraph.\n\nA paragraph.\n\nB paragraph.\n",
                encoding="utf-8",
            )
            _manifest, second = ledger_mod.build_ledger(
                root, ["docs/gdd/*.md"], "add", explicit=True, previous_ledger=first
            )
            new_by_text = {
                row["raw_text"]: row["block_id"]
                for row in second["blocks"]
                if row["block_type"] == "paragraph"
            }
            self.assertEqual(old_by_text["A paragraph."], new_by_text["A paragraph."])
            self.assertEqual(old_by_text["B paragraph."], new_by_text["B paragraph."])
            self.assertIn(new_by_text["A paragraph."], second["delta"]["unchanged"])
            self.assertIn(new_by_text["B paragraph."], second["delta"]["unchanged"])
            self.assertEqual(1, len(second["delta"]["added"]))
            self.assertEqual([], second["delta"]["removed"])

    def test_add_mode_reuses_only_hash_stable_reviewed_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gdd = root / "docs/gdd/game.md"
            gdd.parent.mkdir(parents=True)
            gdd.write_text("# H\n\nA paragraph.\n\nB paragraph.\n", encoding="utf-8")
            _manifest, first_ledger = ledger_mod.build_ledger(
                root, ["docs/gdd/*.md"], "init", explicit=True
            )
            _index, first_candidate = projection_mod.prepare(
                first_ledger, 40, root / "batches-first"
            )
            for row in first_candidate["block_results"]:
                row.update({
                    "atoms": [],
                    "disposition": "context",
                    "delivery_potential": False,
                    "review_status": "reviewed",
                })
            for summary in first_candidate["batch_summaries"]:
                summary["output_accounted_count"] = summary["input_block_count"]

            gdd.write_text(
                "# H\n\nInserted paragraph.\n\nA paragraph.\n\nB paragraph.\n",
                encoding="utf-8",
            )
            _manifest, second_ledger = ledger_mod.build_ledger(
                root, ["docs/gdd/*.md"], "add", explicit=True,
                previous_ledger=first_ledger,
            )
            index, second_candidate = projection_mod.prepare(
                second_ledger, 40, root / "batches-second",
                previous_candidate=first_candidate,
            )
            by_text = {
                block["raw_text"]: block["block_id"]
                for block in second_ledger["blocks"]
                if block["block_type"] == "paragraph"
            }
            results = {
                row["block_id"]: row for row in second_candidate["block_results"]
            }
            self.assertEqual(
                "reused_unchanged", results[by_text["A paragraph."]]["review_status"]
            )
            self.assertEqual(
                "reused_unchanged", results[by_text["B paragraph."]]["review_status"]
            )
            inserted = results[by_text["Inserted paragraph."]]
            self.assertEqual("review_required", inserted["review_status"])
            self.assertIsNone(inserted["delivery_potential"])
            self.assertIn(
                by_text["Inserted paragraph."],
                second_candidate["reuse_summary"]["review_required_blocks"],
            )
            self.assertEqual(
                len(second_candidate["reuse_summary"]["reused_blocks"]),
                sum(row["reused_accounted_count"] for row in second_candidate["batch_summaries"]),
            )
            self.assertEqual(
                index["source_block_count"],
                len(second_candidate["block_results"]),
            )

    def test_add_mode_cross_block_semantics_stale_when_any_source_block_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gdd = root / "docs/gdd/game.md"
            gdd.parent.mkdir(parents=True)
            gdd.write_text("# H\n\nA rule.\n\nB rule.\n", encoding="utf-8")
            _manifest, first_ledger = ledger_mod.build_ledger(
                root, ["docs/gdd/*.md"], "init", explicit=True
            )
            _index, first_candidate = projection_mod.prepare(
                first_ledger, 40, root / "batches-first"
            )
            paragraphs = [
                row for row in first_ledger["blocks"]
                if row["block_type"] == "paragraph"
            ]
            a_id, b_id = paragraphs[0]["block_id"], paragraphs[1]["block_id"]
            for row in first_candidate["block_results"]:
                if row["block_id"] == a_id:
                    row.update({
                        "atoms": [{
                            "kind": "FR",
                            "statement": "A and B form one rule.",
                            "source_block_ids": [a_id, b_id],
                        }],
                        "disposition": "",
                        "delivery_potential": True,
                        "review_status": "reviewed",
                    })
                else:
                    row.update({
                        "atoms": [],
                        "disposition": "context",
                        "delivery_potential": False,
                        "review_status": "reviewed",
                    })
            for summary in first_candidate["batch_summaries"]:
                summary["output_accounted_count"] = summary["input_block_count"]

            gdd.write_text("# H\n\nA rule.\n\nB rule changed.\n", encoding="utf-8")
            _manifest, second_ledger = ledger_mod.build_ledger(
                root, ["docs/gdd/*.md"], "add", explicit=True,
                previous_ledger=first_ledger,
            )
            _index, second_candidate = projection_mod.prepare(
                second_ledger, 40, root / "batches-second",
                previous_candidate=first_candidate,
            )
            result = next(
                row for row in second_candidate["block_results"]
                if row["block_id"] == a_id
            )
            self.assertEqual("review_required", result["review_status"])
            self.assertEqual([], result["atoms"])

    def test_projection_batches_account_for_every_source_block(self) -> None:
        ledger = {
            "source_revision": "source-set:test",
            "blocks": [
                {
                    "block_id": f"SB-{idx}",
                    "source_path": "docs/gdd/a.md",
                    "line_start": idx,
                    "line_end": idx,
                    "raw_text": f"rule {idx}",
                    "requirement_like_hint": idx % 2 == 0,
                }
                for idx in range(1, 8)
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            index, candidate = projection_mod.prepare(ledger, 3, Path(tmp))
        self.assertEqual(3, index["batch_count"])
        self.assertEqual(7, index["source_block_count"])
        self.assertEqual(7, len(candidate["block_results"]))
        self.assertEqual(
            {row["block_id"] for row in ledger["blocks"]},
            {row["block_id"] for row in candidate["block_results"]},
        )
        self.assertTrue(all(row["output_accounted_count"] == 0 for row in candidate["batch_summaries"]))
        self.assertTrue(all(row["disposition"] == "" for row in candidate["block_results"]))
        self.assertTrue(all(row["delivery_potential"] is None for row in candidate["block_results"]))

    def test_projection_batches_include_adjacent_context_without_transferring_ownership(self) -> None:
        ledger = {
            "source_revision": "source-set:test",
            "blocks": [
                {
                    "block_id": f"SB-{index}",
                    "source_path": "docs/gdd/a.md",
                    "heading_path": ["Rules"],
                    "line_start": index,
                    "line_end": index,
                    "raw_text": f"Rule {index}",
                    "content_hash": "sha256:" + str(index) * 64,
                }
                for index in range(1, 5)
            ],
        }
        index, batches = projection_mod.build_batches(
            ledger, max_blocks=2, max_chars=3000
        )
        self.assertEqual(2, index["batch_count"])
        first, second = batches
        self.assertEqual(["SB-1", "SB-2"], first["block_ids"])
        self.assertEqual(["SB-3"], first["context_after_block_ids"])
        self.assertNotIn("SB-3", first["block_ids"])
        self.assertEqual(["SB-3", "SB-4"], second["block_ids"])
        self.assertEqual(["SB-2"], second["context_before_block_ids"])
        self.assertNotIn("SB-2", second["block_ids"])
        self.assertLessEqual(first["input_char_count"], first["max_chars_per_batch"])
        self.assertLessEqual(second["input_char_count"], second["max_chars_per_batch"])

        cross_file = {
            "source_revision": "source-set:test",
            "blocks": [
                {**ledger["blocks"][0], "block_id": "SB-A", "source_path": "docs/gdd/a.md"},
                {**ledger["blocks"][1], "block_id": "SB-B", "source_path": "docs/gdd/b.md"},
            ],
        }
        _index, separated = projection_mod.build_batches(
            cross_file, max_blocks=1, max_chars=3000
        )
        self.assertEqual([], separated[0]["context_after_block_ids"])
        self.assertEqual([], separated[1]["context_before_block_ids"])

    def test_projection_merge_preserves_all_sources_for_duplicate_and_equivalent_atoms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = {
                "schema_version": "newrouge.source-blocks.v1",
                "source_revision": "source-set:test",
                "source_manifest_sha256": "sha256:" + "1" * 64,
                "blocks": [
                    {
                        "block_id": "SB-1", "source_path": "docs/gdd/a.md",
                        "content_hash": "sha256:" + "a" * 64,
                        "raw_text": "Shop cannot upgrade cards.",
                    },
                    {
                        "block_id": "SB-2", "source_path": "docs/gdd/a.md",
                        "content_hash": "sha256:" + "b" * 64,
                        "raw_text": "Shop cannot upgrade cards.",
                    },
                    {
                        "block_id": "SB-3", "source_path": "docs/gdd/a.md",
                        "content_hash": "sha256:" + "c" * 64,
                        "raw_text": "Shop upgrades are forbidden.",
                    },
                ],
            }
            batch_index, candidate = projection_mod.prepare(
                ledger, 1, root / "batches", max_chars=3000
            )
            by_block = {
                row["block_id"]: row for row in candidate["block_results"]
            }
            for row in candidate["batch_summaries"]:
                row["output_accounted_count"] = row["input_block_count"]

            by_block["SB-1"].update({
                "delivery_potential": True,
                "disposition": "atomized",
                "atoms": [{
                    "kind": "FR",
                    "statement": "Shop cannot upgrade cards.",
                    "source_block_ids": ["SB-1"],
                }],
            })
            by_block["SB-2"].update({
                "delivery_potential": True,
                "disposition": "atomized",
                "atoms": [{
                    "kind": "functional",
                    "statement": "  SHOP cannot   upgrade cards. ",
                    "source_block_ids": ["SB-2"],
                }],
            })
            by_block["SB-3"].update({
                "delivery_potential": True,
                "disposition": "atomized",
                "atoms": [{
                    "requirement_id": "FR-SHOP-EXPLICIT",
                    "kind": "functional",
                    "statement": "Shop upgrades are forbidden.",
                    "source_block_ids": ["SB-3"],
                }],
            })

            semantics, _caps, edges = projection_mod.compile_projection(
                ledger, batch_index, candidate
            )
            automatic = [
                row for row in semantics["requirements"]
                if row["requirement_id"] != "FR-SHOP-EXPLICIT"
            ]
            self.assertEqual(1, len(automatic))
            self.assertEqual(["SB-1", "SB-2"], automatic[0]["source_block_ids"])
            rid = automatic[0]["requirement_id"]
            accounting = {
                row["block_id"]: row["requirement_ids"]
                for row in semantics["source_accounting"]
            }
            self.assertEqual([rid], accounting["SB-1"])
            self.assertEqual([rid], accounting["SB-2"])
            self.assertTrue(all(
                any(
                    edge["source_type"] == "source_block"
                    and edge["source_id"] == block_id
                    and edge["target_type"] == "requirement"
                    and edge["target_id"] == rid
                    for edge in edges["edges"]
                )
                for block_id in ("SB-1", "SB-2")
            ))

            # Reuse one explicit id to merge semantically equivalent paraphrases.
            by_block["SB-1"]["atoms"][0]["requirement_id"] = "FR-MERGED"
            by_block["SB-2"]["atoms"][0] = {
                "requirement_id": "FR-MERGED",
                "kind": "functional",
                "statement": "The shop must never upgrade cards.",
                "source_block_ids": ["SB-2"],
            }
            semantics, _caps, _edges = projection_mod.compile_projection(
                ledger, batch_index, candidate
            )
            merged = next(
                row for row in semantics["requirements"]
                if row["requirement_id"] == "FR-MERGED"
            )
            self.assertEqual(["SB-1", "SB-2"], merged["source_block_ids"])
            self.assertIn(
                "The shop must never upgrade cards.",
                merged.get("equivalent_statements", []),
            )

    def test_projection_compile_rejects_duplicate_primary_batch_ownership(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = {
                "schema_version": "newrouge.source-blocks.v1",
                "source_revision": "source-set:test",
                "source_manifest_sha256": "sha256:" + "1" * 64,
                "blocks": [{
                    "block_id": "SB-1",
                    "source_path": "docs/gdd/a.md",
                    "content_hash": "sha256:" + "a" * 64,
                    "raw_text": "Rule.",
                }],
            }
            batch_index, candidate = projection_mod.prepare(
                ledger, 1, root / "batches", max_chars=3000
            )
            duplicate = dict(batch_index["batches"][0])
            duplicate["batch_id"] = "BATCH-9999"
            batch_index["batches"].append(duplicate)
            with self.assertRaisesRegex(ValueError, "duplicate primary batch ownership"):
                projection_mod.compile_projection(ledger, batch_index, candidate)

    def test_projection_canonicalizes_adr_owned_sink_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = {
                "schema_version": "newrouge.source-blocks.v1",
                "source_revision": "source-set:test",
                "source_manifest_sha256": "sha256:" + "1" * 64,
                "blocks": [{
                    "block_id": "SB-1",
                    "source_path": "docs/gdd/a.md",
                    "content_hash": "sha256:" + "a" * 64,
                    "raw_text": "Architecture owns this constraint.",
                }],
            }
            batch_index, candidate = projection_mod.prepare(
                ledger, 1, root / "batches", max_chars=3000
            )
            candidate["batch_summaries"][0]["output_accounted_count"] = 1
            result = candidate["block_results"][0]
            result.update({
                "delivery_potential": True,
                "disposition": "atomized",
                "atoms": [{
                    "requirement_id": "CONSTRAINT-ADR",
                    "kind": "constraint",
                    "statement": "Architecture owns this constraint.",
                    "source_block_ids": ["SB-1"],
                    "delivery_relevant": True,
                    "sink_policy": "adr_owned",
                    "non_task_sinks": [{
                        "type": "adr_owned",
                        "id": "ADR-0038",
                        "relation": "governed_by",
                    }],
                }],
            })
            semantics, _caps, edges = projection_mod.compile_projection(
                ledger, batch_index, candidate
            )
            requirement = semantics["requirements"][0]
            self.assertEqual("adr", requirement["non_task_sinks"][0]["type"])
            self.assertTrue(any(
                edge["target_type"] == "adr" and edge["target_id"] == "ADR-0038"
                for edge in edges["edges"]
            ))

    def test_projection_compile_rejects_unreviewed_blocks_and_requires_batch_accounting(self) -> None:
        ledger = {
            "source_revision": "source-set:test",
            "source_manifest_sha256": "sha256:" + "1" * 64,
            "blocks": [{
                "block_id": "SB-1",
                "source_path": "docs/gdd/a.md",
                "line_start": 1,
                "line_end": 1,
                "raw_text": "升级为同一张卡的升级态。",
                "content_hash": "sha256:" + "2" * 64,
                "source_sha256": "3" * 64,
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            index, candidate = projection_mod.prepare(ledger, 40, Path(tmp), 24000)
        with self.assertRaisesRegex(ValueError, "output_accounted_count"):
            projection_mod.compile_projection(ledger, index, candidate)

        candidate["batch_summaries"][0]["output_accounted_count"] = 1
        candidate["block_results"][0].update({
            "disposition": "context",
            "delivery_potential": False,
        })
        semantics, capabilities, _edges = projection_mod.compile_projection(ledger, index, candidate)
        self.assertEqual("context", semantics["source_accounting"][0]["disposition"])
        self.assertEqual([], capabilities["capabilities"])

    def test_projection_prepare_removes_stale_managed_batch_files(self) -> None:
        ledger = {
            "source_revision": "source-set:test",
            "source_manifest_sha256": "sha256:" + "1" * 64,
            "mode": "init",
            "blocks": [
                {
                    "block_id": "SB-1",
                    "source_path": "docs/gdd/a.md",
                    "line_start": 1,
                    "line_end": 1,
                    "block_type": "paragraph",
                    "content_hash": "sha256:" + "a" * 64,
                    "raw_text": "A",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            batch_dir = Path(tmp)
            (batch_dir / "batch-9999.json").write_text("{}", encoding="utf-8")
            (batch_dir / "keep.txt").write_text("keep", encoding="utf-8")
            projection_mod.prepare(ledger, 40, batch_dir)
            self.assertFalse((batch_dir / "batch-9999.json").exists())
            self.assertTrue((batch_dir / "batch-0001.json").is_file())
            self.assertTrue((batch_dir / "keep.txt").is_file())

    def test_projection_batch_budget_never_truncates_oversized_block(self) -> None:
        ledger = {
            "source_revision": "source-set:test",
            "blocks": [{
                "block_id": "SB-LONG",
                "source_path": "docs/gdd/a.md",
                "line_start": 1,
                "line_end": 1,
                "raw_text": "长" * 2000,
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "do not truncate it silently"):
                projection_mod.prepare(ledger, 40, Path(tmp), 1000)

    def test_projection_conservation_blocks_delivery_potential_unresolved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "docs/gdd/a.md"
            source.parent.mkdir(parents=True)
            source.write_text("商店不得升级卡牌。\n", encoding="utf-8")
            _manifest, ledger = ledger_mod.build_ledger(root, ["docs/gdd/a.md"], "init", explicit=True)
            block = ledger["blocks"][0]
            semantics = {
                "schema_version": "newrouge.semantic-requirements.v1",
                "source_revision": ledger["source_revision"],
                "source_manifest_sha256": ledger["source_manifest_sha256"],
                "source_accounting": [{
                    "block_id": block["block_id"],
                    "batch_id": "BATCH-0001",
                    "block_content_hash": block["content_hash"],
                    "requirement_ids": [],
                    "disposition": "unresolved",
                    "delivery_potential": True,
                    "decision": None,
                }],
                "requirements": [],
            }
            report, _edges = conservation_mod.validate(root, ledger, semantics, "projection")
            self.assertEqual("blocked", report["status"])
            self.assertEqual(1, report["blocking_counts"]["unresolved_delivery_potential"])

            semantics["source_accounting"][0]["decision"] = {
                "owner": "game-design",
                "reason": "Explicitly classified as context after review.",
                "resolved_disposition": "context",
            }
            report, _edges = conservation_mod.validate(root, ledger, semantics, "projection")
            self.assertEqual("passed", report["status"])

    def test_projection_conservation_blocks_unresolved_delivery_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "docs/gdd/a.md"
            source.parent.mkdir(parents=True)
            source.write_text("Rule.\n", encoding="utf-8")
            source_sha = ledger_mod.sha256_text(source.read_text(encoding="utf-8"))
            ledger = {
                "source_revision": "source-set:test",
                "source_manifest_sha256": "sha256:" + "1" * 64,
                "blocks": [{
                    "block_id": "SB-1",
                    "source_path": "docs/gdd/a.md",
                    "source_sha256": source_sha,
                    "content_hash": "sha256:" + "a" * 64,
                }],
            }
            semantics = {
                "source_revision": "source-set:test",
                "source_manifest_sha256": "sha256:" + "1" * 64,
                "source_accounting": [{
                    "block_id": "SB-1",
                    "block_content_hash": "sha256:" + "a" * 64,
                    "disposition": "atomized",
                    "delivery_potential": True,
                    "requirement_ids": ["FR-1"],
                }],
                "requirements": [{
                    "requirement_id": "FR-1",
                    "kind": "functional",
                    "statement": "Rule.",
                    "source_block_ids": ["SB-1"],
                    "delivery_relevant": True,
                    "sink_policy": "task_or_global_constraint",
                    "status": "unresolved",
                }],
            }
            checks = conservation_mod.projection_checks(root, ledger, semantics)
            self.assertIn("FR-1", checks["unresolved_delivery_potential"])
            self.assertIn("FR-1", checks["unresolved_delivery_requirements"])

            semantics["requirements"][0]["decision"] = {
                "owner": "design-owner",
                "reason": "Explicitly defer until milestone M2.",
                "resolved_disposition": "deferred",
            }
            checks = conservation_mod.projection_checks(root, ledger, semantics)
            self.assertNotIn("FR-1", checks["unresolved_delivery_potential"])

    def test_projection_compile_requires_source_manifest_binding_and_valid_status(self) -> None:
        ledger = {
            "source_revision": "source-set:test",
            "source_manifest_sha256": "sha256:" + "1" * 64,
            "blocks": [{
                "block_id": "SB-1",
                "source_path": "docs/gdd/a.md",
                "content_hash": "sha256:" + "a" * 64,
                "raw_text": "Rule.",
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            index, candidate = projection_mod.prepare(ledger, 1, Path(tmp), 3000)
        candidate["batch_summaries"][0]["output_accounted_count"] = 1
        result = candidate["block_results"][0]
        result.update({
            "delivery_potential": True,
            "disposition": "atomized",
            "atoms": [{
                "requirement_id": "FR-1",
                "kind": "functional",
                "statement": "Rule.",
                "source_block_ids": ["SB-1"],
                "delivery_relevant": True,
            }],
        })

        candidate.pop("source_manifest_sha256")
        with self.assertRaisesRegex(ValueError, "source_manifest_sha256"):
            projection_mod.compile_projection(ledger, index, candidate)

        candidate["source_manifest_sha256"] = ledger["source_manifest_sha256"]
        candidate["block_results"][0]["atoms"][0]["status"] = "actve"
        with self.assertRaisesRegex(ValueError, "unsupported requirement status"):
            projection_mod.compile_projection(ledger, index, candidate)

    def test_projection_blocks_stale_semantic_binding_and_duplicate_accounting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "docs/gdd/a.md"
            source.parent.mkdir(parents=True)
            source.write_text("规则。\n", encoding="utf-8")
            _manifest, ledger = ledger_mod.build_ledger(
                root, ["docs/gdd/a.md"], "init", explicit=True
            )
            block_id = ledger["blocks"][0]["block_id"]
            accounting = {
                "block_id": block_id,
                "batch_id": "BATCH-0001",
                "block_content_hash": ledger["blocks"][0]["content_hash"],
                "requirement_ids": [],
                "disposition": "context",
                "delivery_potential": False,
                "decision": None,
            }
            semantics = {
                "schema_version": "newrouge.semantic-requirements.v1",
                "source_revision": "source-set:stale",
                "source_manifest_sha256": "sha256:" + "0" * 64,
                "source_accounting": [accounting, dict(accounting)],
                "requirements": [],
            }
            report, _edges = conservation_mod.validate(
                root, ledger, semantics, "projection"
            )
            self.assertEqual("blocked", report["status"])
            self.assertEqual(2, report["blocking_counts"]["binding_mismatches"])
            self.assertEqual(1, report["blocking_counts"]["duplicate_accounting_blocks"])

    def test_projection_validation_blocks_invalid_status_and_accounting_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "docs/gdd/a.md"
            source.parent.mkdir(parents=True)
            source.write_text("Rule.\n", encoding="utf-8")
            _manifest, ledger = ledger_mod.build_ledger(
                root, ["docs/gdd/a.md"], "init", explicit=True
            )
            block = ledger["blocks"][0]
            semantics = {
                "source_revision": ledger["source_revision"],
                "source_manifest_sha256": ledger["source_manifest_sha256"],
                "source_accounting": [{
                    "block_id": block["block_id"],
                    "block_content_hash": block["content_hash"],
                    "disposition": "bogus",
                    "delivery_potential": True,
                    "requirement_ids": ["FR-MISSING"],
                }],
                "requirements": [{
                    "requirement_id": "FR-1",
                    "kind": "functional",
                    "statement": "Rule.",
                    "source_block_ids": [block["block_id"]],
                    "delivery_relevant": True,
                    "sink_policy": "task_or_global_constraint",
                    "status": "actve",
                }],
            }
            report, _edges = conservation_mod.validate(
                root, ledger, semantics, "projection"
            )
            self.assertEqual("blocked", report["status"])
            self.assertEqual(1, report["blocking_counts"]["invalid_semantics"])
            self.assertEqual(1, report["blocking_counts"]["invalid_source_accounting"])

    def test_missing_p1_waiver_never_bypasses_semantic_or_p0_blockers(self) -> None:
        semantic_blocked = {
            "coverage_model": "semantic-sink",
            "missing_blocking": [{
                "requirement_id": "FR-1",
                "priority": "P1",
                "coverage_status": "missing",
            }],
            "invalid_task_semantic_refs": [],
            "legacy_p0_p1_packaging": {
                "missing": [{
                    "requirement_id": "LEGACY-P1",
                    "priority": "P1",
                }]
            },
        }
        remaining = coverage_mod.blocking_after_p1_waiver(semantic_blocked)
        self.assertTrue(any(row["kind"] == "semantic_sink" for row in remaining))

        packaging_only_p1 = {
            "coverage_model": "semantic-sink",
            "missing_blocking": [],
            "invalid_task_semantic_refs": [],
            "legacy_p0_p1_packaging": {
                "missing": [{"requirement_id": "LEGACY-P1", "priority": "P1"}]
            },
        }
        self.assertEqual([], coverage_mod.blocking_after_p1_waiver(packaging_only_p1))

        packaging_p0 = {
            "coverage_model": "semantic-sink",
            "missing_blocking": [],
            "invalid_task_semantic_refs": [],
            "legacy_p0_p1_packaging": {
                "missing": [{"requirement_id": "LEGACY-P0", "priority": "P0"}]
            },
        }
        remaining = coverage_mod.blocking_after_p1_waiver(packaging_p0)
        self.assertEqual("legacy_packaging", remaining[0]["kind"])

    def test_coverage_blocks_stale_existing_task_mapping_until_reconciled(self) -> None:
        semantics = {
            "schema_version": "newrouge.semantic-requirements.v1",
            "source_accounting": [],
            "requirements": [{
                "requirement_id": "FR-NEW",
                "kind": "functional",
                "statement": "Current rule.",
                "source_block_ids": ["SB-1"],
                "delivery_relevant": True,
                "sink_policy": "task_or_global_constraint",
                "status": "active",
            }],
        }
        candidates = {"candidates": [{
            "id": "T1",
            "semantic_refs": ["FR-NEW"],
            "requirement_ids": ["FR-NEW"],
        }]}
        stale_task = [{"id": "OLD", "semantic_refs": ["FR-REMOVED"]}]
        report = coverage_mod.audit(semantics, candidates, None, stale_task)
        self.assertEqual("blocked", report["status"])
        self.assertEqual("OLD", report["stale_existing_task_mappings"][0]["task_id"])

        reconciled_task = [{"id": "T1", "semantic_refs": ["FR-REMOVED"]}]
        report = coverage_mod.audit(semantics, candidates, None, reconciled_task)
        self.assertEqual([], report["stale_existing_task_mappings"])
        self.assertEqual("ok", report["status"])

        semantics["requirements"].append({
            "requirement_id": "FR-OLD",
            "kind": "functional",
            "statement": "Superseded rule.",
            "source_block_ids": ["SB-OLD"],
            "delivery_relevant": True,
            "sink_policy": "task_or_global_constraint",
            "status": "superseded",
        })
        superseded_task = [{"id": "OLD2", "semantic_refs": ["FR-OLD"]}]
        report = coverage_mod.audit(semantics, candidates, None, superseded_task)
        self.assertEqual("blocked", report["status"])
        self.assertEqual(
            ["FR-OLD"],
            report["stale_existing_task_mappings"][0]["stale_requirement_ids"],
        )

    def test_closure_requires_delivery_sink_and_accepts_task_sink(self) -> None:
        semantics = {
            "requirements": [{
                "requirement_id": "FR-1",
                "kind": "functional",
                "statement": "Shop cannot upgrade cards.",
                "source_block_ids": ["SB-1"],
                "delivery_relevant": True,
                "sink_policy": "task_or_global_constraint",
                "status": "active",
            }]
        }
        closure, _edges = conservation_mod.closure_checks(semantics, {"candidates": []})
        self.assertEqual(1, len(closure["orphan_delivery_requirements"]))

        candidates = {"candidates": [{
            "id": "T1",
            "semantic_refs": ["FR-1"],
            "capability_refs": [],
            "complexity_score": 5,
        }]}
        closure, edges = conservation_mod.closure_checks(semantics, candidates)
        self.assertEqual([], closure["orphan_delivery_requirements"])
        self.assertTrue(any(edge["target_id"] == "T1" for edge in edges))

    def test_compact_intents_split_before_complexity_exceeds_seven(self) -> None:
        anchors = [
            {
                "requirement_id": f"FR-{index}",
                "source_path": "docs/gdd/a.md",
                "line": index,
                "kind": "functional",
                "priority": "P1",
                "text": f"Rule {index}",
                "refs": [],
                "source_block_ids": [f"SB-{index}"],
                "capability_id": "CAP-ONE",
                "capability_title": "One capability",
                "layer_hint": "core",
                "owner_hint": "gameplay",
                "semantic": True,
            }
            for index in range(1, 9)
        ]
        result = intents_mod.build_intents(
            {"schema": "chapter3.validated-semantics.v1", "anchors": anchors},
            "init", "TST", 8, "compact",
        )
        self.assertEqual(2, result["intent_count"])
        self.assertEqual([7, 1], [row["complexity_score"] for row in result["intents"]])
        covered = {
            rid
            for row in result["intents"]
            for rid in row["semantic_refs"]
        }
        self.assertEqual({f"FR-{index}" for index in range(1, 9)}, covered)
        self.assertTrue(all(row["complexity_score"] <= 7 for row in result["intents"]))

    def test_semantic_intent_keeps_capability_and_provisional_dependency(self) -> None:
        semantics = {
            "requirements": [
                {
                    "requirement_id": "FR-1",
                    "kind": "functional",
                    "statement": "Shop cannot upgrade cards.",
                    "source_block_ids": ["SB-1"],
                    "delivery_relevant": True,
                    "sink_policy": "task_or_global_constraint",
                    "status": "active",
                    "priority": "P1",
                },
                {
                    "requirement_id": "FR-2",
                    "kind": "functional",
                    "statement": "Curse can be removed.",
                    "source_block_ids": ["SB-2"],
                    "delivery_relevant": True,
                    "sink_policy": "task_or_global_constraint",
                    "status": "active",
                    "priority": "P1",
                },
            ]
        }
        blocks = {"blocks": [
            {"block_id": "SB-1", "source_path": "docs/gdd/a.md", "line_start": 1},
            {"block_id": "SB-2", "source_path": "docs/gdd/a.md", "line_start": 2},
        ]}
        capabilities = {"capabilities": [{
            "capability_id": "CAP-SHOP",
            "title": "Shop rules",
            "requirement_ids": ["FR-1", "FR-2"],
        }]}
        anchors = intents_mod.semantic_to_anchors(semantics, blocks, capabilities)
        result = intents_mod.build_intents(
            {"schema": "chapter3.validated-semantics.v1", "anchors": anchors},
            "init", "TST", 1, "compact",
        )
        self.assertEqual(2, result["intent_count"])
        self.assertTrue(all(row["capability_refs"] == ["CAP-SHOP"] for row in result["intents"]))
        self.assertTrue(all(row["semantic_refs"] for row in result["intents"]))
        self.assertTrue(any(row["depends_on"] for row in result["intents"]))
        self.assertTrue(all(row["dependency_status"] == "provisional" for row in result["intents"]))

    def test_semantic_intent_uses_chinese_heading_without_capability(self) -> None:
        semantics = {
            "requirements": [
                {
                    "requirement_id": "FR-COMBAT-1",
                    "kind": "functional",
                    "statement": "夜晚开始后敌人的刷新压力逐步提高。",
                    "source_block_ids": ["SB-C1"],
                    "delivery_relevant": True,
                    "sink_policy": "task_or_global_constraint",
                    "status": "active",
                    "priority": "P1",
                },
                {
                    "requirement_id": "FR-COMBAT-2",
                    "kind": "functional",
                    "statement": "玩家必须能感知当前刷新压力的变化。",
                    "source_block_ids": ["SB-C2"],
                    "delivery_relevant": True,
                    "sink_policy": "task_or_global_constraint",
                    "status": "active",
                    "priority": "P1",
                },
                {
                    "requirement_id": "FR-SHOP-1",
                    "kind": "functional",
                    "statement": "商店刷新商品时保持价格规则稳定。",
                    "source_block_ids": ["SB-S1"],
                    "delivery_relevant": True,
                    "sink_policy": "task_or_global_constraint",
                    "status": "active",
                    "priority": "P1",
                },
            ]
        }
        blocks = {"blocks": [
            {
                "block_id": "SB-C1",
                "source_path": "docs/gdd/game.md",
                "line_start": 10,
                "heading_path": ["战斗", "战斗节奏"],
            },
            {
                "block_id": "SB-C2",
                "source_path": "docs/gdd/game.md",
                "line_start": 11,
                "heading_path": ["战斗", "战斗节奏"],
            },
            {
                "block_id": "SB-S1",
                "source_path": "docs/gdd/game.md",
                "line_start": 30,
                "heading_path": ["商店", "商店规则"],
            },
        ]}
        anchors = intents_mod.semantic_to_anchors(
            semantics, blocks, {"capabilities": []}
        )
        result = intents_mod.build_intents(
            {"schema": "chapter3.validated-semantics.v1", "anchors": anchors},
            "init", "TST", 7, "compact",
        )
        self.assertEqual(2, result["intent_count"])
        self.assertEqual(
            {"实现战斗节奏", "实现商店规则"},
            {row["title"] for row in result["intents"]},
        )
        combat = next(row for row in result["intents"] if row["title"] == "实现战斗节奏")
        self.assertEqual(
            {"FR-COMBAT-1", "FR-COMBAT-2"},
            set(combat["semantic_refs"]),
        )
        self.assertEqual([], combat["capability_refs"])
        self.assertEqual(0, result["joint_capability_shadow"]["candidate_group_count"])

    def test_multi_capability_grouping_is_preserved_and_shadowed_advisory_only(self) -> None:
        semantics = {
            "requirements": [
                {
                    "requirement_id": "FR-1",
                    "kind": "functional",
                    "statement": "Reward choice must persist across resume.",
                    "source_block_ids": ["SB-1"],
                    "delivery_relevant": True,
                    "sink_policy": "task_or_global_constraint",
                    "status": "active",
                    "priority": "P1",
                },
                {
                    "requirement_id": "FR-2",
                    "kind": "functional",
                    "statement": "Reward presentation must expose deterministic choice state.",
                    "source_block_ids": ["SB-2"],
                    "delivery_relevant": True,
                    "sink_policy": "task_or_global_constraint",
                    "status": "active",
                    "priority": "P1",
                },
            ]
        }
        blocks = {"blocks": [
            {"block_id": "SB-1", "source_path": "docs/gdd/reward.md", "line_start": 1},
            {"block_id": "SB-2", "source_path": "docs/gdd/reward.md", "line_start": 2},
        ]}
        capabilities = {"capabilities": [
            {
                "capability_id": "CAP-UI",
                "title": "Reward presentation",
                "requirement_ids": ["FR-1", "FR-2"],
            },
            {
                "capability_id": "CAP-REWARD",
                "title": "Reward determinism",
                "requirement_ids": ["FR-1", "FR-2"],
            },
        ]}
        anchors = intents_mod.semantic_to_anchors(semantics, blocks, capabilities)
        self.assertTrue(all(
            row["capability_ids"] == ["CAP-REWARD", "CAP-UI"]
            for row in anchors
        ))
        self.assertTrue(all(row["capability_id"] == "CAP-UI" for row in anchors))

        result = intents_mod.build_intents(
            {"schema": "chapter3.validated-semantics.v1", "anchors": anchors},
            "init", "TST", 7, "compact",
        )
        self.assertEqual(1, result["intent_count"])
        self.assertEqual(
            ["CAP-REWARD", "CAP-UI"],
            result["intents"][0]["capability_refs"],
        )
        shadow = result["joint_capability_shadow"]
        self.assertEqual("advisory", shadow["mode"])
        self.assertFalse(shadow["affects_default_grouping"])
        self.assertEqual(1, shadow["candidate_group_count"])
        self.assertEqual(
            ["CAP-REWARD", "CAP-UI"],
            shadow["candidates"][0]["capability_refs"],
        )
        self.assertEqual(
            ["FR-1", "FR-2"],
            shadow["candidates"][0]["requirement_ids"],
        )
        self.assertTrue(shadow["candidates"][0]["advisory_only"])

    def test_enrichment_emits_file_overlap_as_advisory_signal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "Game.Core/combat_damage.cs"
            path.parent.mkdir(parents=True)
            path.write_text("class CombatDamage {}\n", encoding="utf-8")
            candidates = {"candidates": [
                {"id": "T1", "title": "Combat damage rule", "description": "combat damage", "labels": [], "requirement_ids": ["FR-1"]},
                {"id": "T2", "title": "Combat damage calculation", "description": "combat damage", "labels": [], "requirement_ids": ["FR-2"]},
            ]}
            result = enrich_mod.enrich(root, candidates)
            by_id = {row["id"]: row for row in result["candidates"]}
            self.assertEqual("medium", by_id["T1"]["file_churn_signal"])
            self.assertTrue(by_id["T1"]["implementation_overlap_candidates"])
            self.assertEqual("medium", by_id["T2"]["file_churn_signal"])

    def _refresh_fixture(self, root: Path, status: str) -> dict[str, Path]:
        source = root / "docs/gdd/a.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("Shop cannot upgrade cards.\n", encoding="utf-8")
        source_sha = ledger_mod.sha256_text(source.read_text(encoding="utf-8"))
        block = {
            "block_id": "SB-1",
            "source_path": "docs/gdd/a.md",
            "source_sha256": source_sha,
            "heading_path": [],
            "block_type": "paragraph",
            "ordinal": 1,
            "line_start": 1,
            "line_end": 1,
            "content_hash": "sha256:" + ledger_mod.sha256_text("Shop cannot upgrade cards."),
            "raw_text": "Shop cannot upgrade cards.",
        }
        paths = {
            "manifest": root / "logs/ci/task-generation/source-manifest.v1.json",
            "ledger": root / "logs/ci/task-generation/source-blocks.v1.json",
            "semantics": root / "logs/ci/task-generation/semantic-requirements.v1.json",
            "capabilities": root / "logs/ci/task-generation/capabilities.v1.json",
            "edges": root / "logs/ci/task-generation/topology-edges.v1.json",
            "candidates": root / "logs/ci/task-generation/task-candidates.enriched.json",
            "coverage": root / "logs/ci/task-generation/coverage-report.json",
            "triplet_attestation": (
                root / "logs/ci/task-generation/triplet-baseline-attestation.json"
            ),
            "report": root / "logs/ci/task-generation/semantic-conservation-report.json",
        }
        manifest = {
            "schema_version": "chapter3.source-manifest.v1",
            "source_revision": "source-set:test",
            "manifest_sha256": "sha256:" + "1" * 64,
            "repository_revision": "a" * 40,
        }
        ledger = {
            "schema_version": "newrouge.source-blocks.v1",
            "source_revision": "source-set:test",
            "source_manifest_sha256": manifest["manifest_sha256"],
            "blocks": [block],
        }
        semantics = {
            "schema_version": "newrouge.semantic-requirements.v1",
            "source_revision": "source-set:test",
            "source_manifest_sha256": manifest["manifest_sha256"],
            "source_accounting": [{
                "block_id": "SB-1",
                "batch_id": "BATCH-0001",
                "block_content_hash": block["content_hash"],
                "disposition": "atomized",
                "requirement_ids": ["FR-1"],
                "delivery_potential": True,
            }],
            "requirements": [{
                "requirement_id": "FR-1",
                "kind": "functional",
                "statement": "Shop cannot upgrade cards.",
                "source_block_ids": ["SB-1"],
                "delivery_relevant": True,
                "capability_ids": [],
                "sink_policy": "task_or_global_constraint",
                "status": "active",
            }],
        }
        candidates = {"candidates": []} if status == "blocked" else {"candidates": [{
            "id": "T1",
            "title": "Shop rule",
            "status": "pending",
            "semantic_refs": ["FR-1"],
            "capability_refs": [],
            "complexity_score": 1,
        }]}
        write_json(paths["manifest"], manifest)
        write_json(paths["ledger"], ledger)
        write_json(paths["semantics"], semantics)
        write_json(paths["capabilities"], {
            "schema_version": "newrouge.capabilities.v1",
            "capabilities": [],
        })
        write_json(paths["edges"], {
            "schema_version": "newrouge.topology-edges.v1",
            "edges": [],
        })
        write_json(paths["candidates"], candidates)
        tasks_dir = root / ".taskmaster/tasks"
        write_json(tasks_dir / "tasks.json", {"master": {"tasks": []}})
        write_json(tasks_dir / "tasks_back.json", [])
        write_json(tasks_dir / "tasks_gameplay.json", [])
        task_files = {}
        for value in refresh_mod.TRIPLET_TASK_FILES:
            task_path = root / value
            task_files[value] = {
                "sha256": "sha256:" + refresh_mod.sha256_bytes(task_path.read_bytes()),
                "size": task_path.stat().st_size,
            }
        write_json(paths["triplet_attestation"], {
            "schema_version": "chapter3.triplet-baseline-attestation.v1",
            "status": "passed",
            "task_files": task_files,
            "checks": [
                {"name": name, "status": "passed", "returncode": 0}
                for name in sorted(refresh_mod.TRIPLET_REQUIRED_CHECKS)
            ],
        })
        coverage = coverage_mod.audit_semantic(
            semantics, candidates, None, []
        )
        self.assertEqual("ok" if status == "passed" else "blocked", coverage["status"])
        write_json(paths["coverage"], coverage)
        report, task_edges = conservation_mod.validate(
            root, ledger, semantics, "closure", candidates
        )
        self.assertEqual(status, report["status"])
        write_json(paths["report"], report)
        if task_edges:
            write_json(paths["edges"], {
                "schema_version": "newrouge.topology-edges.v1",
                "edges": task_edges,
            })
        return paths

    def test_guarded_chapter3_run_refreshes_attempt_even_when_child_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            class Failed:
                returncode = 7

            rc, summary = guarded_mod.run_guarded(
                root,
                trigger_run_id="run-child-failed",
                command=["fake-chapter3-run"],
                runner=lambda *args, **kwargs: Failed(),
            )
            self.assertEqual(7, rc)
            self.assertEqual("failed", summary["status"])
            self.assertEqual(7, summary["child_returncode"])
            self.assertEqual(
                "attempt_refreshed_partial",
                summary["final_refresh"]["local_refresh_status"],
            )
            attempt_path = root / refresh_mod.ATTEMPT_PATH
            self.assertTrue(attempt_path.is_file())
            attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
            self.assertEqual("concern", attempt["status"])
            self.assertFalse(attempt["chapter_run"]["closure_passed"])
            self.assertFalse((root / refresh_mod.STABLE_PATH).exists())

    def test_guarded_chapter3_full_run_fails_closed_when_closure_cannot_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            class Passed:
                returncode = 0

            rc, summary = guarded_mod.run_guarded(
                root,
                trigger_run_id="run-child-passed-without-artifacts",
                command=["fake-full-chapter3-run"],
                triplet_status_on_success="passed",
                runner=lambda *args, **kwargs: Passed(),
            )
            self.assertEqual(2, rc)
            self.assertEqual("failed", summary["status"])
            self.assertFalse(summary["final_refresh"]["closure_passed"])
            self.assertEqual(
                "missing_refresh_inputs",
                summary["final_refresh"]["publication_reason"],
            )

    def test_chapter3_begin_run_writes_attempt_before_closure_artifacts_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            summary = refresh_mod.begin_run_attempt(
                root,
                source="chapter3",
                trigger_run_id="run-start-only",
            )
            self.assertEqual("attempt_refreshed_started", summary["local_refresh_status"])
            self.assertFalse(summary["closure_passed"])
            attempt_path = root / refresh_mod.ATTEMPT_PATH
            self.assertTrue(attempt_path.is_file())
            attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
            self.assertEqual("concern", attempt["status"])
            self.assertEqual("started", attempt["chapter_run"]["lifecycle_status"])
            self.assertFalse(attempt["chapter_run"]["closure_passed"])
            self.assertFalse((root / refresh_mod.STABLE_PATH).exists())

    def test_passed_closure_promotes_planning_topology_without_self_staling_revision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._refresh_fixture(root, "passed")
            summary = refresh_mod.run(
                root,
                source="chapter3",
                trigger_run_id="run-promote",
                refresh_local=True,
                write_planning=True,
                publish_if_eligible=False,
                triplet_status="passed",
                source_manifest_path=paths["manifest"],
                ledger_path=paths["ledger"],
                semantics_path=paths["semantics"],
                capabilities_path=paths["capabilities"],
                edges_path=paths["edges"],
                candidates_path=paths["candidates"],
                report_path=paths["report"],
            )
            self.assertTrue(summary["closure_passed"])
            self.assertEqual("written", summary["planning_artifact_status"])
            manifest_path = root / "docs/planning/semantic-topology/topology-manifest.v1.json"
            self.assertTrue(manifest_path.is_file())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertNotIn("repository_revision", manifest)
            self.assertEqual("a" * 40, manifest["source_repository_revision"])
            self.assertEqual("source-set:test", manifest["source_revision"])
            self.assertTrue(manifest["artifacts"])

            blocked_report = json.loads(paths["report"].read_text(encoding="utf-8"))
            blocked_report["status"] = "blocked"
            blocked_report["blocking_counts"]["orphan_delivery_requirements"] = 1
            write_json(paths["report"], blocked_report)
            summary = refresh_mod.run(
                root,
                source="chapter3",
                trigger_run_id="run-blocked-promote",
                refresh_local=True,
                write_planning=True,
                publish_if_eligible=False,
                triplet_status="blocked",
                source_manifest_path=paths["manifest"],
                ledger_path=paths["ledger"],
                semantics_path=paths["semantics"],
                capabilities_path=paths["capabilities"],
                edges_path=paths["edges"],
                candidates_path=paths["candidates"],
                report_path=paths["report"],
            )
            self.assertFalse(summary["closure_passed"])
            self.assertEqual("blocked_by_closure", summary["planning_artifact_status"])

    def test_chapter3_closure_requires_local_stable_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._refresh_fixture(root, "passed")
            summary = refresh_mod.run(
                root,
                source="chapter3",
                trigger_run_id="run-no-local-refresh",
                refresh_local=False,
                write_planning=False,
                publish_if_eligible=False,
                triplet_status="passed",
                source_manifest_path=paths["manifest"],
                ledger_path=paths["ledger"],
                semantics_path=paths["semantics"],
                capabilities_path=paths["capabilities"],
                edges_path=paths["edges"],
                candidates_path=paths["candidates"],
                report_path=paths["report"],
            )
            self.assertTrue(summary["semantic_triplet_closure_passed"])
            self.assertFalse(summary["closure_passed"])
            self.assertEqual("skipped", summary["local_refresh_status"])
            self.assertFalse((root / refresh_mod.STABLE_PATH).exists())

    def test_blocked_or_stale_task_coverage_cannot_promote_latest_successful(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._refresh_fixture(root, "passed")
            coverage = json.loads(paths["coverage"].read_text(encoding="utf-8"))
            coverage["status"] = "blocked"
            write_json(paths["coverage"], coverage)
            summary = refresh_mod.run(
                root,
                source="chapter3",
                trigger_run_id="run-coverage-blocked",
                refresh_local=True,
                write_planning=False,
                publish_if_eligible=False,
                triplet_status="passed",
                source_manifest_path=paths["manifest"],
                ledger_path=paths["ledger"],
                semantics_path=paths["semantics"],
                capabilities_path=paths["capabilities"],
                edges_path=paths["edges"],
                candidates_path=paths["candidates"],
                report_path=paths["report"],
            )
            self.assertFalse(summary["closure_passed"])
            self.assertEqual("blocked", summary["closure_evidence_status"])
            self.assertIn("coverage_status_mismatch", summary["closure_evidence_reason"])
            self.assertFalse((root / refresh_mod.STABLE_PATH).exists())

    def test_stale_triplet_attestation_cannot_promote_latest_successful(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._refresh_fixture(root, "passed")
            tasks_back = root / ".taskmaster/tasks/tasks_back.json"
            write_json(tasks_back, [{"id": "changed-after-attestation"}])
            summary = refresh_mod.run(
                root,
                source="chapter3",
                trigger_run_id="run-stale-triplet-attestation",
                refresh_local=True,
                write_planning=False,
                publish_if_eligible=False,
                triplet_status="passed",
                source_manifest_path=paths["manifest"],
                ledger_path=paths["ledger"],
                semantics_path=paths["semantics"],
                capabilities_path=paths["capabilities"],
                edges_path=paths["edges"],
                candidates_path=paths["candidates"],
                report_path=paths["report"],
            )
            self.assertFalse(summary["closure_passed"])
            self.assertEqual("blocked", summary["triplet_evidence_status"])
            self.assertIn(
                "triplet_file_hash_mismatch",
                summary["triplet_evidence_reason"],
            )
            self.assertFalse((root / refresh_mod.STABLE_PATH).exists())
            attempt = json.loads(
                (root / refresh_mod.ATTEMPT_PATH).read_text(encoding="utf-8")
            )
            self.assertEqual("concern", attempt["status"])
            self.assertFalse(attempt["chapter_run"]["closure_passed"])
            self.assertTrue(any(
                row.get("kind") == "triplet_baseline_evidence_invalid"
                for row in attempt.get("problems", [])
            ))

    def test_projection_stage_report_cannot_promote_latest_successful(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._refresh_fixture(root, "passed")
            report = json.loads(paths["report"].read_text(encoding="utf-8"))
            report["stage"] = "projection"
            write_json(paths["report"], report)
            summary = refresh_mod.run(
                root,
                source="chapter3",
                trigger_run_id="run-projection-spoof",
                refresh_local=True,
                write_planning=True,
                publish_if_eligible=False,
                triplet_status="passed",
                source_manifest_path=paths["manifest"],
                ledger_path=paths["ledger"],
                semantics_path=paths["semantics"],
                capabilities_path=paths["capabilities"],
                edges_path=paths["edges"],
                candidates_path=paths["candidates"],
                report_path=paths["report"],
            )
            self.assertFalse(summary["closure_passed"])
            self.assertEqual("blocked", summary["closure_evidence_status"])
            self.assertIn("closure_stage_required", summary["closure_evidence_reason"])
            self.assertFalse((root / refresh_mod.STABLE_PATH).exists())
            self.assertEqual("blocked_by_closure", summary["planning_artifact_status"])

    def test_planning_refresh_failure_restores_previous_stable_and_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._refresh_fixture(root, "passed")
            first = refresh_mod.run(
                root,
                source="chapter3",
                trigger_run_id="run-first",
                refresh_local=True,
                write_planning=True,
                publish_if_eligible=False,
                triplet_status="passed",
                source_manifest_path=paths["manifest"],
                ledger_path=paths["ledger"],
                semantics_path=paths["semantics"],
                capabilities_path=paths["capabilities"],
                edges_path=paths["edges"],
                candidates_path=paths["candidates"],
                report_path=paths["report"],
            )
            self.assertTrue(first["closure_passed"])
            stable_path = root / refresh_mod.STABLE_PATH
            stable_before = stable_path.read_bytes()
            manifest_path = root / "docs/planning/semantic-topology/topology-manifest.v1.json"
            manifest_before = manifest_path.read_bytes()

            real_copy = refresh_mod.shutil.copyfile
            calls = {"count": 0}

            def failing_copy(source, destination):
                calls["count"] += 1
                if calls["count"] == 2:
                    raise OSError("planning copy failure")
                return real_copy(source, destination)

            with patch.object(refresh_mod.shutil, "copyfile", side_effect=failing_copy):
                second = refresh_mod.run(
                    root,
                    source="chapter3",
                    trigger_run_id="run-second",
                    refresh_local=True,
                    write_planning=True,
                    publish_if_eligible=False,
                    triplet_status="passed",
                    source_manifest_path=paths["manifest"],
                    ledger_path=paths["ledger"],
                    semantics_path=paths["semantics"],
                    capabilities_path=paths["capabilities"],
                    edges_path=paths["edges"],
                    candidates_path=paths["candidates"],
                    report_path=paths["report"],
                )
            self.assertFalse(second["closure_passed"])
            self.assertEqual("planning_topology_refresh_failed", second["local_refresh_failure_family"])
            self.assertEqual(stable_before, stable_path.read_bytes())
            self.assertEqual(manifest_before, manifest_path.read_bytes())

    def test_regression_summary_separates_source_semantic_and_task_layers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out_dir = root / "regression"
            tasks_dir = root / ".taskmaster/tasks"
            tasks_dir.mkdir(parents=True)
            write_json(tasks_dir / "tasks.json", {"master": {"tasks": [{"id": "1", "title": "Baseline"}]}})
            write_json(tasks_dir / "tasks_back.json", [])
            write_json(tasks_dir / "tasks_gameplay.json", [])
            write_json(out_dir / "task-candidates.enriched.json", {"candidates": [{"id": "T1"}]})
            write_json(out_dir / "coverage-report.json", {
                "status": "ok",
                "coverage_model": "semantic-sink",
                "missing_blocking_count": 0,
            })
            write_json(out_dir / "task-intents.quality.json", {
                "status": "ok",
                "issue_count": 0,
                "issue_counts": {},
            })
            write_json(out_dir / "source-blocks.v1.json", {
                "blocks": [
                    {"block_id": "SB-1", "source_path": "docs/gdd/a.md"},
                    {"block_id": "SB-2", "source_path": "docs/gdd/a.md"},
                ],
                "parser_inventory": {"paragraph": 2},
                "delta": {"unchanged": ["SB-1"], "changed": ["SB-2"], "added": [], "removed": []},
            })
            write_json(out_dir / "requirements.index.json", {"anchors": [{"requirement_id": "LEGACY-1"}]})
            semantic_path = root / "semantic-requirements.v1.json"
            write_json(semantic_path, {
                "schema_version": "newrouge.semantic-requirements.v1",
                "source_revision": "source-set:test",
                "source_accounting": [
                    {"block_id": "SB-1", "disposition": "atomized", "delivery_potential": True},
                    {"block_id": "SB-2", "disposition": "context", "delivery_potential": False},
                ],
                "requirements": [{
                    "requirement_id": "FR-1",
                    "delivery_relevant": True,
                    "status": "active",
                }],
            })
            summary = regression_mod.build_summary(root, out_dir, semantic_path)
            self.assertEqual("chapter3.regression-check.v2", summary["schema"])
            self.assertEqual(2, summary["layers"]["source"]["source_block_count"])
            self.assertEqual("available", summary["layers"]["semantic"]["status"])
            self.assertEqual(1.0, summary["layers"]["semantic"]["source_accounting_coverage"])
            self.assertEqual(1, summary["layers"]["semantic"]["delivery_requirement_count"])
            self.assertEqual(1, summary["layers"]["task"]["candidate_count"])
            self.assertEqual(1, summary["shadow_compare"]["legacy_requirement_anchor_count"])

            summary = regression_mod.build_summary(root, out_dir, None)
            self.assertEqual("not_run", summary["layers"]["semantic"]["status"])

    def test_publication_eligibility_is_trusted_main_and_clean_only(self) -> None:
        root = Path(".")
        cases = [
            (["feature/test", "", "a" * 40, "a" * 40], False, "trusted_ref_required"),
            (["main", " M workflow.md", "a" * 40, "a" * 40], False, "dirty_worktree"),
            (["main", "", "a" * 40, "b" * 40], False, "head_not_local_main"),
            (["main", "", "a" * 40, "a" * 40], True, "eligible"),
        ]
        for responses, expected_ok, reason_prefix in cases:
            with self.subTest(reason=reason_prefix):
                with patch.object(refresh_mod, "git_result", side_effect=responses):
                    ok, reason = refresh_mod.publication_eligibility(root)
                self.assertEqual(expected_ok, ok)
                self.assertTrue(reason.startswith(reason_prefix), reason)

    def test_dev_cli_refresh_hook_fails_on_local_refresh_failure_but_not_deferred_publication(self) -> None:
        class Args:
            repo_root = "."
            source = "chapter3"
            begin_run = False
            trigger_run_id = "run-test"
            refresh_local = True
            write_planning_artifacts = False
            publish_if_eligible = True
            triplet_status = "passed"
            source_manifest = "logs/ci/task-generation/source-manifest.v1.json"
            ledger = "logs/ci/task-generation/source-blocks.v1.json"
            semantics = "logs/ci/task-generation/semantic-requirements.v1.json"
            capabilities = "logs/ci/task-generation/capabilities.v1.json"
            edges = "logs/ci/task-generation/topology-edges.v1.json"
            candidates = "logs/ci/task-generation/task-candidates.enriched.json"
            report = "logs/ci/task-generation/semantic-conservation-report.json"
            coverage = "logs/ci/task-generation/coverage-report.json"
            triplet_attestation = "logs/ci/task-generation/triplet-baseline-attestation.json"
            reconciliation = "logs/ci/chapter5/reconciliation/latest.json"
            readiness = "logs/ci/chapter5/readiness/latest.json"

        failed = {
            "local_refresh_status": "failed",
            "chapter_closure_status": "knowledge_refresh_failed",
            "publication_status": "deferred",
            "publication_reason": "knowledge_refresh_failed",
        }
        with patch.object(refresh_mod, "run", return_value=failed):
            self.assertEqual(2, dev_cli_mod.cmd_refresh_knowledge(Args()))

        deferred = {
            "local_refresh_status": "stable_refreshed",
            "chapter_closure_status": "passed",
            "publication_status": "deferred",
            "publication_reason": "dirty_worktree",
        }
        with patch.object(refresh_mod, "run", return_value=deferred):
            self.assertEqual(0, dev_cli_mod.cmd_refresh_knowledge(Args()))

        Args.begin_run = True
        Args.publish_if_eligible = False
        started = {
            "local_refresh_status": "attempt_refreshed_started",
            "chapter_closure_status": "concern",
            "publication_status": "deferred",
        }
        with patch.object(refresh_mod, "begin_run_attempt", return_value=started):
            self.assertEqual(0, dev_cli_mod.cmd_refresh_knowledge(Args()))

    def test_failed_closure_never_attempts_canonical_publication(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._refresh_fixture(root, "blocked")
            with patch.object(
                refresh_mod,
                "maybe_publish",
                side_effect=AssertionError("publication must not run before closure passes"),
            ):
                summary = refresh_mod.run(
                    root,
                    source="chapter3",
                    trigger_run_id="run-blocked-publish",
                    refresh_local=True,
                    write_planning=False,
                    publish_if_eligible=True,
                    triplet_status="blocked",
                    source_manifest_path=paths["manifest"],
                    ledger_path=paths["ledger"],
                    semantics_path=paths["semantics"],
                    capabilities_path=paths["capabilities"],
                    edges_path=paths["edges"],
                    candidates_path=paths["candidates"],
                    report_path=paths["report"],
                )
            self.assertFalse(summary["closure_passed"])
            self.assertEqual("deferred", summary["publication_status"])
            self.assertEqual("closure_not_passed", summary["publication_reason"])

    def test_attempt_refresh_failure_has_independent_failure_family(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._refresh_fixture(root, "blocked")
            real_write = refresh_mod.write_json

            def failing_write(path: Path, payload) -> None:
                if path == root / refresh_mod.ATTEMPT_PATH:
                    raise OSError("attempt disk failure")
                real_write(path, payload)

            with patch.object(refresh_mod, "write_json", side_effect=failing_write):
                summary = refresh_mod.run(
                    root,
                    source="chapter3",
                    trigger_run_id="run-attempt-write-fail",
                    refresh_local=True,
                    write_planning=False,
                    publish_if_eligible=True,
                    triplet_status="blocked",
                    source_manifest_path=paths["manifest"],
                    ledger_path=paths["ledger"],
                    semantics_path=paths["semantics"],
                    capabilities_path=paths["capabilities"],
                    edges_path=paths["edges"],
                    candidates_path=paths["candidates"],
                    report_path=paths["report"],
                )
            self.assertFalse(summary["closure_passed"])
            self.assertEqual("knowledge_refresh_failed", summary["chapter_closure_status"])
            self.assertEqual("failed", summary["local_refresh_status"])
            self.assertEqual("attempt_refresh_failed", summary["local_refresh_failure_family"])
            self.assertEqual("deferred", summary["publication_status"])
            self.assertEqual("knowledge_refresh_failed", summary["publication_reason"])
            self.assertFalse((root / refresh_mod.STABLE_PATH).exists())

    def test_stable_refresh_failure_blocks_chapter_closure_and_publication(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._refresh_fixture(root, "passed")
            real_write = refresh_mod.write_json

            def failing_write(path: Path, payload) -> None:
                if path == root / refresh_mod.STABLE_PATH:
                    raise OSError("stable disk failure")
                real_write(path, payload)

            with patch.object(refresh_mod, "write_json", side_effect=failing_write):
                summary = refresh_mod.run(
                    root,
                    source="chapter3",
                    trigger_run_id="run-stable-write-fail",
                    refresh_local=True,
                    write_planning=True,
                    publish_if_eligible=True,
                    triplet_status="passed",
                    source_manifest_path=paths["manifest"],
                    ledger_path=paths["ledger"],
                    semantics_path=paths["semantics"],
                    capabilities_path=paths["capabilities"],
                    edges_path=paths["edges"],
                    candidates_path=paths["candidates"],
                    report_path=paths["report"],
                )
            self.assertTrue(summary["semantic_triplet_closure_passed"])
            self.assertFalse(summary["closure_passed"])
            self.assertEqual("knowledge_refresh_failed", summary["chapter_closure_status"])
            self.assertEqual("stable_refresh_failed", summary["local_refresh_failure_family"])
            self.assertEqual("deferred", summary["publication_status"])
            self.assertFalse((root / refresh_mod.STABLE_PATH).exists())
            attempt = load_workspace_topology(root, "attempt")
            self.assertEqual("concern", attempt["status"])
            self.assertFalse(attempt["chapter_run"]["closure_passed"])
            self.assertEqual(
                "stable_refresh_failed",
                attempt["chapter_run"]["knowledge_refresh_failure_family"],
            )
            self.assertTrue(any(
                problem.get("kind") == "knowledge_refresh_failed"
                for problem in attempt.get("problems", [])
            ))
            self.assertFalse((root / "docs/planning/semantic-topology/topology-manifest.v1.json").exists())

    def test_stable_write_failure_preserves_previous_successful_topology(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._refresh_fixture(root, "passed")
            first = refresh_mod.run(
                root,
                source="chapter3",
                trigger_run_id="run-first-pass",
                refresh_local=True,
                write_planning=False,
                publish_if_eligible=False,
                triplet_status="passed",
                source_manifest_path=paths["manifest"],
                ledger_path=paths["ledger"],
                semantics_path=paths["semantics"],
                capabilities_path=paths["capabilities"],
                edges_path=paths["edges"],
                candidates_path=paths["candidates"],
                report_path=paths["report"],
            )
            self.assertTrue(first["closure_passed"])
            stable_path = root / refresh_mod.STABLE_PATH
            stable_before = stable_path.read_bytes()
            real_write = refresh_mod.write_json

            def failing_write(path: Path, payload) -> None:
                if path == stable_path:
                    raise OSError("stable replace failure")
                real_write(path, payload)

            with patch.object(refresh_mod, "write_json", side_effect=failing_write):
                second = refresh_mod.run(
                    root,
                    source="chapter3",
                    trigger_run_id="run-second-pass",
                    refresh_local=True,
                    write_planning=False,
                    publish_if_eligible=True,
                    triplet_status="passed",
                    source_manifest_path=paths["manifest"],
                    ledger_path=paths["ledger"],
                    semantics_path=paths["semantics"],
                    capabilities_path=paths["capabilities"],
                    edges_path=paths["edges"],
                    candidates_path=paths["candidates"],
                    report_path=paths["report"],
                )
            self.assertFalse(second["closure_passed"])
            self.assertEqual("stable_refresh_failed", second["local_refresh_failure_family"])
            self.assertEqual(stable_before, stable_path.read_bytes())
            stable = load_workspace_topology(root, "stable")
            attempt = load_workspace_topology(root, "attempt")
            self.assertEqual("run-first-pass", stable["identity"]["trigger_run_id"])
            self.assertEqual("run-second-pass", attempt["identity"]["trigger_run_id"])
            self.assertEqual("concern", attempt["status"])

    def test_failed_attempt_does_not_overwrite_latest_successful(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._refresh_fixture(root, "passed")
            summary = refresh_mod.run(
                root,
                source="chapter3",
                trigger_run_id="run-pass",
                refresh_local=True,
                write_planning=False,
                publish_if_eligible=False,
                triplet_status="passed",
                source_manifest_path=paths["manifest"],
                ledger_path=paths["ledger"],
                semantics_path=paths["semantics"],
                capabilities_path=paths["capabilities"],
                edges_path=paths["edges"],
                candidates_path=paths["candidates"],
                report_path=paths["report"],
            )
            self.assertTrue(summary["closure_passed"])
            stable_before = (root / refresh_mod.STABLE_PATH).read_text(encoding="utf-8")

            blocked_report = json.loads(paths["report"].read_text(encoding="utf-8"))
            blocked_report["status"] = "blocked"
            blocked_report["blocking_counts"]["orphan_delivery_requirements"] = 1
            write_json(paths["report"], blocked_report)
            summary = refresh_mod.run(
                root,
                source="chapter3",
                trigger_run_id="run-fail",
                refresh_local=True,
                write_planning=False,
                publish_if_eligible=False,
                triplet_status="blocked",
                source_manifest_path=paths["manifest"],
                ledger_path=paths["ledger"],
                semantics_path=paths["semantics"],
                capabilities_path=paths["capabilities"],
                edges_path=paths["edges"],
                candidates_path=paths["candidates"],
                report_path=paths["report"],
            )
            self.assertFalse(summary["closure_passed"])
            self.assertEqual(stable_before, (root / refresh_mod.STABLE_PATH).read_text(encoding="utf-8"))
            attempt = load_workspace_topology(root, "attempt")
            stable = load_workspace_topology(root, "stable")
            self.assertEqual("run-fail", attempt["identity"]["trigger_run_id"])
            self.assertEqual("run-pass", stable["identity"]["trigger_run_id"])
            self.assertFalse((root / "knowledge").exists())


if __name__ == "__main__":
    unittest.main()
