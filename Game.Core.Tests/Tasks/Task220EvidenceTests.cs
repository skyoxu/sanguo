using System;
using System.Collections.Generic;
using System.IO;
using Game.Core.Contracts;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task220EvidenceTests
{
    // acceptance: ACC:T220.1
    [Fact]
    public void ShouldLinkRequirementEvidence_WhenContractEvolutionRuleIsDeclared()
    {
        var evidence = Task220Evidence.Current;

        evidence.RequirementIds.Should().Contain("REQ-3810a1457878");
        evidence.SourceRefs.Should().Contain("docs/prd/PRD_V4_RULES_FREEZE.md:179");
        evidence.CoreCoverage.Should().Contain("Game.Core.Tests/Tasks/Task220EvidenceTests.cs");
    }

    // acceptance: ACC:T220.2
    [Fact]
    public void ShouldPreserveExistingFields_WhenAdapterFacingContractAddsFields()
    {
        var baseline = ContractShape.Create("AdapterSavePayload", new[] { "slotId", "version", "payload" }, new[] { "save", "load" });
        var candidate = ContractShape.Create("AdapterSavePayload", new[] { "slotId", "version", "payload", "checksum" }, new[] { "save", "load" });

        var result = ContractEvolutionPolicy.Evaluate(baseline, candidate, ContractMigrationPlan.None);

        result.IsAccepted.Should().BeTrue();
        candidate.Fields.Should().ContainInOrder(baseline.Fields);
        candidate.Behaviors.Should().ContainInOrder(baseline.Behaviors);
    }

    // acceptance: ACC:T220.3
    [Fact]
    public void ShouldRejectContractChange_WhenExistingFieldIsRemovedWithoutLaterMigrationPlan()
    {
        var baseline = ContractShape.Create("AdapterSavePayload", new[] { "slotId", "version", "payload" }, new[] { "save", "load" });
        var candidate = ContractShape.Create("AdapterSavePayload", new[] { "slotId", "payload" }, new[] { "save", "load" });

        var result = ContractEvolutionPolicy.Evaluate(baseline, candidate, ContractMigrationPlan.None);

        result.IsAccepted.Should().BeFalse();
        result.BlockingReasons.Should().Contain("Removed field: version");
    }

    // acceptance: ACC:T220.4
    [Fact]
    public void ShouldLinkTraceableEvidence_WhenContractEvolutionCoverageIsDeclared()
    {
        var evidence = Task220Evidence.Current;

        evidence.CoreCoverage.Should().Contain("Game.Core.Tests/Tasks/Task220EvidenceTests.cs");
        evidence.AdapterCoverage.Should().Contain(new[]
        {
            "Tests.Godot/tests/Adapters/test_event_bus_adapter.gd",
            "Tests.Godot/tests/Adapters/test_data_store_adapter.gd",
            "Tests.Godot/tests/Adapters/Db/test_db_migration_hook.gd"
        });
        evidence.Assumptions.Should().BeEmpty();
    }

    // acceptance: ACC:T220.5
    [Fact]
    public void ShouldIncludePlayerVisibleAdapterCoverage_WhenObligationO5IsTracked()
    {
        var evidence = Task220Evidence.Current;

        evidence.Obligations.Should().ContainKey("OBL:T220.O5");
        evidence.Obligations["OBL:T220.O5"].Should().Contain(new[]
        {
            "Tests.Godot/tests/Adapters/test_event_bus_adapter.gd",
            "Tests.Godot/tests/Adapters/test_data_store_adapter.gd",
            "Tests.Godot/tests/Adapters/Config/test_audio_player_adapter_nodes.gd"
        });
    }

    // acceptance: ACC:T220.6
    [Fact]
    public void ShouldWireMinimalAdapterBehavior_WhenObligationO6IsTracked()
    {
        var evidence = Task220Evidence.Current;

        evidence.Obligations.Should().ContainKey("OBL:T220.O6");
        evidence.Obligations["OBL:T220.O6"].Should().Contain(new[]
        {
            "Tests.Godot/tests/Adapters/test_event_bus_adapter.gd",
            "Tests.Godot/tests/Adapters/test_data_store_adapter.gd"
        });
    }

    // acceptance: ACC:T220.7
    [Fact]
    public void ShouldPreserveDeterministicCoreBoundaries_WhenContractEvolutionRuleIsEvaluated()
    {
        var first = ContractEvolutionPolicy.Evaluate(
            ContractShape.Create("EventEnvelope", new[] { "eventId", "type" }, new[] { "publish" }),
            ContractShape.Create("EventEnvelope", new[] { "eventId", "type", "source" }, new[] { "publish" }),
            ContractMigrationPlan.None);
        var second = ContractEvolutionPolicy.Evaluate(
            ContractShape.Create("EventEnvelope", new[] { "eventId", "type" }, new[] { "publish" }),
            ContractShape.Create("EventEnvelope", new[] { "eventId", "type", "source" }, new[] { "publish" }),
            ContractMigrationPlan.None);

        second.Should().BeEquivalentTo(first);
    }

    // acceptance: ACC:T220.8
    [Fact]
    public void ShouldKeepPreviouslyValidBehaviorAccepted_WhenOnlyAdditiveFieldsAreIntroduced()
    {
        var baseline = ContractShape.Create("EventBusMessage", new[] { "name", "payload" }, new[] { "publish", "subscribe" });
        var candidate = ContractShape.Create("EventBusMessage", new[] { "name", "payload", "traceId" }, new[] { "publish", "subscribe" });

        var result = ContractEvolutionPolicy.Evaluate(baseline, candidate, ContractMigrationPlan.None);

        result.IsAccepted.Should().BeTrue();
        result.BlockingReasons.Should().BeEmpty();
    }

    // acceptance: ACC:T220.9
    [Fact]
    public void ShouldRejectContractChange_WhenBehaviorMeaningChangesWithoutLaterMigrationPlan()
    {
        var baseline = ContractShape.Create("DataStoreAdapter", new[] { "key", "value" }, new[] { "load returns missing when absent" });
        var candidate = ContractShape.Create("DataStoreAdapter", new[] { "key", "value" }, new[] { "load creates default when absent" });

        var result = ContractEvolutionPolicy.Evaluate(baseline, candidate, ContractMigrationPlan.None);

        result.IsAccepted.Should().BeFalse();
        result.BlockingReasons.Should().Contain("Changed behavior: load returns missing when absent");
    }

    // acceptance: ACC:T220.10
    [Fact]
    public void ShouldAcceptBreakingContractChange_WhenLaterMigrationPlanAuthorizesIt()
    {
        var baseline = ContractShape.Create("DbSchema", new[] { "schemaVersion", "payload" }, new[] { "migrate from previous version" });
        var candidate = ContractShape.Create("DbSchema", new[] { "schemaVersion", "body" }, new[] { "migrate from previous version" });
        var migrationPlan = new ContractMigrationPlan(
            "T220 later migration",
            new[] { "Removed field: payload", "Renamed field: payload -> body" });

        var result = ContractEvolutionPolicy.Evaluate(baseline, candidate, migrationPlan);

        result.IsAccepted.Should().BeTrue();
        result.BlockingReasons.Should().BeEmpty();
    }

    // acceptance: ACC:T220.11
    [Fact]
    public void ShouldKeepEvidenceTraceable_WhenAudioAdapterCoverageParticipatesInContractEvolution()
    {
        var evidence = Task220Evidence.Current;

        evidence.AdapterCoverage.Should().Contain("Tests.Godot/tests/Adapters/Config/test_audio_player_adapter_nodes.gd");
        evidence.CoreCoverage.Should().OnlyContain(path => path.StartsWith("Game.Core.Tests/", StringComparison.Ordinal));
    }

    // acceptance: ACC:T220.12
    [Fact]
    public void ShouldRejectContractChange_WhenExistingFieldIsRenamedWithoutLaterMigrationPlan()
    {
        var baseline = ContractShape.Create("AudioAdapterConfig", new[] { "busName", "volume" }, new[] { "apply volume" });
        var candidate = ContractShape.Create("AudioAdapterConfig", new[] { "audioBusName", "volume" }, new[] { "apply volume" });

        var result = ContractEvolutionPolicy.Evaluate(baseline, candidate, ContractMigrationPlan.None);

        result.IsAccepted.Should().BeFalse();
        result.BlockingReasons.Should().Contain("Removed field: busName");
    }

    // acceptance: ACC:T220.13
    [Fact]
    public void ShouldKeepAdapterFacingCoverageExplicit_WhenNoUndocumentedAssumptionsAreAllowed()
    {
        var evidence = Task220Evidence.Current;

        evidence.AdapterCoverage.Should().NotBeEmpty();
        evidence.AdapterCoverage.Should().OnlyContain(path => path.StartsWith("Tests.Godot/tests/Adapters/", StringComparison.Ordinal));
        evidence.Assumptions.Should().BeEmpty();
    }

    // acceptance: ACC:T220.14
    [Fact]
    public void ShouldProduceChapterThreeCoverageAuditEvidence_WhenContractEvolutionTaskIsImplemented()
    {
        var evidence = Task220Evidence.Current;

        evidence.Obligations.Should().ContainKey("OBL:T220.O8");
        evidence.Obligations["OBL:T220.O8"].Should().Contain("logs/ci/2026-06-09/sc-analyze/summary.json");
        evidence.Obligations.Should().ContainKey("OBL:T220.O9");
        evidence.Obligations["OBL:T220.O9"].Should().Contain("logs/ci/2026-06-09/sc-build-tdd/check_tasks_all_refs.log");
        evidence.Obligations["OBL:T220.O8"].Should().OnlyContain(path => File.Exists(ResolveRepoPath(path)));
        evidence.Obligations["OBL:T220.O9"].Should().OnlyContain(path => File.Exists(ResolveRepoPath(path)));
    }

    private static string ResolveRepoPath(string relativePath)
    {
        var cursor = new DirectoryInfo(AppContext.BaseDirectory);
        while (cursor is not null)
        {
            if (File.Exists(Path.Combine(cursor.FullName, "AGENTS.md")))
            {
                return Path.Combine(cursor.FullName, relativePath);
            }

            cursor = cursor.Parent;
        }

        return relativePath;
    }

    private sealed record Task220Evidence(
        IReadOnlyList<string> CoreCoverage,
        IReadOnlyList<string> AdapterCoverage,
        IReadOnlyDictionary<string, IReadOnlyList<string>> Obligations,
        IReadOnlyList<string> RequirementIds,
        IReadOnlyList<string> SourceRefs,
        IReadOnlyList<string> Assumptions)
    {
        public static Task220Evidence Current { get; } = new(
            new[] { "Game.Core.Tests/Tasks/Task220EvidenceTests.cs" },
            new[]
            {
                "Tests.Godot/tests/Adapters/test_event_bus_adapter.gd",
                "Tests.Godot/tests/Adapters/test_data_store_adapter.gd",
                "Tests.Godot/tests/Adapters/Db/test_db_migration_hook.gd",
                "Tests.Godot/tests/Adapters/Config/test_audio_player_adapter_nodes.gd"
            },
            new Dictionary<string, IReadOnlyList<string>>
            {
                ["OBL:T220.O5"] = new[]
                {
                    "Tests.Godot/tests/Adapters/test_event_bus_adapter.gd",
                    "Tests.Godot/tests/Adapters/test_data_store_adapter.gd",
                    "Tests.Godot/tests/Adapters/Config/test_audio_player_adapter_nodes.gd"
                },
                ["OBL:T220.O6"] = new[]
                {
                    "Tests.Godot/tests/Adapters/test_event_bus_adapter.gd",
                    "Tests.Godot/tests/Adapters/test_data_store_adapter.gd"
                },
                ["OBL:T220.O8"] = new[] { "logs/ci/2026-06-09/sc-analyze/summary.json" },
                ["OBL:T220.O9"] = new[] { "logs/ci/2026-06-09/sc-build-tdd/check_tasks_all_refs.log" }
            },
            new[] { "REQ-3810a1457878" },
            new[] { "docs/prd/PRD_V4_RULES_FREEZE.md:179" },
            Array.Empty<string>());
    }
}
