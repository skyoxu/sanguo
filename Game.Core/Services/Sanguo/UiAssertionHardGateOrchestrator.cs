using System;
using System.Collections.Generic;
using System.Linq;

namespace Game.Core.Services.Sanguo;

/// <summary>
/// Task 152 hard-gate orchestration entrypoint for UI explainability and i18n exposure assertions.
/// </summary>
public static class UiAssertionHardGateOrchestrator
{
    public const string ExplainabilityAccId = "A-011";
    public const string I18nExposureAccId = "A-012";

    public static UiAssertionHardGateSummary BuildSummary(UiAssertionHardGateFixture fixture)
    {
        ArgumentNullException.ThrowIfNull(fixture);

        return new UiAssertionHardGateSummary(
            HasExplainabilityAssertions: fixture.HasExplainabilityAssertions,
            HasI18nExposureAssertions: fixture.HasI18nExposureAssertions);
    }

    public static UiAssertionHardGateResult Evaluate(UiAssertionHardGateFixture fixture)
    {
        ArgumentNullException.ThrowIfNull(fixture);
        return Evaluate(BuildSummary(fixture));
    }

    public static UiAssertionHardGateResult Evaluate(UiAssertionHardGateSummary summary)
    {
        var failingAccIds = new List<string>();
        if (!summary.HasExplainabilityAssertions)
        {
            failingAccIds.Add(ExplainabilityAccId);
        }

        if (!summary.HasI18nExposureAssertions)
        {
            failingAccIds.Add(I18nExposureAccId);
        }

        var runResult = UiAssertionGateRunner.RunWithForcedFailures(failingAccIds);
        var diagnostics = runResult.Records
            .Where(record => string.Equals(record.State, UiAssertionGateRunner.StateFail, StringComparison.Ordinal))
            .Select(record => $"UI hard gate failed: {record.AccId}. Action: add deterministic UI assertion coverage for {record.CheckName}.")
            .ToArray();

        var executedAccIds = runResult.Records
            .Select(record => record.AccId)
            .Distinct(StringComparer.Ordinal)
            .OrderBy(accId => accId, StringComparer.Ordinal)
            .ToArray();

        return new UiAssertionHardGateResult(
            IsPassed: runResult.ExitCode == 0,
            ExitCode: runResult.ExitCode,
            Status: runResult.Status,
            ExecutedAccIds: executedAccIds,
            FailingAccIds: failingAccIds.ToArray(),
            Diagnostics: diagnostics,
            MachineReadableSummaryJson: runResult.MachineReadableSummaryJson);
    }
}

public sealed record UiAssertionHardGateFixture(
    string FixtureId,
    bool HasExplainabilityAssertions,
    bool HasI18nExposureAssertions,
    string RawLog);

public sealed record UiAssertionHardGateSummary(
    bool HasExplainabilityAssertions,
    bool HasI18nExposureAssertions);

public sealed record UiAssertionHardGateResult(
    bool IsPassed,
    int ExitCode,
    string Status,
    IReadOnlyList<string> ExecutedAccIds,
    IReadOnlyList<string> FailingAccIds,
    IReadOnlyList<string> Diagnostics,
    string MachineReadableSummaryJson);
