using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using FluentAssertions;
using Game.Core.Contracts;
using Xunit;

namespace Game.Core.Tests.Services;

public sealed class DiagnosticRetentionWindowTests
{
    // ACC:T114.1
    [Fact]
    [Trait("acceptance", "ACC:T114.1")]
    public void ShouldRemoveOutOfWindowDiagnosticsAndKeepRetainedSetBounded_WhenCleanupRunsAtSettlement()
    {
        var settlementUtc = new DateTime(2026, 1, 10, 12, 0, 0, DateTimeKind.Utc);
        var retentionWindow = TimeSpan.FromDays(3);
        const int maxRetainedRuns = 3;

        var diagnostics = new[]
        {
            CreateDiagnostic("run-001", settlementUtc.AddDays(-10)),
            CreateDiagnostic("run-002", settlementUtc.AddDays(-5)),
            CreateDiagnostic("run-003", settlementUtc.AddDays(-2)),
            CreateDiagnostic("run-004", settlementUtc.AddDays(-1).AddHours(-2)),
            CreateDiagnostic("run-005", settlementUtc.AddHours(-6)),
            CreateDiagnostic("run-006", settlementUtc.AddHours(-1)),
        };

        var first = CleanupDiagnostics(diagnostics, settlementUtc, retentionWindow, maxRetainedRuns);
        var second = CleanupDiagnostics(diagnostics, settlementUtc, retentionWindow, maxRetainedRuns);

        first.Select(x => x.Id).Should().Equal(
            second.Select(x => x.Id),
            "cleanup must be deterministic for the same diagnostics and configuration");

        first.Should().HaveCount(maxRetainedRuns, "retained diagnostics must stay bounded");
        first.Should().OnlyContain(x => x.Timestamp >= settlementUtc - retentionWindow,
            "diagnostics outside the retention window must be removed");

        first.Select(x => x.Id).Should().BeEquivalentTo(new[] { "run-004", "run-005", "run-006" },
            "retention should keep the latest bounded runs after cleanup");
    }

    private static IReadOnlyList<DomainEvent> CleanupDiagnostics(
        IReadOnlyList<DomainEvent> diagnostics,
        DateTime settlementUtc,
        TimeSpan retentionWindow,
        int maxRetainedRuns)
    {
        var policyType = Type.GetType("Game.Core.Services.DiagnosticRetentionWindow, Game.Core");
        if (policyType is null)
        {
            return diagnostics.ToArray();
        }

        var cleanupMethod = policyType.GetMethod(
            "Cleanup",
            BindingFlags.Public | BindingFlags.Static,
            binder: null,
            types: new[] { typeof(IReadOnlyList<DomainEvent>), typeof(DateTime), typeof(TimeSpan), typeof(int) },
            modifiers: null);

        if (cleanupMethod is null)
        {
            return diagnostics.ToArray();
        }

        var value = cleanupMethod.Invoke(null, new object[] { diagnostics, settlementUtc, retentionWindow, maxRetainedRuns });
        if (value is IEnumerable<DomainEvent> cleaned)
        {
            return cleaned.ToArray();
        }

        return diagnostics.ToArray();
    }

    private static DomainEvent CreateDiagnostic(string runId, DateTime timestampUtc)
        => new(
            Type: "core.traceability.checked",
            Source: "core.tests.t114",
            Data: new DiagnosticEventData(runId),
            Timestamp: timestampUtc,
            Id: runId);

    private sealed record DiagnosticEventData(string RunId) : IEventData;
}
