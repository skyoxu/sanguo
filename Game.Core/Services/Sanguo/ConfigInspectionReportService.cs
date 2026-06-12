using System;
using System.Collections.Generic;
using System.Linq;
using Game.Core.Contracts.Sanguo;

namespace Game.Core.Services.Sanguo;

public sealed class ConfigInspectionReportService
{
    public ConfigInspectionReport Inspect(
        RuntimeConfigSnapshot runtimeBefore,
        GameStartConfig? activeConfig,
        GovernanceMetadata governanceMetadata,
        MigrationCompatibilityCompletenessValidationResult migrationCompatibility,
        ReportMetadata reportMetadata)
    {
        ArgumentNullException.ThrowIfNull(runtimeBefore);
        ArgumentNullException.ThrowIfNull(governanceMetadata);
        ArgumentNullException.ThrowIfNull(migrationCompatibility);
        ArgumentNullException.ThrowIfNull(reportMetadata);

        var failureCodes = new List<string>();
        IReadOnlyDictionary<string, string> activeConfigValues = new Dictionary<string, string>(StringComparer.Ordinal);

        if (activeConfig is null)
        {
            failureCodes.Add("config_missing");
        }
        else
        {
            activeConfigValues = ToConfigValues(activeConfig);
            if (!GameStartConfigValidator.TryValidate(activeConfig, out var validationErrors))
            {
                failureCodes.Add("validation_failed");
                failureCodes.AddRange(validationErrors.Select(error => $"config:{error}"));
            }
        }

        if (!migrationCompatibility.IsComplete)
        {
            failureCodes.Add("migration_incompatible");
            failureCodes.AddRange(migrationCompatibility.FailureCodes.Select(code => $"migration:{code}"));
        }

        var orderedFailureCodes = failureCodes
            .OrderBy(static code => code, StringComparer.Ordinal)
            .ToArray();
        var validationStatus = orderedFailureCodes.Length == 0 ? "valid" : "failed";

        return new ConfigInspectionReport(
            CanShip: orderedFailureCodes.Length == 0,
            ActiveConfigValues: activeConfigValues,
            ValidationStatus: validationStatus,
            FailureCodes: orderedFailureCodes,
            GovernanceMetadata: governanceMetadata,
            MigrationCompatibilityState: new MigrationCompatibilityState(
                IsCompatible: migrationCompatibility.IsComplete,
                FailureOutput: migrationCompatibility.FailureOutput),
            ReportMetadata: reportMetadata,
            RuntimeBefore: runtimeBefore,
            RuntimeAfter: runtimeBefore);
    }

    private static IReadOnlyDictionary<string, string> ToConfigValues(GameStartConfig config)
    {
        return new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["map_id"] = config.MapId,
            ["players_count"] = config.PlayersCount.ToString(System.Globalization.CultureInfo.InvariantCulture),
            ["starting_money_preset"] = config.StartingMoneyPreset.ToString(System.Globalization.CultureInfo.InvariantCulture),
            ["global_event_interval_turns"] = config.GlobalEventIntervalTurns.ToString(System.Globalization.CultureInfo.InvariantCulture),
            ["random_seed"] = config.RandomSeed.ToString(System.Globalization.CultureInfo.InvariantCulture),
            ["active_strategem_id"] = config.ActiveStrategemId,
            ["passive_strategem_id"] = config.PassiveStrategemId,
            ["run_mode"] = config.RunMode,
            ["commander_id"] = config.CommanderId,
            ["difficulty"] = config.Difficulty,
        };
    }
}

public sealed record ConfigInspectionReport(
    bool CanShip,
    IReadOnlyDictionary<string, string> ActiveConfigValues,
    string ValidationStatus,
    IReadOnlyList<string> FailureCodes,
    GovernanceMetadata GovernanceMetadata,
    MigrationCompatibilityState MigrationCompatibilityState,
    ReportMetadata ReportMetadata,
    RuntimeConfigSnapshot RuntimeBefore,
    RuntimeConfigSnapshot RuntimeAfter);

public sealed record RuntimeConfigSnapshot(
    string StateId,
    IReadOnlyDictionary<string, string> ActiveConfigValues);

public sealed record GovernanceMetadata(
    IReadOnlyCollection<string> AdrRefs,
    IReadOnlyCollection<string> OverlayRefs);

public sealed record MigrationCompatibilityState(
    bool IsCompatible,
    string FailureOutput);

public sealed record ReportMetadata(
    string ReportId,
    string GeneratedBy,
    DateTime GeneratedAtUtc);
