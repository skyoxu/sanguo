using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using FluentAssertions;
using Game.Core.Contracts;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task114V3Tests
{
    // ACC:T114.2
    [Fact]
    [Trait("acceptance", "ACC:T114.2")]
    public void ShouldKeepInWindowDiagnosticsUnchanged_WhenCleanupRunsWithExpiredDiagnosticsPresent()
    {
        var settlementUtc = new DateTime(2026, 1, 10, 12, 0, 0, DateTimeKind.Utc);
        var retentionWindow = TimeSpan.FromDays(3);
        const int maxRetainedRuns = 10;

        var expiredDiagnostic = CreateDiagnostic("run-expired", settlementUtc.AddDays(-4));
        var inWindowDiagnosticA = CreateDiagnostic("run-keep-a", settlementUtc.AddDays(-2));
        var inWindowDiagnosticB = CreateDiagnostic("run-keep-b", settlementUtc.AddHours(-3));

        var diagnostics = new List<DomainEvent>
        {
            expiredDiagnostic,
            inWindowDiagnosticA,
            inWindowDiagnosticB,
        };

        var cleaned = InvokeCleanup(diagnostics, settlementUtc, retentionWindow, maxRetainedRuns);

        cleaned.Should().HaveCount(2, "diagnostics outside the retention window should be removed");
        cleaned.Should().Equal(inWindowDiagnosticA, inWindowDiagnosticB);
        cleaned.Should().OnlyContain(x => x.Timestamp >= settlementUtc - retentionWindow);
    }

    // ACC:T114.3
    [Fact]
    [Trait("acceptance", "ACC:T114.3")]
    public void ShouldMakeDeterministicTriggerDecision_WhenInputsAndConfigurationAreIdentical()
    {
        var settlementUtc = new DateTime(2026, 1, 10, 12, 0, 0, DateTimeKind.Utc);
        var retentionWindow = TimeSpan.FromDays(7);
        const int maxRetainedRuns = 10;

        var diagnostics = new List<DomainEvent>
        {
            CreateDiagnostic("run-expired", settlementUtc.AddDays(-30)),
            CreateDiagnostic("run-keep-a", settlementUtc.AddDays(-2)),
            CreateDiagnostic("run-keep-b", settlementUtc.AddHours(-5)),
        };

        var first = InvokeCleanup(diagnostics, settlementUtc, retentionWindow, maxRetainedRuns);
        var second = InvokeCleanup(diagnostics, settlementUtc, retentionWindow, maxRetainedRuns);

        var firstTriggered = IsCleanupTriggered(diagnostics, first);
        var secondTriggered = IsCleanupTriggered(diagnostics, second);

        firstTriggered.Should().BeTrue("an expired diagnostic should trigger cleanup");
        secondTriggered.Should().Be(firstTriggered, "trigger decision must be deterministic for identical inputs");
        first.Select(x => x.Id).Should().Equal(second.Select(x => x.Id));
    }

    private static IReadOnlyList<DomainEvent> InvokeCleanup(
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
        return value is IEnumerable<DomainEvent> cleaned ? cleaned.ToArray() : diagnostics.ToArray();
    }

    private static bool IsCleanupTriggered(IReadOnlyList<DomainEvent> before, IReadOnlyList<DomainEvent> after)
    {
        if (before.Count != after.Count)
        {
            return true;
        }

        return !before.Select(x => x.Id).SequenceEqual(after.Select(x => x.Id));
    }

    private static DomainEvent CreateDiagnostic(string runId, DateTime timestampUtc)
        => new(
            Type: "core.traceability.checked",
            Source: "core.tests.t114.v3",
            Data: new DiagnosticPayload(runId),
            Timestamp: timestampUtc,
            Id: runId);

    private sealed record DiagnosticPayload(string RunId) : IEventData;
}
