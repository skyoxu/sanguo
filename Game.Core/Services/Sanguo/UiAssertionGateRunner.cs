using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

namespace Game.Core.Services.Sanguo;

/// <summary>
/// Task 92 split runner for A-008~A-012 UI assertions.
/// Exposes deterministic gate-unit metadata and a machine-readable summary.
/// </summary>
public static class UiAssertionGateRunner
{
    public const string StatePass = "pass";
    public const string StateFail = "fail";

    private static readonly UiAssertionGateUnit[] RequiredGateUnits =
    {
        new("A-008", "A-008.PopupLogAtomicCommit", "PopupLogAtomicCommit", true),
        new("A-009", "A-009.PopupOverloadSummary", "PopupOverloadSummary", true),
        new("A-010", "A-010.HudFixedWindowLazyLoad", "HudFixedWindowLazyLoad", true),
        new("A-011", "A-011.ReleaseI18nFallback", "ReleaseI18nFallback", true),
        new("A-012", "A-012.DevRawKeyDiagnostics", "DevRawKeyDiagnostics", true),
    };

    public static IReadOnlyList<UiAssertionGateUnit> GetRequiredGateUnits()
    {
        return RequiredGateUnits;
    }

    public static UiAssertionGateRunResult RunWithForcedFailures(IEnumerable<string> failingAccIds)
    {
        ArgumentNullException.ThrowIfNull(failingAccIds);

        var forcedFailSet = new HashSet<string>(
            failingAccIds
                .Where(static id => !string.IsNullOrWhiteSpace(id))
                .Select(static id => id.Trim()),
            StringComparer.Ordinal);

        var records = RequiredGateUnits
            .Select(unit =>
            {
                var forcedFail = forcedFailSet.Contains(unit.AccId);
                var state = forcedFail ? StateFail : StatePass;
                var message = forcedFail
                    ? $"Forced failure for required assertion {unit.AccId}."
                    : $"Required assertion {unit.AccId} passed in deterministic UI gate simulation.";

                return new UiAssertionGateRecord(
                    unit.AccId,
                    unit.StableId,
                    unit.CheckName,
                    state,
                    message,
                    unit.IsMandatory);
            })
            .ToArray();

        var hasMandatoryFailure = records.Any(record =>
            record.IsMandatory &&
            string.Equals(record.State, StateFail, StringComparison.OrdinalIgnoreCase));

        var status = hasMandatoryFailure ? "fail" : "ok";
        var exitCode = hasMandatoryFailure ? 1 : 0;
        var summaryJson = JsonSerializer.Serialize(new
        {
            status,
            exit_code = exitCode,
            records = records.Select(record => new
            {
                acc_id = record.AccId,
                stable_id = record.StableId,
                check = record.CheckName,
                state = record.State,
                message = record.Message,
                mandatory = record.IsMandatory,
            }),
        });

        return new UiAssertionGateRunResult(
            ExitCode: exitCode,
            Status: status,
            Records: records,
            MachineReadableSummaryJson: summaryJson);
    }
}

public sealed record UiAssertionGateUnit(
    string AccId,
    string StableId,
    string CheckName,
    bool IsMandatory);

public sealed record UiAssertionGateRecord(
    string AccId,
    string StableId,
    string CheckName,
    string State,
    string Message,
    bool IsMandatory);

public sealed record UiAssertionGateRunResult(
    int ExitCode,
    string Status,
    IReadOnlyList<UiAssertionGateRecord> Records,
    string MachineReadableSummaryJson);
