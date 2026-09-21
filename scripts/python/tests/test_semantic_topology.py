from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.python._knowledge_catalog_builder import build_layers
from scripts.python._knowledge_locator_core import locate
from scripts.python._semantic_topology import (
    TOPOLOGY_ARTIFACTS,
    WORKSPACE_TOPOLOGY_STABLE,
    WORKSPACE_TOPOLOGY_STABILIZED,
    attach_scene_design_trace,
    load_topology_from_snapshot,
    load_workspace_topology,
)


class FakeSnapshot:
    authority_ref = "refs/heads/main"

    def __init__(self, docs, commit="a" * 40):
        self.docs = {
            path: value if isinstance(value, str) else json.dumps(value)
            for path, value in docs.items()
        }
        self.paths = tuple(sorted(self.docs))
        self.commit = commit

    def read_text(self, path):
        return self.docs[path]

    def digest(self, path):
        return hashlib.sha256(self.docs[path].encode("utf-8")).hexdigest()


def valid_docs(revision="a" * 40):
    source_text = "Requirement text\n"
    source_sha = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    docs = {
        "docs/gdd/a.md": source_text,
        TOPOLOGY_ARTIFACTS["source_blocks"]: {"schema_version": "newrouge.source-blocks.v1", "blocks": [
            {"block_id": "SB-1", "source_path": "docs/gdd/a.md",
             "line_start": 1, "line_end": 1, "content_hash": "sha256:" + ("1" * 64),
             "source_sha256": source_sha}
        ]},
        TOPOLOGY_ARTIFACTS["requirements"]: {"schema_version": "newrouge.semantic-requirements.v1", "requirements": [
            {"requirement_id": "FR-1", "kind": "functional", "statement": "Requirement text",
             "source_block_ids": ["SB-1"], "delivery_relevant": True, "status": "active",
             "sink_policy": "task_or_global_constraint", "capability_ids": ["CAP-1"]}
        ]},
        TOPOLOGY_ARTIFACTS["capabilities"]: {"schema_version": "newrouge.capabilities.v1", "capabilities": [
            {"capability_id": "CAP-1", "title": "Test capability", "requirement_ids": ["FR-1"]}
        ]},
        TOPOLOGY_ARTIFACTS["edges"]: {"schema_version": "newrouge.topology-edges.v1", "edges": [
            {"source_type": "requirement", "source_id": "FR-1",
             "target_type": "task", "target_id": "7",
             "relation": "implemented_by"}
        ]},
    }
    artifacts = {}
    for key in ("source_blocks", "requirements", "capabilities", "edges"):
        artifact_path = TOPOLOGY_ARTIFACTS[key]
        raw = json.dumps(docs[artifact_path]).encode("utf-8")
        artifacts[artifact_path] = "sha256:" + hashlib.sha256(raw).hexdigest()
    docs[TOPOLOGY_ARTIFACTS["manifest"]] = {
        "schema_version": "newrouge.semantic-topology-manifest.v1",
        "source_revision": "source-set:test",
        "source_manifest_sha256": "sha256:" + ("0" * 64),
        "repository_revision": revision,
        "schema_revision": "v1",
        "generator_revision": "test",
        "artifacts": artifacts,
    }
    return docs


class SemanticTopologyTests(unittest.TestCase):
    def test_validator_allows_legacy_checkout_without_git_main_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/python/validate_semantic_topology.py",
                    "--repo-root",
                    tmp,
                ],
                cwd=Path(__file__).resolve().parents[3],
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertEqual("legacy_unmapped", json.loads(completed.stdout)["status"])

    def test_validator_blocks_partial_topology_without_touching_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / TOPOLOGY_ARTIFACTS["manifest"]
            manifest.parent.mkdir(parents=True)
            manifest.write_text("{}", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/python/validate_semantic_topology.py",
                    "--repo-root",
                    tmp,
                ],
                cwd=Path(__file__).resolve().parents[3],
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )
            self.assertEqual(1, completed.returncode)
            payload = json.loads(completed.stdout)
            self.assertEqual("blocked", payload["status"])
            self.assertEqual("partial topology artifact set", payload["reason"])

    def test_kcp_builder_classifies_topology_as_derived_planning_source(self):
        snapshot = FakeSnapshot({
            "docs/planning/semantic-topology/semantic-requirements.v1.json": {
                "requirements": [{"requirement_id": "FR-1"}]
            },
            "docs/planning/semantic-topology/schemas/semantic-requirements.v1.schema.json": {
                "$id": "newrouge.semantic-requirements.v1"
            },
        })
        policies = {
            "policy_revision": "test",
            "policies": [{
                "consumer": "repository-session",
                "domains": ["game-design"],
                "statuses": ["active"],
                "visibility": ["active"],
                "exact_paths": [],
                "path_prefixes": ["docs/planning/semantic-topology/"],
            }],
        }
        _snapshot, catalog, projections = build_layers(snapshot, {"rules": []}, policies)
        self.assertEqual(2, len(catalog["modules"]))
        modules = {module["source_path"]: module for module in catalog["modules"]}
        semantic_path = "docs/planning/semantic-topology/semantic-requirements.v1.json"
        schema_path = "docs/planning/semantic-topology/schemas/semantic-requirements.v1.schema.json"
        self.assertEqual("semantic-topology", modules[semantic_path]["kind"])
        self.assertEqual("derived-planning-topology", modules[semantic_path]["source_role"])
        self.assertFalse(modules[schema_path]["semantic_eligible"])
        eligible = projections["projections"][0]["eligible_module_ids"]
        self.assertEqual([modules[semantic_path]["module_id"]], eligible)

    def test_kcp_locator_returns_topology_node_authority_and_related_task(self):
        source_text = "Requirement text\n"
        source_sha = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
        snapshot = FakeSnapshot({
            "docs/gdd/a.md": source_text,
            "docs/planning/semantic-topology/source-blocks.v1.json": {
                "blocks": [{
                    "block_id": "SB-1",
                    "source_path": "docs/gdd/a.md",
                    "source_sha256": source_sha,
                    "line_start": 1,
                    "line_end": 1,
                }]
            },
            "docs/planning/semantic-topology/semantic-requirements.v1.json": {
                "requirements": [{
                    "requirement_id": "FR-1",
                    "statement": "Requirement text",
                    "kind": "functional",
                    "source_block_ids": ["SB-1"],
                }]
            },
            "docs/planning/semantic-topology/capabilities.v1.json": {
                "capabilities": [{
                    "capability_id": "CAP-1",
                    "title": "Test capability",
                    "requirement_ids": ["FR-1"],
                }]
            },
            "docs/planning/semantic-topology/topology-edges.v1.json": {
                "edges": [
                    {
                        "source_type": "requirement", "source_id": "FR-1",
                        "target_type": "capability", "target_id": "CAP-1",
                        "relation": "grouped_by",
                    },
                    {
                        "source_type": "capability", "source_id": "CAP-1",
                        "target_type": "task", "target_id": "7",
                        "relation": "implemented_by",
                    },
                ]
            },
        })
        policy = {
            "consumer": "repository-session",
            "domains": ["game-design"],
            "statuses": ["active"],
            "visibility": ["active"],
            "path_prefixes": ["docs/planning/semantic-topology/"],
            "exact_paths": [],
        }
        policies = {"policy_revision": "test", "policies": [policy]}
        _snapshot, catalog, projections = build_layers(snapshot, {"rules": []}, policies)
        eligible = set(projections["projections"][0]["eligible_module_ids"])
        result = locate({"query": "FR-1"}, catalog, policy, eligible, 5)
        self.assertEqual("matched", result["status"])
        candidate = next(
            item for item in result["candidates"]
            if item.get("topology_node", {}).get("node_id") == "FR-1"
        )
        node = candidate["topology_node"]
        self.assertEqual("requirement", node["node_type"])
        self.assertEqual(["7"], node["related_task_ids"])
        self.assertEqual("docs/gdd/a.md", node["authority_sources"][0]["path"])
        self.assertEqual(source_sha, node["authority_sources"][0]["source_sha256"])
        self.assertEqual("topology-node", candidate["rank_evidence"]["location_strategy"])

        capability_result = locate({"query": "CAP-1"}, catalog, policy, eligible, 5)
        capability_candidate = next(
            item for item in capability_result["candidates"]
            if item.get("topology_node", {}).get("node_id") == "CAP-1"
        )
        capability_node = capability_candidate["topology_node"]
        self.assertEqual(["7"], capability_node["related_task_ids"])
        self.assertEqual("docs/gdd/a.md", capability_node["authority_sources"][0]["path"])

    def test_workspace_stabilized_view_is_distinct_from_latest_successful(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stable = root / WORKSPACE_TOPOLOGY_STABLE
            stabilized = root / WORKSPACE_TOPOLOGY_STABILIZED
            stable.parent.mkdir(parents=True, exist_ok=True)
            base = {
                "schema_version": "newrouge.semantic-topology-view.v1",
                "available": True,
                "fresh": True,
                "identity": {"kind": "workspace", "revision": "workspace:test"},
                "status": "fresh",
                "nodes": {"source_blocks": [], "requirements": [], "capabilities": [], "tasks": [], "acceptance": []},
                "edges": [], "task_trace": {}, "summary": {}, "problems": [],
            }
            stable.write_text(json.dumps({**base, "identity": {**base["identity"], "trigger_run_id": "chapter3-run"}}), encoding="utf-8")
            stabilized.write_text(json.dumps({**base, "identity": {**base["identity"], "trigger_run_id": "chapter5-run"}}), encoding="utf-8")
            latest = load_workspace_topology(root, "stable")
            chapter5 = load_workspace_topology(root, "stabilized")
            self.assertEqual("chapter3-run", latest["identity"]["trigger_run_id"])
            self.assertEqual("chapter5-run", chapter5["identity"]["trigger_run_id"])
            self.assertEqual("stabilized", chapter5["workspace_view"])

    def test_missing_artifacts_are_explicit_legacy_unmapped(self):
        view = load_topology_from_snapshot(FakeSnapshot({}), [])
        self.assertFalse(view["available"])
        self.assertEqual("legacy_unmapped", view["status"])

    def test_valid_topology_is_revision_bound_and_traces_tasks(self):
        details = [{
            "task": {"id": 7, "title": "Do it", "status": "pending"},
            "godot": {
                "status": "static_attached",
                "scenes": [{"scene": "Game.Godot/Scenes/Main.tscn"}],
            },
        }]
        view = load_topology_from_snapshot(FakeSnapshot(valid_docs()), details)
        self.assertTrue(view["available"])
        self.assertTrue(view["fresh"])
        self.assertEqual(["FR-1"], view["task_trace"]["7"]["requirements"])
        graph = {"nodes": {"Game.Godot/Scenes/Main.tscn": {}}, "edges": []}
        attach_scene_design_trace(graph, view, details)
        trace = graph["design_trace"]["Game.Godot/Scenes/Main.tscn"]
        self.assertEqual(["FR-1"], trace["requirements"])
        self.assertEqual("navigation_only", trace["semantic_claim"])

    def test_acceptance_nodes_project_existing_task_view_authority(self):
        details = [{
            "task": {"id": 7, "title": "Do it", "status": "pending"},
            "mappings": {
                "tasks_back": [{
                    "taskmaster_id": 7,
                    "acceptance": ["Result must be deterministic."],
                }],
                "tasks_gameplay": [],
            },
            "godot": {"status": "unmapped", "scenes": []},
        }]
        view = load_topology_from_snapshot(FakeSnapshot(valid_docs()), details)
        self.assertEqual(1, len(view["nodes"]["acceptance"]))
        acceptance = view["nodes"]["acceptance"][0]
        self.assertEqual("7", acceptance["task_id"])
        self.assertEqual("unmapped", acceptance["topology_origin"])
        self.assertIn(acceptance["acceptance_id"], view["task_trace"]["7"]["acceptance"])
        self.assertEqual(0, view["summary"]["acceptance_with_semantic_origin"])

        docs = valid_docs()
        docs[TOPOLOGY_ARTIFACTS["edges"]]["edges"].append({
            "source_type": "requirement",
            "source_id": "FR-1",
            "target_type": "acceptance",
            "target_id": acceptance["acceptance_id"],
            "relation": "accepted_by",
        })
        view = load_topology_from_snapshot(FakeSnapshot(docs), details)
        self.assertEqual(1, view["summary"]["acceptance_with_semantic_origin"])
        self.assertEqual("mapped", view["nodes"]["acceptance"][0]["topology_origin"])

    def test_capability_without_delivery_sink_keeps_requirement_orphan(self):
        docs = valid_docs()
        docs[TOPOLOGY_ARTIFACTS["edges"]] = {"edges": [
            {"source_type": "requirement", "source_id": "FR-1",
             "target_type": "capability", "target_id": "CAP-1",
             "relation": "grouped_by"}
        ]}
        view = load_topology_from_snapshot(FakeSnapshot(docs), [])
        self.assertEqual(1, view["summary"]["orphan_requirements"])
        requirement = view["nodes"]["requirements"][0]
        self.assertFalse(requirement["sink_resolved"])
        self.assertIn("orphan", requirement["topology_states"])
        docs[TOPOLOGY_ARTIFACTS["edges"]]["edges"].append(
            {"source_type": "capability", "source_id": "CAP-1",
             "target_type": "task", "target_id": "7",
             "relation": "implemented_by"}
        )
        details = [{"task": {"id": 7, "status": "pending"}, "godot": {"scenes": []}}]
        view = load_topology_from_snapshot(FakeSnapshot(docs), details)
        self.assertEqual(0, view["summary"]["orphan_requirements"])
        self.assertTrue(view["nodes"]["requirements"][0]["sink_resolved"])

    def test_revision_mismatch_is_stale_not_rewritten(self):
        view = load_topology_from_snapshot(FakeSnapshot(valid_docs("b" * 40)), [])
        self.assertFalse(view["fresh"])
        self.assertTrue(any(
            x["kind"] == "repository_revision_mismatch" for x in view["problems"]
        ))

    def test_source_hash_drift_marks_topology_stale(self):
        docs = valid_docs()
        docs["docs/gdd/a.md"] = "Changed requirement text\n"
        view = load_topology_from_snapshot(FakeSnapshot(docs), [])
        self.assertFalse(view["fresh"])
        self.assertTrue(any(x["kind"] == "source_hash_mismatch" for x in view["problems"]))

    def test_task_semantic_refs_must_resolve(self):
        details = [{"task": {"id": 7, "status": "pending", "semantic_refs": ["FR-MISSING"]},
                    "godot": {"scenes": []}}]
        view = load_topology_from_snapshot(FakeSnapshot(valid_docs()), details)
        self.assertFalse(view["fresh"])
        self.assertTrue(any(x["kind"] == "invalid_task_semantic_ref" for x in view["problems"]))

    def test_workspace_preview_rejects_main_authority_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "logs/ci/project-health-knowledge/topology/workspace-latest.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({
                "available": True,
                "identity": {
                    "kind": "workspace",
                    "revision": "workspace:test",
                    "authority_ref": "refs/heads/main",
                },
            }), encoding="utf-8")
            view = load_workspace_topology(root)
            self.assertFalse(view["available"])
            self.assertTrue(any(
                item["kind"] == "workspace_claims_main_authority"
                for item in view["problems"]
            ))

    def test_workspace_preview_requires_workspace_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "logs/ci/project-health-knowledge/topology/workspace-latest.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({
                "available": True,
                "identity": {"kind": "main", "revision": "x"},
            }), encoding="utf-8")
            view = load_workspace_topology(root)
            self.assertFalse(view["available"])
            self.assertEqual("workspace", view["identity"]["kind"])


if __name__ == "__main__":
    unittest.main()
