using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Security;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task72AuditFallbackRotationTests
{
    private const string PrimarySinkPath = "res://logs/security/security-audit.jsonl";
    private const string FallbackSinkPath = "user://logs/security/security-audit.jsonl";
    private const int RotationCapFiles = 3;
    private const int BoundedTotalSizeBytes = 4096;

    // ACC:T72.1
    [Fact]
    [Trait("acceptance", "ACC:T72.1")]
    public void ShouldAttemptFallbackWriteAndContinueRuntime_WhenPrimaryAuditWriteFails()
    {
        var writeAttempts = new List<string>();
        var warnings = new List<string>();

        var act = () =>
        {
            var writeOk = SecurityAuditFallbackPolicy.TryWriteWithFallback(
                primarySinkPath: PrimarySinkPath,
                fallbackSinkPath: FallbackSinkPath,
                tryWrite: path =>
                {
                    writeAttempts.Add(path);
                    return string.Equals(path, FallbackSinkPath, StringComparison.Ordinal);
                },
                warningSink: warnings.Add);

            writeOk.Should().BeTrue("a fallback write to user:// should keep runtime alive after primary failure");
        };

        act.Should().NotThrow("audit fallback must not abort runtime flow");
        writeAttempts.Should().Equal(PrimarySinkPath, FallbackSinkPath);
        warnings.Should().Contain(message => message.Contains("fallback", StringComparison.OrdinalIgnoreCase));
    }

    // ACC:T72.2
    [Fact]
    [Trait("acceptance", "ACC:T72.2")]
    public void ShouldRotateFallbackWritesUnderFixedCap_WhenPrimaryAuditWriteKeepsFailing()
    {
        var retainedFallbackPayloads = new List<string>();

        for (var sequence = 0; sequence < 7; sequence++)
        {
            var payload = BuildAuditPayload(sequence);

            var writeOk = SecurityAuditFallbackPolicy.TryWriteWithFallback(
                primarySinkPath: PrimarySinkPath,
                fallbackSinkPath: FallbackSinkPath,
                tryWrite: path =>
                {
                    if (string.Equals(path, PrimarySinkPath, StringComparison.Ordinal))
                    {
                        return false;
                    }

                    retainedFallbackPayloads.Add(payload);
                    SecurityAuditFallbackPolicy.EnforceRotationCapAndBoundedTotalSize(
                        retainedFallbackPayloads,
                        RotationCapFiles,
                        BoundedTotalSizeBytes);
                    return true;
                });

            writeOk.Should().BeTrue();
        }

        retainedFallbackPayloads.Count.Should().BeLessOrEqualTo(
            RotationCapFiles,
            "fixed-cap fallback rotation should prevent unbounded growth even under repeated primary failures");

        retainedFallbackPayloads
            .Select(ParseSequence)
            .Should()
            .Equal(new[] { 4, 5, 6 }, "oldest fallback payloads should be rotated out under the fixed cap");
    }

    private static string BuildAuditPayload(int sequence)
    {
        return $"{{\"seq\":{sequence},\"action\":\"core.audit.logged\",\"reason\":\"primary_failover\"}}";
    }

    private static int ParseSequence(string payload)
    {
        using var doc = JsonDocument.Parse(payload);
        return doc.RootElement.GetProperty("seq").GetInt32();
    }
}
