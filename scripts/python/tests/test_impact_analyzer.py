import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.python.impact_analysis_index import ImpactIndexError
from scripts.python.impact_analyzer import (
    ImpactAnalyzer,
    ResolvedTarget,
    SymbolIndex,
    TargetResolver,
    _edge,
    _sort_edges,
    classify_risk,
    load_frozen_binding,
    validate_report_document,
)


REVISION = "a" * 40
SHA = "b" * 64


def aliases(event=None, contract=None):
    return {
        "schema_version": "newrouge.impact-target-aliases.v1",
        "alias_table_revision": "test",
        "aliases": {"event": event or {}, "contract": contract or {}},
    }


def hashes_for(sources):
    return {path: hashlib.sha256(text.encode("utf-8")).hexdigest() for path, text in sources.items()}


def binding():
    return {
        "consumer": "chapter6",
        "task_id": "T1",
        "frozen_context_path": "logs/ci/knowledge-context/frozen.json",
        "frozen_context_sha256": "1" * 64,
        "decision_set_sha256": "2" * 64,
        "freeze_point": "before-red",
        "publication_generation": "generation-1",
        "publication_sha256": "3" * 64,
    }


def analyzer_for(sources):
    analyzer = ImpactAnalyzer.__new__(ImpactAnalyzer)
    analyzer.root = Path(".").resolve()
    analyzer.revision = REVISION
    analyzer.trusted_ref = "refs/heads/test"
    analyzer.index_sha256 = "4" * 64
    analyzer.index = {"index_id": "idx-" + "5" * 64, "analysis_config_revision": "config-v1"}
    analyzer.manifest = {"trusted_ref": "refs/heads/test"}
    analyzer.sources = dict(sources)
    analyzer.hashes = hashes_for(sources)
    analyzer.resolver = TargetResolver(analyzer.index, analyzer.sources, analyzer.hashes, aliases())
    return analyzer


def valid_report():
    edge = _edge(
        "file",
        "Game.Core/Services/Consumer.cs",
        "symbol",
        "Demo.Target",
        "references",
        "Game.Core/Services/Consumer.cs",
        "line:4-4",
        "6" * 64,
    )
    return {
        "schema_version": "newrouge.impact-analysis.v1",
        "status": "ok",
        "repository_revision": REVISION,
        "trusted_ref": "refs/heads/test",
        "index_id": "idx-" + "5" * 64,
        "index_sha256": "4" * 64,
        "analyzer_implementation_revision": "newrouge.impact-analyzer.v1",
        "analysis_config_revision": "config-v1",
        "toolchain": {"python": "3.13.7"},
        "target": {
            "kind": "class",
            "identity": "Demo.Target",
            "canonical_path": "Game.Core/Services/Target.cs",
            "source_sha256": "7" * 64,
            "resolution_method": "exact-index-symbol",
        },
        "affected_files": ["Game.Core/Services/Consumer.cs", "Game.Core/Services/Target.cs"],
        "affected_symbols": ["Demo.Target"],
        "impact_edges": [edge],
        "tests": [],
        "runtime_refs": [],
        "knowledge_refs": [],
        "risk_level": "medium",
        "risk_policy_revision": "newrouge.impact-risk.v1",
        "matched_risk_rules": ["service-target"],
        "risk_reasons": ["service target"],
        "generated_at": "2026-09-05T00:00:00Z",
        "failure_reason": None,
        "knowledge_binding": binding(),
    }


class ImpactAnalyzerUnitTests(unittest.TestCase):
    def assert_error(self, code, action):
        with self.assertRaises(ImpactIndexError) as caught:
            action()
        self.assertEqual(caught.exception.code, code)

    def test_symbol_parser_ignores_comments_strings_and_character_literals(self):
        sources = {
            "Game.Core/Real.cs": '''namespace Demo;
// public sealed class CommentOnly {}
/* public interface BlockOnly {} */
public sealed class Real
{
    private const string Fake = "public sealed class StringOnly {}";
    private const char Brace = '}';
}
'''
        }
        index = SymbolIndex(sources, hashes_for(sources))
        identities = {symbol.identity for symbol in index.symbols}
        self.assertIn("Demo.Real", identities)
        self.assertNotIn("Demo.CommentOnly", identities)
        self.assertNotIn("Demo.BlockOnly", identities)
        self.assertNotIn("Demo.StringOnly", identities)

    def test_method_identity_normalizes_nested_parameters_and_resolves_overload(self):
        sources = {
            "Game.Core/Worker.cs": '''using System.Collections.Generic;
namespace Demo;
public sealed class Worker<T>
{
    public void Run(string value, ref int[] counts, bool? enabled, Dictionary<string, List<int?>> items) { }
    public void Run(int value) { }
}
'''
        }
        resolver = TargetResolver({}, sources, hashes_for(sources), aliases())
        target = resolver.resolve({
            "type": "method",
            "id": "Demo.Worker`1::Run(System.String,System.Int32[]&,System.Nullable`1<System.Boolean>,System.Collections.Generic.Dictionary`2<System.String,System.Collections.Generic.List`1<System.Nullable`1<System.Int32>>>)",
        })
        self.assertEqual(target.canonical_path, "Game.Core/Worker.cs")
        self.assertEqual(target.resolution_method, "exact-index-symbol")

    def test_incomplete_overload_constructor_and_dynamic_target_fail_closed(self):
        sources = {
            "Game.Core/Worker.cs": "namespace Demo; public sealed class Worker { public Worker() {} public void Run(int value) {} public void Run(string value) {} }"
        }
        resolver = TargetResolver({}, sources, hashes_for(sources), aliases())
        self.assert_error("ambiguous_target", lambda: resolver.resolve({"type": "method", "id": "Demo.Worker::Run"}))
        self.assert_error("unsupported_target", lambda: resolver.resolve({"type": "method", "id": "Demo.Worker::.ctor()"}))
        self.assert_error("unsupported_target", lambda: resolver.resolve({"type": "method", "id": "Demo.Worker::Run(dynamic)"}))

    def test_exact_identity_wins_before_kind_scoped_alias(self):
        sources = {
            "Game.Core/Contracts/Events/CurrentEvent.cs": "namespace Demo; public sealed record CurrentEvent;",
            "Game.Core/Contracts/Events/LegacyEvent.cs": "namespace Demo; public sealed record LegacyEvent;",
        }
        resolver = TargetResolver(
            {},
            sources,
            hashes_for(sources),
            aliases(event={"Demo.CurrentEvent": "Demo.LegacyEvent", "legacy": "Demo.LegacyEvent"}),
        )
        exact = resolver.resolve({"type": "event", "id": "Demo.CurrentEvent"})
        alias_target = resolver.resolve({"type": "event", "id": "legacy"})
        self.assertEqual(exact.identity, "Demo.CurrentEvent")
        self.assertEqual(exact.resolution_method, "exact-index-symbol")
        self.assertEqual(alias_target.identity, "Demo.LegacyEvent")
        self.assertEqual(alias_target.resolution_method, "kind-scoped-alias")

    def test_alias_must_resolve_to_same_kind_under_contracts(self):
        sources = {
            "Game.Core/Elsewhere/ExternalEvent.cs": "namespace Demo; public sealed record ExternalEvent;",
            "Game.Core/Contracts/Value.cs": "namespace Demo; public sealed record Value;",
        }
        outside = TargetResolver({}, sources, hashes_for(sources), aliases(event={"legacy": "Demo.ExternalEvent"}))
        cross_kind = TargetResolver({}, sources, hashes_for(sources), aliases(event={"value": "Demo.Value"}))
        self.assert_error("invalid_manifest", lambda: outside.resolve({"type": "event", "id": "legacy"}))
        self.assert_error("invalid_manifest", lambda: cross_kind.resolve({"type": "event", "id": "value"}))

    def test_underqualified_and_ambiguous_symbols_are_rejected(self):
        sources = {
            "Game.Core/A.cs": "namespace A; public sealed class Worker {}",
            "Game.Core/B.cs": "namespace B; public sealed class Worker {}",
        }
        resolver = TargetResolver({}, sources, hashes_for(sources), aliases())
        self.assert_error("underqualified_target", lambda: resolver.resolve({"type": "class", "id": "Worker"}))
        duplicate = {
            "Game.Core/A.cs": "namespace A; public sealed class Worker {}",
            "Game.Core/A2.cs": "namespace A; public sealed class Worker {}",
        }
        ambiguous = TargetResolver({}, duplicate, hashes_for(duplicate), aliases())
        self.assert_error("ambiguous_target", lambda: ambiguous.resolve({"type": "class", "id": "A.Worker"}))

    def test_analyzer_emits_only_provable_csharp_and_test_evidence(self):
        sources = {
            "Game.Core/Contracts/Events/TestEvent.cs": "namespace Demo.Contracts; public sealed record TestEvent(int Value);",
            "Game.Core/Services/TestService.cs": '''using Demo.Contracts;
namespace Demo.Services;
public sealed class TestService
{
    public void Handle(TestEvent value) { _ = value; }
}
''',
            "Game.Core.Tests/Services/TestServiceTests.cs": '''using Demo.Contracts;
namespace Demo.Tests;
public sealed class TestServiceTests
{
    public void Handles_event()
    {
        var value = new TestEvent(1);
    }
    // Refs:
    // - Demo.Contracts.TestEvent
}
''',
            "Game.Core/CommentOnly.cs": '''namespace Demo;
public sealed class CommentOnly
{
    // TestEvent must not count.
    private const string Name = "TestEvent";
}
''',
            "Game.Godot/Scenes/Fake.tscn": '[node name="TestEvent" type="Node"]\n',
            "docs/fake.md": "TestEvent is mentioned here.\n",
        }
        report = analyzer_for(sources).analyze({"type": "event", "id": "Demo.Contracts.TestEvent"}, binding())
        relations = [edge["relation"] for edge in report["impact_edges"]]
        evidence_paths = {edge["evidence_path"] for edge in report["impact_edges"]}
        self.assertIn("consumes", relations)
        self.assertIn("tests", relations)
        self.assertTrue(any(edge["from_kind"] == "test_symbol" for edge in report["impact_edges"]))
        self.assertNotIn("Game.Core/CommentOnly.cs", evidence_paths)
        self.assertNotIn("Game.Godot/Scenes/Fake.tscn", evidence_paths)
        self.assertNotIn("docs/fake.md", evidence_paths)
        self.assertEqual(report["runtime_refs"], [])
        self.assertEqual(report["knowledge_refs"], [])
        expected = sorted(report["impact_edges"], key=lambda edge: (
            edge["from_kind"], edge["from"], edge["to_kind"], edge["to"], edge["relation"], edge["evidence_path"], edge["evidence_anchor"]
        ))
        self.assertEqual(report["impact_edges"], expected)
        source_hashes = hashes_for(sources)
        for edge in report["impact_edges"]:
            self.assertEqual(edge["evidence_sha256"], source_hashes[edge["evidence_path"]])

    def test_inheritance_implementation_and_reference_edges_use_legal_endpoints(self):
        sources = {
            "Game.Core/IWorker.cs": "namespace Demo; public interface IWorker { }",
            "Game.Core/BaseWorker.cs": "namespace Demo; public class BaseWorker { }",
            "Game.Core/Worker.cs": "namespace Demo; public sealed class Worker : BaseWorker, IWorker { }",
            "Game.Core/Consumer.cs": "namespace Demo; public sealed class Consumer { private Worker? _worker; }",
        }
        interface_report = analyzer_for(sources).analyze({"type": "interface", "id": "Demo.IWorker"}, binding())
        base_report = analyzer_for(sources).analyze({"type": "class", "id": "Demo.BaseWorker"}, binding())
        worker_report = analyzer_for(sources).analyze({"type": "class", "id": "Demo.Worker"}, binding())
        self.assertIn("implements", {edge["relation"] for edge in interface_report["impact_edges"]})
        self.assertIn("inherits", {edge["relation"] for edge in base_report["impact_edges"]})
        reference = next(edge for edge in worker_report["impact_edges"] if edge["relation"] == "references")
        self.assertEqual((reference["from_kind"], reference["to_kind"]), ("file", "symbol"))

    def test_edge_validation_rejects_bad_endpoint_anchor_and_hash(self):
        self.assert_error("unsupported_relation", lambda: _edge("event", "E", "class", "C", "consumes", "x.cs", "line:1-1", SHA))
        self.assert_error("source_read_failure", lambda: _edge("file", "x.cs", "symbol", "C", "references", "x.cs", "free form", SHA))
        self.assert_error("source_read_failure", lambda: _edge("file", "x.cs", "symbol", "C", "references", "x.cs", "line:2-1", "bad"))

    def test_risk_policy_uses_highest_applicable_rule(self):
        cases = [
            (ResolvedTarget("contract", "Demo.Contract", "Game.Core/Contracts/Contract.cs", SHA, "exact"), [], "high", "contract-target"),
            (ResolvedTarget("event", "Demo.Event", "Game.Core/Contracts/Event.cs", SHA, "exact"), [], "high", "event-target"),
            (ResolvedTarget("file", "Game.Core/Save/Schema.cs", "Game.Core/Save/Schema.cs", SHA, "exact"), [], "high", "save-format-target"),
            (ResolvedTarget("class", "Demo.Damage", "Game.Core/Combat/Damage.cs", SHA, "exact"), [], "high", "core-domain-target"),
            (ResolvedTarget("class", "Demo.AudioService", "Game.Godot/Services/AudioService.cs", SHA, "exact"), [], "medium", "service-target"),
            (ResolvedTarget("system", "Demo.AudioSystem", "Game.Godot/Systems/AudioSystem.cs", SHA, "exact"), [], "medium", "system-target"),
            (ResolvedTarget("class", "Demo.MenuView", "Game.Godot/Scripts/UI/MenuView.cs", SHA, "exact"), [], "low", "ui-only-target"),
            (ResolvedTarget("class", "Demo.Tool", "tools/Tool.cs", SHA, "exact"), [], "unknown", "insufficient-evidence"),
        ]
        for target, edges, expected_level, expected_rule in cases:
            with self.subTest(target=target.identity):
                level, rules, reasons = classify_risk(target, edges)
                self.assertEqual(level, expected_level)
                self.assertIn(expected_rule, rules)
                self.assertEqual(len(rules), len(reasons))

        mixed_target = ResolvedTarget("class", "Demo.MenuView", "Game.Godot/Scripts/UI/MenuView.cs", SHA, "exact")
        mixed_edge = _edge("file", "Game.Core/Combat/Driver.cs", "symbol", "Demo.MenuView", "references", "Game.Core/Combat/Driver.cs", "line:1-1", SHA)
        level, rules, _ = classify_risk(mixed_target, [mixed_edge])
        self.assertEqual(level, "low")
        self.assertEqual(rules, ["ui-only-target"])

    def test_report_validator_rejects_every_malformed_section_stably(self):
        validate_report_document(valid_report())
        invalid_manifest_mutations = [
            lambda report: report.update(target=None),
            lambda report: report.update(affected_files={}),
            lambda report: report["impact_edges"][0].pop("from"),
            lambda report: report["impact_edges"][0].update(evidence_sha256="bad"),
            lambda report: report.update(repository_revision="short"),
            lambda report: report.update(index_sha256="bad"),
            lambda report: report.update(matched_risk_rules=["event-target"]),
            lambda report: report.update(runtime_refs=[{"fake": True}]),
            lambda report: report.update(failure_reason={"code": "bad"}),
        ]
        for mutate in invalid_manifest_mutations:
            report = valid_report()
            mutate(report)
            with self.subTest(mutation=mutate):
                self.assert_error("invalid_manifest", lambda report=report: validate_report_document(report))

        for mutate in [
            lambda report: report.update(knowledge_binding=None),
            lambda report: report["knowledge_binding"].update(frozen_context_sha256="bad"),
        ]:
            report = valid_report()
            mutate(report)
            self.assert_error("invalid_kcp_binding", lambda report=report: validate_report_document(report))

    def test_projection_is_deterministic_for_different_input_iteration_order(self):
        ordered = {
            "Game.Core/Target.cs": "namespace Demo; public sealed class Target { }",
            "Game.Core/ZConsumer.cs": "namespace Demo; public sealed class ZConsumer { private Target? _target; }",
            "Game.Core/AConsumer.cs": "namespace Demo; public sealed class AConsumer { private Target? _target; }",
        }
        reversed_sources = dict(reversed(list(ordered.items())))
        first = analyzer_for(ordered).analyze({"type": "class", "id": "Demo.Target"}, binding())
        second = analyzer_for(reversed_sources).analyze({"type": "class", "id": "Demo.Target"}, binding())
        first.pop("generated_at")
        second.pop("generated_at")
        self.assertEqual(first, second)

    def test_index_unavailable_is_fail_closed(self):
        self.assert_error(
            "missing_index",
            lambda: ImpactAnalyzer(Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp()) / "impact-index.v1.json", REVISION),
        )

    def test_kcp_binding_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "frozen.json"
            path.write_text(json.dumps({
                "schema_version": "newrouge.knowledge-frozen-context.v1",
                "freeze_state": "frozen",
                "snapshot": {"commit": "b" * 40},
                "consumer": "chapter6",
            }), encoding="utf-8")
            self.assert_error(
                "revision_mismatch",
                lambda: load_frozen_binding(Path(directory), "frozen.json", REVISION, "chapter6", "T1"),
            )

    def test_raw_strings_do_not_create_symbols(self):
        source = {'Game.Core/Raw.cs': 'namespace Demo;\nvar text = """ public class Fake { } """;\nvar interpolated = $""" public interface FakeToo { } """;\npublic sealed class Real { }'}
        symbols = SymbolIndex(source, hashes_for(source)).symbols
        self.assertEqual([s.identity for s in symbols if s.kind == 'class'], ['Demo.Real'])
        self.assertFalse(any(s.identity == 'Demo.FakeToo' for s in symbols))

    def test_duplicate_fully_qualified_symbol_identity_is_ambiguous(self):
        source = {'A.cs': 'namespace Demo; public class Same {}', 'B.cs': 'namespace Demo; public class Same {}'}
        resolver = TargetResolver({}, source, hashes_for(source), aliases())
        self.assert_error('ambiguous_target', lambda: resolver.resolve({'type': 'class', 'id': 'Demo.Same'}))

    def test_unsupported_type_forms_fail_closed(self):
        source = {'A.cs': 'namespace Demo; public class Worker { public void Run(int x) {} }'}
        resolver = TargetResolver({}, source, hashes_for(source), aliases())
        for parameter in ('int*', '(int,string)', 'delegate*<int,void>', 'T'):
            self.assert_error('unsupported_target', lambda parameter=parameter: resolver.resolve({'type': 'method', 'id': f'Demo.Worker::Run({parameter})'}))

    def test_interface_and_abstract_methods_are_indexed_but_calls_are_not(self):
        source = {'A.cs': '''namespace Demo; public interface IWorker { void Run(int value); } public abstract class Base { protected abstract void Stop(); } public sealed class Use { void X() { Run(1); } }'''}
        index = SymbolIndex(source, hashes_for(source))
        method_ids = {s.identity for s in index.symbols if s.kind == 'method'}
        self.assertIn('Demo.IWorker::Run(System.Int32)', method_ids)
        self.assertIn('Demo.Base::Stop()', method_ids)
        self.assertNotIn('Demo.Use::Run(System.Int32)', method_ids)

    def test_inheritance_does_not_cross_namespace_short_name(self):
        source = {'A.cs': 'namespace A; public class Base {} public class Child : Base {}', 'B.cs': 'namespace B; public class Base {}'}
        report = analyzer_for(source).analyze({'type': 'class', 'id': 'B.Base'}, binding())
        self.assertNotIn('inherits', {edge['relation'] for edge in report['impact_edges']})

    def test_using_directive_and_qualified_references_are_provable(self):
        source = {'A.cs': 'namespace A; public class Target {}', 'B.cs': 'using A; namespace B; public class Consumer { private A.Target? value; }'}
        report = analyzer_for(source).analyze({'type': 'class', 'id': 'A.Target'}, binding())
        references = [edge for edge in report['impact_edges'] if edge['relation'] == 'references']
        self.assertTrue(references)
        self.assertTrue(all(edge['to_kind'] == 'symbol' for edge in references))

    def test_refs_can_be_same_line_or_following_line(self):
        source = {
            'A.cs': 'namespace Demo; public class Target {}',
            'A.Tests.cs': 'namespace Demo.Tests; public class TargetTests { // Refs: Demo.Target\n public void Covers() {} }',
        }
        report = analyzer_for(source).analyze({'type': 'class', 'id': 'Demo.Target'}, binding())
        self.assertTrue(any(edge['relation'] == 'tests' and edge['from_kind'] == 'test_symbol' for edge in report['impact_edges']))

    def test_edge_conflicting_duplicate_payload_is_rejected(self):
        edge = _edge('file', 'A.cs', 'symbol', 'Demo.Target', 'references', 'A.cs', 'line:1-1', SHA)
        conflict = dict(edge, evidence_sha256='c' * 64)
        self.assert_error('invalid_manifest', lambda: _sort_edges([edge, conflict]))

    def test_edge_rejects_path_outside_indexed_source_universe(self):
        self.assert_error('source_read_failure', lambda: _edge('file', 'A.cs', 'symbol', 'Demo.Target', 'references', 'Missing.cs', 'line:1-1', SHA, indexed_hashes={'A.cs': SHA}))

    def test_non_csharp_sources_do_not_create_symbols(self):
        sources = {
            'Game.Core/Real.cs': 'namespace Demo; public class Real {}',
            'Game.Godot/Fake.tscn': 'namespace Demo; public class Fake {}',
            'docs/fake.md': 'namespace Demo; public class FakeToo {}',
        }
        symbols = SymbolIndex(sources, hashes_for(sources)).symbols
        identities = {symbol.identity for symbol in symbols}
        self.assertIn('Demo.Real', identities)
        self.assertNotIn('Demo.Fake', identities)
        self.assertNotIn('Demo.FakeToo', identities)


if __name__ == "__main__":
    unittest.main()
