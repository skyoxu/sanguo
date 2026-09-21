#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON_DIR = REPO_ROOT / "scripts" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

import build_source_ledger as ledger_mod
import chapter5_semantic_reconciliation as ch5
import chapter6_knowledge as chapter6_knowledge
import chapter6_route
import refresh_chapter_knowledge as refresh_mod
import run_chapter5_guarded as guarded_ch5


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class Chapter5SemanticReconciliationTests(unittest.TestCase):
    def _prepare_source(self, root: Path, text: str = "# Rules\n\nU1 route choice is irreversible.\n"):
        source = root / "docs/gdd/a.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(text, encoding="utf-8")
        manifest, ledger = ledger_mod.build_ledger(
            root, ["docs/gdd/a.md"], "init", explicit=True
        )
        manifest_path = root / ch5.DEFAULT_SOURCE_MANIFEST
        ledger_path = root / ch5.DEFAULT_SOURCE_LEDGER
        write_json(manifest_path, manifest)
        write_json(ledger_path, ledger)
        return manifest_path, ledger_path, ledger

    def _compile_snapshot(self, root: Path, *, statement: str, priority: str = "P1"):
        manifest_path, ledger_path, ledger = self._prepare_source(root)
        candidate_path = root / ch5.DEFAULT_EXTRACTION_CANDIDATE
        snapshot_path = root / ch5.DEFAULT_EXTRACTION_SNAPSHOT
        result = ch5.prepare_extraction_b(
            root,
            manifest_path=manifest_path,
            ledger_path=ledger_path,
            candidate_path=candidate_path,
            snapshot_path=snapshot_path,
        )
        self.assertEqual("review_required", result["status"])
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        target = None
        for row in candidate["block_results"]:
            if "irreversible" in row["raw_source"]:
                target = row
                row.update({
                    "review_status": "reviewed",
                    "delivery_potential": True,
                    "disposition": "",
                    "obligations": [{
                        "statement": statement,
                        "kind": "invariant",
                        "priority": priority,
                        "delivery_relevant": True,
                        "source_block_ids": [row["block_id"]],
                    }],
                })
            else:
                row.update({
                    "review_status": "reviewed",
                    "delivery_potential": False,
                    "disposition": "context",
                    "obligations": [],
                })
        self.assertIsNotNone(target)
        write_json(candidate_path, candidate)
        snapshot = ch5.compile_extraction_b(
            root,
            manifest_path=manifest_path,
            ledger_path=ledger_path,
            candidate_path=candidate_path,
            snapshot_path=snapshot_path,
        )
        self.assertEqual("complete", snapshot["status"])
        return manifest_path, ledger_path, ledger, snapshot

    def _write_semantics(self, root: Path, ledger: dict, *, include: bool = True):
        block = next(row for row in ledger["blocks"] if "irreversible" in row["raw_text"])
        requirements = []
        if include:
            requirements = [{
                "requirement_id": "INV-U1",
                "kind": "invariant",
                "statement": "U1 route choice is irreversible.",
                "source_block_ids": [block["block_id"]],
                "delivery_relevant": True,
                "status": "active",
                "priority": "P1",
                "non_task_sinks": [],
            }]
        payload = {
            "schema_version": "newrouge.semantic-requirements.v1",
            "source_revision": ledger["source_revision"],
            "source_manifest_sha256": ledger["source_manifest_sha256"],
            "source_accounting": [],
            "requirements": requirements,
        }
        path = root / ch5.DEFAULT_CH3_SEMANTICS
        write_json(path, payload)
        return path

    def _write_task(self, root: Path, *, semantic_refs=None, acceptance=None, depends_on=None, overlap=None, task_id: int = 1):
        semantic_refs = list(semantic_refs or [])
        acceptance = list(acceptance or [])
        overlay = root / "docs/architecture/overlays/PRD/08/_index.md"
        overlay.parent.mkdir(parents=True, exist_ok=True)
        overlay.write_text("# Route overlay\n", encoding="utf-8")
        contract = root / "Game.Core/Contracts/RouteEvents.cs"
        contract.parent.mkdir(parents=True, exist_ok=True)
        contract.write_text(
            'public static class RouteEvents { public const string Selected = "core.route.selected"; }\n',
            encoding="utf-8",
        )
        row = {
            "id": f"GM-{task_id:04d}",
            "taskmaster_id": task_id,
            "title": "Route choice",
            "status": "pending",
            "semantic_refs": semantic_refs,
            "acceptance": acceptance,
            "depends_on": list(depends_on or []),
            "implementation_overlap_candidates": list(overlap or []),
            "overlay_refs": ["docs/architecture/overlays/PRD/08/_index.md"],
            "contractRefs": ["core.route.selected"],
        }
        write_json(root / ".taskmaster/tasks/tasks_gameplay.json", [row])
        write_json(root / ".taskmaster/tasks/tasks_back.json", [])
        return row

    def _review_decisions(
        self,
        root: Path,
        *,
        requirement_id: str = "INV-U1",
        acceptance_index: int = 1,
        include_acceptance: bool = True,
        authority_status: str = "compatible",
        authority_rationale: str = "Contract is compatible with the reviewed semantic obligation.",
        match_status: str = "equivalent",
        match_rationale: str = "Independent semantic review confirms the obligation matches the Chapter 3 requirement.",
    ) -> dict:
        snapshot = json.loads((root / ch5.DEFAULT_EXTRACTION_SNAPSHOT).read_text(encoding="utf-8"))
        obligation_id = snapshot["semantic_inventory"][0]["obligation_id"]
        payload = {
            "match_decisions": [{
                "obligation_id": obligation_id,
                "chapter3_requirement_ids": [requirement_id],
                "status": match_status,
                "rationale": match_rationale,
            }],
            "authority_decisions": [{
                "authority_ref": "core.route.selected",
                "status": authority_status,
                "rationale": authority_rationale,
            }],
        }
        if include_acceptance:
            payload["acceptance_links"] = [{
                "acceptance_index": acceptance_index,
                "requirement_ids": [requirement_id],
                "test_refs": ["Game.Core.Tests/RouteTests.cs"],
            }]
        return payload

    def test_global_orphan_finds_missing_semantic_even_when_all_task_refs_are_removed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _manifest, _ledger_path, ledger, _snapshot = self._compile_snapshot(
                root, statement="U1 route choice is irreversible."
            )
            semantics_path = self._write_semantics(root, ledger, include=False)
            self._write_task(root, semantic_refs=[], acceptance=[])
            out = ch5.reconciliation_path_for_task(root, "1")
            readiness = ch5.readiness_path_for_task(root, "1")
            reconciliation, gate = ch5.reconcile(
                root,
                task_id="1",
                snapshot_path=root / ch5.DEFAULT_EXTRACTION_SNAPSHOT,
                semantics_path=semantics_path,
                decisions_path=None,
                out_path=out,
                readiness_path=readiness,
            )
            statuses = {row["status"] for row in reconciliation["findings"]}
            self.assertIn("missing_in_ch3", statuses)
            self.assertEqual(1, reconciliation["summary"]["orphan_delivery_semantic"])
            self.assertEqual("BLOCKED", gate["readiness"])

    def test_equivalent_wording_is_not_required_to_match_as_raw_string(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _manifest, _ledger_path, ledger, _snapshot = self._compile_snapshot(
                root, statement="Route choice cannot be reversed once selected."
            )
            semantics_path = self._write_semantics(root, ledger, include=True)
            self._write_task(
                root,
                semantic_refs=["INV-U1"],
                acceptance=["Route selection remains locked. Refs: Game.Core.Tests/RouteTests.cs"],
            )
            decisions = root / "decisions.json"
            payload = self._review_decisions(
                root,
                match_rationale="Independent semantic review confirms the paraphrase preserves the irreversible-route invariant.",
            )
            payload["acceptance_links"][0]["authority_refs"] = ["core.route.selected"]
            payload["allow_concerns"] = True
            write_json(decisions, payload)
            reconciliation, gate = ch5.reconcile(
                root,
                task_id="1",
                snapshot_path=root / ch5.DEFAULT_EXTRACTION_SNAPSHOT,
                semantics_path=semantics_path,
                decisions_path=decisions,
                out_path=ch5.reconciliation_path_for_task(root, "1"),
                readiness_path=ch5.readiness_path_for_task(root, "1"),
            )
            source_findings = [
                row for row in reconciliation["findings"]
                if row.get("finding_type") == "source_semantic"
                and row.get("chapter5_obligation")
            ]
            self.assertEqual("equivalent", source_findings[0]["status"])
            self.assertIn(gate["readiness"], {"READY", "CONCERNS"})
            self.assertTrue(gate["closure_allowed"])

    def test_lexical_similarity_never_auto_proves_equivalence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _manifest, _ledger_path, ledger, _snapshot = self._compile_snapshot(
                root, statement="U1 route choice is reversible after selection.", priority="P2"
            )
            semantics_path = self._write_semantics(root, ledger, include=True)
            self._write_task(
                root,
                semantic_refs=["INV-U1"],
                acceptance=["Route remains locked. Refs: Game.Core.Tests/RouteTests.cs"],
            )
            decisions = root / "decisions.json"
            payload = self._review_decisions(root)
            payload.pop("match_decisions")
            payload["allow_concerns"] = True
            write_json(decisions, payload)
            reconciliation, gate = ch5.reconcile(
                root,
                task_id="1",
                snapshot_path=root / ch5.DEFAULT_EXTRACTION_SNAPSHOT,
                semantics_path=semantics_path,
                decisions_path=decisions,
                out_path=ch5.reconciliation_path_for_task(root, "1"),
                readiness_path=ch5.readiness_path_for_task(root, "1"),
            )
            semantic = [
                row for row in reconciliation["findings"]
                if row.get("finding_type") == "source_semantic"
                and row.get("chapter5_obligation")
            ][0]
            self.assertGreater(semantic["similarity"], 0.25)
            self.assertEqual("needs_human_decision", semantic["status"])
            self.assertEqual("BLOCKED", gate["readiness"])
            self.assertFalse(gate["closure_allowed"])

    def test_authority_compatibility_requires_explicit_review_and_conflict_blocks(self) -> None:
        for authority_status in (None, "conflict"):
            with self.subTest(authority_status=authority_status), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _manifest, _ledger_path, ledger, _snapshot = self._compile_snapshot(
                    root, statement="U1 route choice is irreversible."
                )
                semantics_path = self._write_semantics(root, ledger, include=True)
                self._write_task(
                    root,
                    semantic_refs=["INV-U1"],
                    acceptance=["Route remains locked. Refs: Game.Core.Tests/RouteTests.cs"],
                )
                decisions = root / "decisions.json"
                payload = self._review_decisions(root)
                if authority_status is None:
                    payload.pop("authority_decisions")
                else:
                    payload["authority_decisions"][0]["status"] = "conflict"
                    payload["authority_decisions"][0]["rationale"] = "Contract permits reversal while the requirement forbids it."
                write_json(decisions, payload)
                reconciliation, gate = ch5.reconcile(
                    root,
                    task_id="1",
                    snapshot_path=root / ch5.DEFAULT_EXTRACTION_SNAPSHOT,
                    semantics_path=semantics_path,
                    decisions_path=decisions,
                    out_path=ch5.reconciliation_path_for_task(root, "1"),
                    readiness_path=ch5.readiness_path_for_task(root, "1"),
                )
                statuses = {row.get("status") for row in reconciliation["findings"]}
                self.assertEqual("BLOCKED", gate["readiness"])
                if authority_status is None:
                    self.assertIn("needs_human_decision", statuses)
                else:
                    self.assertIn("conflict_with_adr", statuses)

    def test_invented_chapter3_behavior_and_acceptance_scope_creep_block_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _manifest, _ledger_path, ledger, _snapshot = self._compile_snapshot(
                root, statement="U1 route choice is irreversible."
            )
            semantics_path = self._write_semantics(root, ledger, include=True)
            semantics = json.loads(semantics_path.read_text(encoding="utf-8"))
            block_id = semantics["requirements"][0]["source_block_ids"][0]
            semantics["requirements"].append({
                "requirement_id": "FR-INVENTED",
                "kind": "functional",
                "statement": "Grant a bonus reward not present in the source.",
                "source_block_ids": [block_id],
                "delivery_relevant": True,
                "status": "active",
                "priority": "P1",
                "non_task_sinks": [],
            })
            write_json(semantics_path, semantics)
            self._write_task(
                root,
                semantic_refs=["INV-U1"],
                acceptance=["Bonus reward appears. Refs: Game.Core.Tests/RouteTests.cs"],
            )
            decisions = root / "decisions.json"
            write_json(decisions, {
                "acceptance_links": [{
                    "acceptance_index": 1,
                    "requirement_ids": ["FR-INVENTED"],
                    "test_refs": ["Game.Core.Tests/RouteTests.cs"],
                }],
            })
            reconciliation, gate = ch5.reconcile(
                root,
                task_id="1",
                snapshot_path=root / ch5.DEFAULT_EXTRACTION_SNAPSHOT,
                semantics_path=semantics_path,
                decisions_path=decisions,
                out_path=ch5.reconciliation_path_for_task(root, "1"),
                readiness_path=ch5.readiness_path_for_task(root, "1"),
            )
            statuses = {row.get("status") for row in reconciliation["findings"]}
            self.assertIn("invented_in_ch3", statuses)
            self.assertIn("out_of_task_scope", statuses)
            self.assertEqual("BLOCKED", gate["readiness"])
            self.assertFalse(gate["closure_allowed"])

    def test_nonexistent_acceptance_authority_ref_blocks_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _manifest, _ledger_path, ledger, _snapshot = self._compile_snapshot(
                root, statement="U1 route choice is irreversible."
            )
            semantics_path = self._write_semantics(root, ledger, include=True)
            self._write_task(
                root,
                semantic_refs=["INV-U1"],
                acceptance=["Route remains locked. Refs: Game.Core.Tests/RouteTests.cs"],
            )
            decisions = root / "decisions.json"
            write_json(decisions, {
                "acceptance_links": [{
                    "acceptance_index": 1,
                    "requirement_ids": ["INV-U1"],
                    "authority_refs": ["ADR-99999"],
                    "test_refs": ["Game.Core.Tests/RouteTests.cs"],
                }],
            })
            reconciliation, gate = ch5.reconcile(
                root,
                task_id="1",
                snapshot_path=root / ch5.DEFAULT_EXTRACTION_SNAPSHOT,
                semantics_path=semantics_path,
                decisions_path=decisions,
                out_path=ch5.reconciliation_path_for_task(root, "1"),
                readiness_path=ch5.readiness_path_for_task(root, "1"),
            )
            self.assertTrue(any(
                row.get("status") == "untraceable_acceptance"
                and row.get("authority_ref") == "ADR-99999"
                for row in reconciliation["findings"]
            ))
            self.assertEqual("BLOCKED", gate["readiness"])

    def test_acceptance_declared_adr_enters_authority_review_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _manifest, _ledger_path, ledger, _snapshot = self._compile_snapshot(
                root, statement="U1 route choice is irreversible."
            )
            semantics_path = self._write_semantics(root, ledger, include=True)
            self._write_task(
                root,
                semantic_refs=["INV-U1"],
                acceptance=["Route remains locked. Refs: Game.Core.Tests/RouteTests.cs"],
            )
            adr = root / "docs/adr/ADR-1234-route.md"
            adr.parent.mkdir(parents=True, exist_ok=True)
            adr.write_text("# ADR-1234\n\nRoute choice is locked after selection.\n", encoding="utf-8")
            decisions = root / "decisions.json"
            payload = self._review_decisions(root)
            payload["acceptance_links"][0]["authority_refs"] = ["ADR-1234"]
            write_json(decisions, payload)

            reconciliation, gate = ch5.reconcile(
                root,
                task_id="1",
                snapshot_path=root / ch5.DEFAULT_EXTRACTION_SNAPSHOT,
                semantics_path=semantics_path,
                decisions_path=decisions,
                out_path=ch5.reconciliation_path_for_task(root, "1"),
                readiness_path=ch5.readiness_path_for_task(root, "1"),
            )
            self.assertEqual("BLOCKED", gate["readiness"])
            self.assertTrue(any(
                row.get("authority_ref") == "ADR-1234"
                and row.get("status") == "needs_human_decision"
                for row in reconciliation["findings"]
            ))

            payload["authority_decisions"].append({
                "authority_ref": "ADR-1234",
                "status": "compatible",
                "rationale": "ADR explicitly preserves the irreversible route-choice invariant.",
            })
            write_json(decisions, payload)
            reconciliation, gate = ch5.reconcile(
                root,
                task_id="1",
                snapshot_path=root / ch5.DEFAULT_EXTRACTION_SNAPSHOT,
                semantics_path=semantics_path,
                decisions_path=decisions,
                out_path=ch5.reconciliation_path_for_task(root, "1"),
                readiness_path=ch5.readiness_path_for_task(root, "1"),
            )
            self.assertTrue(gate["closure_allowed"])
            self.assertTrue(any(
                row.get("ref") == "ADR-1234"
                for row in reconciliation["authority_scope"]["adrs"]
            ))
            ok, _payload, reason = ch5.load_task_readiness(root, "1")
            self.assertTrue(ok, reason)

    def test_extraction_b_cache_reuses_same_identity_and_invalidates_on_source_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path, ledger_path, _ledger, snapshot = self._compile_snapshot(
                root, statement="U1 route choice is irreversible."
            )
            candidate_path = root / ch5.DEFAULT_EXTRACTION_CANDIDATE
            snapshot_path = root / ch5.DEFAULT_EXTRACTION_SNAPSHOT
            hit = ch5.prepare_extraction_b(
                root,
                manifest_path=manifest_path,
                ledger_path=ledger_path,
                candidate_path=candidate_path,
                snapshot_path=snapshot_path,
            )
            self.assertEqual("cache_hit", hit["status"])
            self.assertEqual(snapshot["extraction_b_snapshot_id"], hit["extraction_b_snapshot_id"])

            source = root / "docs/gdd/a.md"
            source.write_text("# Rules\n\nU1 route choice is irreversible after confirmation.\n", encoding="utf-8")
            manifest2, ledger2 = ledger_mod.build_ledger(
                root, ["docs/gdd/a.md"], "init", explicit=True
            )
            write_json(manifest_path, manifest2)
            write_json(ledger_path, ledger2)
            miss = ch5.prepare_extraction_b(
                root,
                manifest_path=manifest_path,
                ledger_path=ledger_path,
                candidate_path=candidate_path,
                snapshot_path=snapshot_path,
            )
            self.assertEqual("review_required", miss["status"])
            self.assertNotEqual(snapshot["extraction_b_snapshot_id"], miss["extraction_b_snapshot_id"])

    def test_dependency_and_overlap_decisions_are_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _manifest, _ledger_path, ledger, _snapshot = self._compile_snapshot(
                root, statement="U1 route choice is irreversible."
            )
            semantics_path = self._write_semantics(root, ledger, include=True)
            self._write_task(
                root,
                semantic_refs=["INV-U1"],
                acceptance=["Route selection remains locked. Refs: Game.Core.Tests/RouteTests.cs"],
                depends_on=[2],
                overlap=[3],
                task_id=5,
            )
            decisions = root / "decisions.json"
            payload = self._review_decisions(root)
            payload["dependency_decisions"] = [
                    {
                        "dependency_id": 2,
                        "action": "remove",
                        "dependency_reason": "Chapter 3 owner/layer adjacency only.",
                        "dependency_evidence": [],
                    },
                    {
                        "dependency_id": 4,
                        "action": "add",
                        "relation": "contract",
                        "dependency_reason": "Consumes route-selection contract.",
                        "dependency_evidence": ["core.route.selected"],
                    },
                ]
            payload["overlap_decisions"] = [{
                "other_task_id": 3,
                "status": "keep_separate",
                "rationale": "Shared scene surface but separate semantic ownership.",
            }]
            write_json(decisions, payload)
            reconciliation, gate = ch5.reconcile(
                root,
                task_id="5",
                snapshot_path=root / ch5.DEFAULT_EXTRACTION_SNAPSHOT,
                semantics_path=semantics_path,
                decisions_path=decisions,
                out_path=ch5.reconciliation_path_for_task(root, "5"),
                readiness_path=ch5.readiness_path_for_task(root, "5"),
            )
            actions = {(row["dependency_id"], row["action"]) for row in reconciliation["dependency_corrections"]}
            self.assertIn(("2", "remove"), actions)
            self.assertIn(("4", "add"), actions)
            self.assertEqual("keep_separate", reconciliation["overlap_reviews"][0]["status"])
            self.assertNotEqual("BLOCKED", gate["readiness"])

    def test_chapter5_knowledge_refresh_promotes_only_verified_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path, ledger_path, ledger, _snapshot = self._compile_snapshot(
                root, statement="U1 route choice is irreversible."
            )
            semantics_path = self._write_semantics(root, ledger, include=True)
            self._write_task(
                root,
                semantic_refs=["INV-U1"],
                acceptance=["Route selection remains locked. Refs: Game.Core.Tests/RouteTests.cs"],
            )
            decisions = root / "decisions.json"
            write_json(decisions, self._review_decisions(root))
            reconciliation_path = ch5.reconciliation_path_for_task(root, "1")
            readiness_path = ch5.readiness_path_for_task(root, "1")
            _reconciliation, gate = ch5.reconcile(
                root,
                task_id="1",
                snapshot_path=root / ch5.DEFAULT_EXTRACTION_SNAPSHOT,
                semantics_path=semantics_path,
                decisions_path=decisions,
                out_path=reconciliation_path,
                readiness_path=readiness_path,
            )
            self.assertEqual("READY", gate["readiness"])

            capabilities = root / "logs/ci/task-generation/capabilities.v1.json"
            edges = root / "logs/ci/task-generation/topology-edges.v1.json"
            candidates = root / "logs/ci/task-generation/task-candidates.enriched.json"
            write_json(capabilities, {
                "schema_version": "newrouge.capabilities.v1",
                "capabilities": [],
            })
            write_json(edges, {
                "schema_version": "newrouge.topology-edges.v1",
                "edges": [],
            })
            write_json(candidates, {"candidates": [{"id": "1", "semantic_refs": ["INV-U1"]}]})

            summary = refresh_mod.run(
                root,
                source="chapter5",
                trigger_run_id="ch5-test",
                refresh_local=True,
                write_planning=False,
                publish_if_eligible=False,
                triplet_status="unknown",
                source_manifest_path=manifest_path,
                ledger_path=ledger_path,
                semantics_path=semantics_path,
                capabilities_path=capabilities,
                edges_path=edges,
                candidates_path=candidates,
                report_path=root / "unused.json",
                reconciliation_path=reconciliation_path,
                readiness_path=readiness_path,
            )
            self.assertTrue(summary["closure_passed"])
            self.assertEqual("stable_refreshed", summary["local_refresh_status"])
            self.assertEqual(refresh_mod.CHAPTER5_STABLE_PATH.as_posix(), summary["stabilized_path"])
            stabilized = root / refresh_mod.CHAPTER5_STABLE_PATH
            self.assertTrue(stabilized.is_file())
            payload = json.loads(stabilized.read_text(encoding="utf-8"))
            self.assertEqual("READY", payload["chapter_run"]["readiness"])
            self.assertEqual("stabilized", payload["chapter_run"]["reconciliation_status"])
            self.assertEqual("stabilized", payload["summary"]["chapter5_reconciliation_status"])
            self.assertTrue(payload["reconciliation"]["summary"])
            first_bytes = stabilized.read_bytes()
            first_stable_hash = payload["chapter_run"]["stable_input_hash"]

            # Re-running reconciliation with identical guarded inputs may change
            # generated_at/reconciliation hash, but must keep the same stable input identity.
            ch5.reconcile(
                root,
                task_id="1",
                snapshot_path=root / ch5.DEFAULT_EXTRACTION_SNAPSHOT,
                semantics_path=semantics_path,
                decisions_path=decisions,
                out_path=reconciliation_path,
                readiness_path=readiness_path,
            )

            second = refresh_mod.run(
                root,
                source="chapter5",
                trigger_run_id="ch5-test-repeat",
                refresh_local=True,
                write_planning=False,
                publish_if_eligible=False,
                triplet_status="unknown",
                source_manifest_path=manifest_path,
                ledger_path=ledger_path,
                semantics_path=semantics_path,
                capabilities_path=capabilities,
                edges_path=edges,
                candidates_path=candidates,
                report_path=root / "unused.json",
                reconciliation_path=reconciliation_path,
                readiness_path=readiness_path,
            )
            self.assertTrue(second["closure_passed"])
            self.assertEqual("stable_reused", second["local_refresh_status"])
            self.assertEqual(first_bytes, stabilized.read_bytes())
            self.assertEqual(
                first_stable_hash,
                json.loads(stabilized.read_text(encoding="utf-8"))["chapter_run"]["stable_input_hash"],
            )


    def test_reconciliation_blocks_when_chapter4_authority_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _manifest, _ledger_path, ledger, _snapshot = self._compile_snapshot(
                root, statement="U1 route choice is irreversible."
            )
            semantics_path = self._write_semantics(root, ledger, include=True)
            self._write_task(
                root,
                semantic_refs=["INV-U1"],
                acceptance=["Route remains locked. Refs: Game.Core.Tests/RouteTests.cs"],
            )
            (root / "Game.Core/Contracts/RouteEvents.cs").unlink()
            decisions = root / "decisions.json"
            write_json(decisions, self._review_decisions(root))
            reconciliation, gate = ch5.reconcile(
                root,
                task_id="1",
                snapshot_path=root / ch5.DEFAULT_EXTRACTION_SNAPSHOT,
                semantics_path=semantics_path,
                decisions_path=decisions,
                out_path=ch5.reconciliation_path_for_task(root, "1"),
                readiness_path=ch5.readiness_path_for_task(root, "1"),
            )
            self.assertIn("contract_missing:core.route.selected", reconciliation["authority_scope_errors"])
            self.assertEqual("BLOCKED", gate["readiness"])

    def test_readiness_fingerprint_invalidates_semantics_task_and_authority_drift(self) -> None:
        mutations = ("semantics", "semantic_refs", "acceptance", "dependency", "overlay", "contract")
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                manifest_path, ledger_path, ledger, _snapshot = self._compile_snapshot(
                    root, statement="U1 route choice is irreversible."
                )
                semantics_path = self._write_semantics(root, ledger, include=True)
                self._write_task(
                    root,
                    semantic_refs=["INV-U1"],
                    acceptance=["Route remains locked. Refs: Game.Core.Tests/RouteTests.cs"],
                )
                decisions = root / "decisions.json"
                write_json(decisions, self._review_decisions(root))
                reconciliation_path = ch5.reconciliation_path_for_task(root, "1")
                readiness_path = ch5.readiness_path_for_task(root, "1")
                _reconciliation, gate = ch5.reconcile(
                    root,
                    task_id="1",
                    snapshot_path=root / ch5.DEFAULT_EXTRACTION_SNAPSHOT,
                    semantics_path=semantics_path,
                    decisions_path=decisions,
                    out_path=reconciliation_path,
                    readiness_path=readiness_path,
                )
                self.assertTrue(gate["closure_allowed"])
                ok, _payload, reason = ch5.load_task_readiness(root, "1")
                self.assertTrue(ok, reason)

                if mutation == "semantics":
                    semantics = json.loads(semantics_path.read_text(encoding="utf-8"))
                    semantics["requirements"][0]["statement"] = "U1 route choice may be reversed."
                    write_json(semantics_path, semantics)
                elif mutation in {"semantic_refs", "acceptance", "dependency"}:
                    tasks_path = root / ".taskmaster/tasks/tasks_gameplay.json"
                    tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
                    if mutation == "semantic_refs":
                        tasks[0]["semantic_refs"] = ["INV-OTHER"]
                    elif mutation == "acceptance":
                        tasks[0]["acceptance"] = ["Route may be changed. Refs: Game.Core.Tests/RouteTests.cs"]
                    else:
                        tasks[0]["depends_on"] = [7]
                    write_json(tasks_path, tasks)
                elif mutation == "overlay":
                    overlay = root / "docs/architecture/overlays/PRD/08/_index.md"
                    overlay.write_text("# Route overlay\n\nChanged architecture constraint.\n", encoding="utf-8")
                else:
                    contract = root / "Game.Core/Contracts/RouteEvents.cs"
                    contract.write_text(
                        'public static class RouteEvents { public const string Selected = "core.route.selected"; public const string Reversed = "core.route.reversed"; }\n',
                        encoding="utf-8",
                    )

                ok, _payload, reason = ch5.load_task_readiness(root, "1")
                self.assertFalse(ok)
                self.assertIn(
                    reason,
                    {
                        "chapter5_reconciliation_input_fingerprint_stale",
                        "chapter5_current_authority_scope_invalid",
                    },
                )

                capabilities = root / "logs/ci/task-generation/capabilities.v1.json"
                edges = root / "logs/ci/task-generation/topology-edges.v1.json"
                candidates = root / "logs/ci/task-generation/task-candidates.enriched.json"
                write_json(capabilities, {"schema_version": "newrouge.capabilities.v1", "capabilities": []})
                write_json(edges, {"schema_version": "newrouge.topology-edges.v1", "edges": []})
                write_json(candidates, {"candidates": [{"id": "1", "semantic_refs": ["INV-U1"]}]})
                summary = refresh_mod.run(
                    root,
                    source="chapter5",
                    trigger_run_id=f"stale-{mutation}",
                    refresh_local=True,
                    write_planning=False,
                    publish_if_eligible=False,
                    triplet_status="unknown",
                    source_manifest_path=manifest_path,
                    ledger_path=ledger_path,
                    semantics_path=semantics_path,
                    capabilities_path=capabilities,
                    edges_path=edges,
                    candidates_path=candidates,
                    report_path=root / "unused.json",
                    reconciliation_path=reconciliation_path,
                    readiness_path=readiness_path,
                )
                self.assertFalse(summary["closure_passed"])
                self.assertNotEqual("stable_refreshed", summary["local_refresh_status"])

    def test_readiness_fingerprint_invalidates_declared_adr_byte_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _manifest, _ledger_path, ledger, _snapshot = self._compile_snapshot(
                root, statement="U1 route choice is irreversible."
            )
            semantics_path = self._write_semantics(root, ledger, include=True)
            self._write_task(
                root,
                semantic_refs=["INV-U1"],
                acceptance=["Route remains locked. Refs: Game.Core.Tests/RouteTests.cs"],
            )
            adr = root / "docs/adr/ADR-1234-route.md"
            adr.parent.mkdir(parents=True, exist_ok=True)
            adr.write_text("# ADR-1234\n\nRoute choice remains locked.\n", encoding="utf-8")
            decisions = root / "decisions.json"
            payload = self._review_decisions(root)
            payload["acceptance_links"][0]["authority_refs"] = ["ADR-1234"]
            payload["authority_decisions"].append({
                "authority_ref": "ADR-1234",
                "status": "compatible",
                "rationale": "ADR preserves the irreversible route invariant.",
            })
            write_json(decisions, payload)
            ch5.reconcile(
                root,
                task_id="1",
                snapshot_path=root / ch5.DEFAULT_EXTRACTION_SNAPSHOT,
                semantics_path=semantics_path,
                decisions_path=decisions,
                out_path=ch5.reconciliation_path_for_task(root, "1"),
                readiness_path=ch5.readiness_path_for_task(root, "1"),
            )
            ok, _payload, reason = ch5.load_task_readiness(root, "1")
            self.assertTrue(ok, reason)
            adr.write_text("# ADR-1234\n\nRoute choice may be reversed.\n", encoding="utf-8")
            ok, _payload, reason = ch5.load_task_readiness(root, "1")
            self.assertFalse(ok)
            self.assertEqual("chapter5_reconciliation_input_fingerprint_stale", reason)

    def test_guarded_chapter5_failure_still_leaves_last_attempt(self) -> None:
        class Result:
            returncode = 7

        def runner(*_args, **_kwargs):
            return Result()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stable_path = root / refresh_mod.CHAPTER5_STABLE_PATH
            stable_path.parent.mkdir(parents=True, exist_ok=True)
            stable_path.write_text('{"sentinel":"prior-stable"}\n', encoding="utf-8")
            prior_stable = stable_path.read_bytes()
            rc, summary = guarded_ch5.run_guarded(
                root,
                trigger_run_id="ch5-interrupted",
                command=["fake-chapter5-child"],
                runner=runner,
            )
            self.assertEqual(7, rc)
            self.assertEqual("failed", summary["status"])
            attempt_path = root / refresh_mod.ATTEMPT_PATH
            self.assertTrue(attempt_path.is_file())
            attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
            self.assertEqual("ch5-interrupted", attempt["chapter_run"]["trigger_run_id"])
            self.assertEqual("failed", attempt["chapter_run"]["lifecycle_status"])
            self.assertFalse(attempt["chapter_run"]["closure_passed"])
            self.assertEqual(prior_stable, stable_path.read_bytes())
            self.assertEqual("producer_run_failed", summary["final_refresh"]["publication_reason"])

    def test_chapter6_readiness_becomes_stale_when_source_bytes_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _manifest, _ledger_path, ledger, _snapshot = self._compile_snapshot(
                root, statement="U1 route choice is irreversible."
            )
            semantics_path = self._write_semantics(root, ledger, include=True)
            self._write_task(
                root,
                semantic_refs=["INV-U1"],
                acceptance=["Route remains locked. Refs: Game.Core.Tests/RouteTests.cs"],
            )
            decisions = root / "decisions.json"
            write_json(decisions, self._review_decisions(root))
            ch5.reconcile(
                root,
                task_id="1",
                snapshot_path=root / ch5.DEFAULT_EXTRACTION_SNAPSHOT,
                semantics_path=semantics_path,
                decisions_path=decisions,
                out_path=ch5.reconciliation_path_for_task(root, "1"),
                readiness_path=ch5.readiness_path_for_task(root, "1"),
            )
            ok, _payload, reason = ch5.load_task_readiness(root, "1")
            self.assertTrue(ok, reason)

            (root / "docs/gdd/a.md").write_text(
                "# Rules\n\nU1 route choice can be reversed after confirmation.\n",
                encoding="utf-8",
            )
            ok, _payload, reason = ch5.load_task_readiness(root, "1")
            self.assertFalse(ok)
            self.assertEqual("chapter5_current_source_scope_invalid", reason)

            rc, route = chapter6_route.route_chapter6(repo_root=root, task_id="1")
            self.assertEqual(3, rc)
            self.assertEqual("chapter5_readiness", route["blocked_by"])
            self.assertEqual("chapter5_current_source_scope_invalid", route["latest_reason"])

    def test_chapter6_route_blocks_when_readiness_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rc, payload = chapter6_route.route_chapter6(
                repo_root=Path(tmp), task_id="1"
            )
            self.assertEqual(3, rc)
            self.assertEqual("chapter5_readiness", payload["blocked_by"])
            self.assertEqual("return_to_chapter5", payload["chapter6_next_action"])

    def test_chapter6_and_review_paths_do_not_embed_global_knowledge_mutators(self) -> None:
        forbidden = {
            "refresh-knowledge",
            "publish_knowledge_catalog.py",
            "project-health-scan",
            "generate-knowledge-links",
            "init-knowledge-catalog",
        }
        paths = [
            "scripts/python/run_single_task_chapter6_lane.py",
            "scripts/python/resume_task.py",
            "scripts/sc/run_review_pipeline.py",
            "scripts/sc/llm_review_needs_fix_fast.py",
            "scripts/python/chapter6_route.py",
            "scripts/python/chapter6_knowledge.py",
        ]
        for relative in paths:
            with self.subTest(path=relative):
                text = (REPO_ROOT / relative).read_text(encoding="utf-8")
                hits = sorted(token for token in forbidden if token in text)
                self.assertEqual([], hits, f"{relative} embeds forbidden global mutators: {hits}")

        lane_text = (REPO_ROOT / "scripts/python/run_single_task_chapter6_lane.py").read_text(encoding="utf-8")
        self.assertIn("--skip-project-health", lane_text)

    def test_chapter6_capture_never_mutates_global_knowledge_or_project_health(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            current = root / "knowledge/indexes/current.json"
            lkg = root / "knowledge/indexes/last-known-good.json"
            health = root / "logs/ci/project-health-knowledge/latest.json"
            links = root / "docs/knowledge/generated/task-resource-links.json"
            write_json(current, {"generation_id": "g1"})
            write_json(lkg, {"generation_id": "g0"})
            write_json(health, {"revision": "main", "scene_graph": {}})
            write_json(links, {"generated": []})
            before = {path: path.read_bytes() for path in (current, lkg, health, links)}

            result = chapter6_knowledge.run(root, "1")
            self.assertEqual("knowledge_captured", result["status"])
            self.assertEqual("not_performed", result["global_refresh"])
            self.assertTrue((root / "logs/ci/chapter6-knowledge/task-1/knowledge-capture-candidate.json").is_file())
            for path, data in before.items():
                self.assertEqual(data, path.read_bytes())

            rejected = chapter6_knowledge.run(root, "1", write_task_refs=True)
            self.assertEqual("knowledge_capture_failed", rejected["status"])
            self.assertEqual("chapter6_global_task_ref_write_forbidden", rejected["reason"])


if __name__ == "__main__":
    unittest.main()
