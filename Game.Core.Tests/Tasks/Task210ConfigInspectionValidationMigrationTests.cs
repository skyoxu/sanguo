using System;
using System.Collections.Generic;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task210ConfigInspectionValidationMigrationTests
{
    private const string TaskEvidenceRef = "Game.Core.Tests/Tasks/Task210ConfigInspectionValidationMigrationTests.cs";

    // ACC:T210.1 ACC:T210.2 ACC:T210.3 ACC:T210.4 ACC:T210.5 ACC:T210.7 ACC:T210.8 ACC:T210.11 ACC:T210.13 ACC:T210.14
    [Fact]
    [Trait("acceptance", "ACC:T210.config-inspection-report")]
    public void ShouldReportConfigInspectionState_WhenValidationMigrationGovernanceAndMetadataArePresent()
    {
        var service = new ConfigInspectionReportService();
        var generator = new MigrationCompatibilityReportGenerator();
        var migrationReport = generator.Generate(
            assertions: new[] { "config-inspection-state" },
            gates: new[] { "validation-gates" },
            scenarioEvidence: new[] { "migration-compatibility" },
            deterministicTestEvidence: new[] { TaskEvidenceRef });
        var migrationCompatibility = MigrationCompatibilityCompletenessValidator.Validate(
            migrationReport,
            evidenceLinks: new[] { TaskEvidenceRef },
            taskSpecificEvidenceRef: TaskEvidenceRef);

        var generatedAtUtc = new DateTime(2026, 6, 12, 0, 0, 0, DateTimeKind.Utc);

        var report = service.Inspect(
            runtimeBefore: RuntimeSnapshot(),
            activeConfig: ValidConfig(),
            governanceMetadata: GovernanceEvidence(),
            migrationCompatibility: migrationCompatibility,
            reportMetadata: new ReportMetadata(
                ReportId: "task-210-config-inspection",
                GeneratedBy: "chapter6",
                GeneratedAtUtc: generatedAtUtc));

        report.CanShip.Should().BeTrue();
        report.ActiveConfigValues.Should().ContainKeys("map_id", "players_count", "difficulty");
        report.ValidationStatus.Should().Be("valid");
        report.FailureCodes.Should().BeEmpty();
        report.GovernanceMetadata.AdrRefs.Should().Contain(new[] { "ADR-0005", "ADR-0011" });
        report.GovernanceMetadata.OverlayRefs.Should().Contain(new[]
        {
            "docs/architecture/overlays/PRD-SANGUO-T2/08/08-governance-build-release-quality-gates.md",
            "docs/architecture/overlays/PRD-SANGUO-V3/08/08-governance-logging-policy-and-lint.md",
            "docs/architecture/overlays/PRD-SANGUO-V3/08/08-governance-migration-compatibility.md",
            "docs/architecture/overlays/PRD-SANGUO-T2/08/08-t50-game-start-config.md",
        });
        report.MigrationCompatibilityState.IsCompatible.Should().BeTrue();
        report.MigrationCompatibilityState.FailureOutput.Should().Be("ok");
        report.ReportMetadata.ReportId.Should().Be("task-210-config-inspection");
        report.ReportMetadata.GeneratedBy.Should().Be("chapter6");
        report.ReportMetadata.GeneratedAtUtc.Should().Be(generatedAtUtc);
    }

    // ACC:T210.6 ACC:T210.9 ACC:T210.10 ACC:T210.12
    [Theory]
    [InlineData(ConfigFailureKind.Invalid, "validation_failed")]
    [InlineData(ConfigFailureKind.Missing, "config_missing")]
    [InlineData(ConfigFailureKind.MigrationIncompatible, "migration_incompatible")]
    public void ShouldReportValidationFailureAndPreserveRuntimeState_WhenConfigCannotShip(
        ConfigFailureKind failureKind,
        string expectedFailureCode)
    {
        var service = new ConfigInspectionReportService();
        var runtimeBefore = RuntimeSnapshot();

        var report = service.Inspect(
            runtimeBefore: runtimeBefore,
            activeConfig: ConfigFor(failureKind),
            governanceMetadata: GovernanceEvidence(),
            migrationCompatibility: MigrationCompatibilityFor(failureKind),
            reportMetadata: new ReportMetadata(
                ReportId: $"task-210-{failureKind}",
                GeneratedBy: "chapter6",
                GeneratedAtUtc: new DateTime(2026, 6, 12, 0, 0, 0, DateTimeKind.Utc)));

        report.CanShip.Should().BeFalse();
        report.ValidationStatus.Should().Be("failed");
        report.FailureCodes.Should().Contain(expectedFailureCode);
        report.RuntimeAfter.Should().BeEquivalentTo(runtimeBefore);
        report.RuntimeAfter.ActiveConfigValues.Should().BeEquivalentTo(runtimeBefore.ActiveConfigValues);
    }

    public enum ConfigFailureKind
    {
        Invalid,
        Missing,
        MigrationIncompatible,
    }

    private static GameStartConfig? ConfigFor(ConfigFailureKind failureKind)
        => failureKind switch
        {
            ConfigFailureKind.Invalid => ValidConfig() with { PlayersCount = 9 },
            ConfigFailureKind.Missing => null,
            ConfigFailureKind.MigrationIncompatible => ValidConfig(),
            _ => throw new ArgumentOutOfRangeException(nameof(failureKind), failureKind, null),
        };

    private static MigrationCompatibilityCompletenessValidationResult MigrationCompatibilityFor(ConfigFailureKind failureKind)
    {
        if (failureKind == ConfigFailureKind.MigrationIncompatible)
        {
            var incompleteReport = new MigrationCompatibilityReport(new[] { "Assertions", "DeterministicTests" });
            return MigrationCompatibilityCompletenessValidator.Validate(
                incompleteReport,
                evidenceLinks: Array.Empty<string>(),
                taskSpecificEvidenceRef: TaskEvidenceRef);
        }

        var completeReport = new MigrationCompatibilityReport(new[] { "Assertions", "Gates", "ScenarioEvidence", "DeterministicTests" });
        return MigrationCompatibilityCompletenessValidator.Validate(
            completeReport,
            evidenceLinks: new[] { TaskEvidenceRef },
            taskSpecificEvidenceRef: TaskEvidenceRef);
    }

    private static GameStartConfig ValidConfig()
        => new(
            MapId: "sanguo-default",
            PlayersCount: 4,
            StartingMoneyPreset: 10000,
            GlobalEventIntervalTurns: 10,
            RandomSeed: 210,
            CharacterAssignments: new Dictionary<string, string>(StringComparer.Ordinal)
            {
                ["p1"] = "c_liu_bei",
                ["p2"] = "c_cao_cao",
                ["p3"] = "c_sun_quan",
                ["p4"] = "c_zhuge_liang",
            });

    private static RuntimeConfigSnapshot RuntimeSnapshot()
        => new(
            StateId: "state-before",
            ActiveConfigValues: new Dictionary<string, string>(StringComparer.Ordinal)
            {
                ["map_id"] = "sanguo-default",
                ["players_count"] = "4",
                ["difficulty"] = "normal",
            });

    private static GovernanceMetadata GovernanceEvidence()
        => new(
            AdrRefs: new[] { "ADR-0005", "ADR-0011" },
            OverlayRefs: new[]
            {
                "docs/architecture/overlays/PRD-SANGUO-T2/08/08-governance-build-release-quality-gates.md",
                "docs/architecture/overlays/PRD-SANGUO-V3/08/08-governance-logging-policy-and-lint.md",
                "docs/architecture/overlays/PRD-SANGUO-V3/08/08-governance-migration-compatibility.md",
                "docs/architecture/overlays/PRD-SANGUO-T2/08/08-t50-game-start-config.md",
            });
}
