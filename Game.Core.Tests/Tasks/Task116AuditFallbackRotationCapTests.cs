using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Security;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task116AuditFallbackRotationCapTests
{
    private const string PrimarySinkPath = "res://logs/security/security-audit.jsonl";
    private const string FallbackSinkPath = "user://logs/security/security-audit.jsonl";
    private const int RotationCapFiles = 3;
    private const int BoundedTotalSizeBytes = 240;

    // ACC:T116.1
    [Fact]
    [Trait("acceptance", "ACC:T116.1")]
    public void ShouldEnforceRotationCapAndBoundedTotalSize_WhenFallbackWritesRepeatUnderPrimaryFailure()
    {
        var retainedFallbackPayloads = new List<string>();
        var warnings = new List<string>();

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
                },
                warningSink: warnings.Add);

            writeOk.Should().BeTrue("fallback writes should keep runtime alive when primary sink fails");
        }

        var observedTotalBytes = retainedFallbackPayloads.Sum(static payload => Encoding.UTF8.GetByteCount(payload));

        warnings.Should().NotBeEmpty();
        warnings.Should().OnlyContain(message => message.Contains("fallback", StringComparison.OrdinalIgnoreCase));

        retainedFallbackPayloads.Count.Should().BeLessOrEqualTo(
            RotationCapFiles,
            "rotation cap should limit the number of retained fallback chunks");

        observedTotalBytes.Should().BeLessOrEqualTo(
            BoundedTotalSizeBytes,
            "bounded total size policy must prevent unbounded fallback growth");

        var retainedSequences = retainedFallbackPayloads
            .Select(ParseSequence)
            .ToList();
        retainedSequences.Should().BeInAscendingOrder("oldest-first trimming should keep a deterministic tail window");
        if (retainedSequences.Count > 0)
        {
            var expectedStart = 7 - retainedSequences.Count;
            retainedSequences.Should().Equal(
                Enumerable.Range(expectedStart, retainedSequences.Count),
                "oldest-first trimming should remove earliest sequences first");
        }
    }

    // ACC:T116.2
    [Fact]
    [Trait("acceptance", "ACC:T116.2")]
    public void ShouldKeepDeterministicWriteOrderEvidence_WhenFallbackPathIsUsed()
    {
        var observedOrder = new List<int>();

        for (var sequence = 0; sequence < 4; sequence++)
        {
            var currentSequence = sequence;
            var writeOk = SecurityAuditFallbackPolicy.TryWriteWithFallback(
                primarySinkPath: PrimarySinkPath,
                fallbackSinkPath: FallbackSinkPath,
                tryWrite: path =>
                {
                    if (string.Equals(path, PrimarySinkPath, StringComparison.Ordinal))
                    {
                        return false;
                    }

                    observedOrder.Add(currentSequence);
                    return true;
                });

            writeOk.Should().BeTrue();
        }

        observedOrder.Should().Equal(0, 1, 2, 3);
    }

    private static string BuildAuditPayload(int sequence)
    {
        return $"{{\"ts\":\"2026-01-10T12:00:00Z\",\"action\":\"core.audit.logged\",\"reason\":\"primary_fail\",\"target\":\"audit\",\"caller\":\"task116\",\"seq\":{sequence},\"pad\":\"{new string('x', 48)}\"}}";
    }

    private static int ParseSequence(string payload)
    {
        using var doc = JsonDocument.Parse(payload);
        return doc.RootElement.GetProperty("seq").GetInt32();
    }
}
