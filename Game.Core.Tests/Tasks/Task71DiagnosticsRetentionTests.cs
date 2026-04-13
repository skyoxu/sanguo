using System;
using System.Collections.Generic;
using System.Linq;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task71DiagnosticsRetentionTests
{
    // ACC:T71.1
    [Fact]
    [Trait("acceptance", "ACC:T71.1")]
    public void ShouldPreserveTask113DesensitizationBehavior_WhenReleasePayloadIsProcessed()
    {
        var rawPayload = new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["authToken"] = "token-abc-123",
            ["stackTrace"] = "NullReferenceException at line 42",
            ["eventType"] = "core.traceability.checked",
        };

        var sanitizedPayload = DiagnosticPayloadDesensitizationPolicy.Apply("release", rawPayload);

        sanitizedPayload["authToken"].Should().MatchRegex(@"^\[masked:[0-9a-f]{12}\]$");
        sanitizedPayload["stackTrace"].Should().MatchRegex(@"^\[masked:[0-9a-f]{12}\]$");
        sanitizedPayload["authToken"].Should().NotContain("token-abc-123");
        sanitizedPayload["stackTrace"].Should().NotContain("NullReferenceException");
        sanitizedPayload["eventType"].Should().Be(rawPayload["eventType"]);
    }

    // ACC:T71.2
    [Fact]
    [Trait("acceptance", "ACC:T71.2")]
    public void ShouldPreserveTask114RetentionBehavior_WhenCleanupRunsOnMixedWindowDiagnostics()
    {
        var settlementUtc = new DateTime(2026, 1, 10, 12, 0, 0, DateTimeKind.Utc);
        var retentionWindow = TimeSpan.FromDays(3);

        var expired = CreateReleaseDiagnostic("run-expired", settlementUtc.AddDays(-5), "token-expired");
        var inWindowA = CreateReleaseDiagnostic("run-keep-a", settlementUtc.AddDays(-2), "token-keep-a");
        var inWindowB = CreateReleaseDiagnostic("run-keep-b", settlementUtc.AddHours(-6), "token-keep-b");
        var diagnostics = new List<DomainEvent> { expired, inWindowA, inWindowB };

        var cleaned = DiagnosticRetentionWindow.Cleanup(diagnostics, settlementUtc, retentionWindow, maxRetainedRuns: 10);

        cleaned.Should().Equal(inWindowA, inWindowB);
        ExtractPayload(cleaned[0])["authToken"].Should().Be(ExtractPayload(inWindowA)["authToken"]);
        ExtractPayload(cleaned[1])["authToken"].Should().Be(ExtractPayload(inWindowB)["authToken"]);
    }

    [Fact]
    public void ShouldNotRetainExpiredDiagnostics_WhenCleanupRuns()
    {
        var settlementUtc = new DateTime(2026, 1, 10, 12, 0, 0, DateTimeKind.Utc);
        var retentionWindow = TimeSpan.FromDays(1);

        var expired = CreateReleaseDiagnostic("run-expired", settlementUtc.AddDays(-2), "token-expired");
        var inWindow = CreateReleaseDiagnostic("run-in-window", settlementUtc.AddHours(-2), "token-in-window");
        var diagnostics = new List<DomainEvent> { expired, inWindow };

        var cleaned = DiagnosticRetentionWindow.Cleanup(diagnostics, settlementUtc, retentionWindow, maxRetainedRuns: 10);

        cleaned.Select(x => x.Id).Should().NotContain(expired.Id);
        cleaned.Select(x => x.Id).Should().ContainSingle().Which.Should().Be(inWindow.Id);
    }

    [Fact]
    public void ShouldReturnStableTimeOrderedDiagnostics_WhenCleanupRunsOnInWindowDiagnostics()
    {
        var settlementUtc = new DateTime(2026, 1, 10, 12, 0, 0, DateTimeKind.Utc);
        var retentionWindow = TimeSpan.FromDays(3);

        var newer = CreateReleaseDiagnostic("run-newer", settlementUtc.AddHours(-1), "token-newer");
        var older = CreateReleaseDiagnostic("run-older", settlementUtc.AddHours(-3), "token-older");
        var diagnostics = new List<DomainEvent> { newer, older };

        var cleaned = DiagnosticRetentionWindow.Cleanup(diagnostics, settlementUtc, retentionWindow, maxRetainedRuns: 10);
        var cleanedAgain = DiagnosticRetentionWindow.Cleanup(diagnostics, settlementUtc, retentionWindow, maxRetainedRuns: 10);

        cleaned.Select(x => x.Id).Should().Equal(
            new[] { older.Id, newer.Id },
            "integration cleanup should keep a stable deterministic order for in-window diagnostics");
        cleanedAgain.Select(x => x.Id).Should().Equal(
            cleaned.Select(x => x.Id),
            "cleanup should stay deterministic across repeated runs with the same inputs");
    }

    private static DomainEvent CreateReleaseDiagnostic(string runId, DateTime timestampUtc, string rawToken)
    {
        var rawPayload = new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["authToken"] = rawToken,
            ["eventType"] = "core.traceability.checked",
        };

        var sanitizedPayload = DiagnosticPayloadDesensitizationPolicy.Apply("release", rawPayload);

        return new DomainEvent(
            Type: "core.traceability.checked",
            Source: "core.tests.task71",
            Data: new DiagnosticPayload(sanitizedPayload),
            Timestamp: timestampUtc,
            Id: runId);
    }

    private static IReadOnlyDictionary<string, string> ExtractPayload(DomainEvent diagnostic)
    {
        diagnostic.Data.Should().BeOfType<DiagnosticPayload>();
        return ((DiagnosticPayload)diagnostic.Data!).Payload;
    }

    private sealed record DiagnosticPayload(IReadOnlyDictionary<string, string> Payload) : IEventData;
}
