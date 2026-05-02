using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task174AuditFallbackRotationHardGateTests
{
    private static readonly string[] ExpectedAuditAccIds =
    {
        "A-018",
        "A-019",
    };

    // ACC:T174.1
    [Fact]
    [Trait("acceptance", "ACC:T174.1")]
    public void ShouldExposeOnlyAuditFallbackAndRotationAssertions_WhenRunningTask174HardGateBundle()
    {
        var result = CoreAssertionGateRunner.RunAuditFallbackRotationBundle();

        var mandatoryAccIds = result.Records
            .Where(static record => record.IsMandatory)
            .Select(record => record.AccId)
            .Distinct(StringComparer.Ordinal)
            .OrderBy(static accId => accId, StringComparer.Ordinal)
            .ToArray();

        mandatoryAccIds.Should().Equal(
            ExpectedAuditAccIds,
            "Task 174 hard-gate bundle should isolate audit fallback/rotation assertions from unrelated checks.");
    }

    [Fact]
    public void ShouldNotEmitUnrelatedAssertionIds_WhenRunningTask174HardGateBundleWithAuditFallbackFailure()
    {
        var result = CoreAssertionGateRunner.RunAuditFallbackRotationBundle(CoreAssertionGateExecutionInputs.AllPassing with
        {
            HasAuditFallbackEvidence = false,
        });

        var records = ReadSummaryRecords(result.MachineReadableSummaryJson);

        var unrelatedAccIds = records
            .Select(record => record.GetProperty("acc_id").GetString() ?? string.Empty)
            .Where(accId => !ExpectedAuditAccIds.Contains(accId, StringComparer.Ordinal))
            .Distinct(StringComparer.Ordinal)
            .OrderBy(static accId => accId, StringComparer.Ordinal)
            .ToArray();

        unrelatedAccIds.Should().BeEmpty(
            "Task 174 hard-gate bundle must not report assertions outside A-018 and A-019.");
    }

    // ACC:T174.2
    [Fact]
    public void ShouldReturnGateFailure_WhenAuditFallbackEvidenceIsDisabled()
    {
        var result = CoreAssertionGateRunner.RunAuditFallbackRotationBundle(CoreAssertionGateExecutionInputs.AllPassing with
        {
            HasAuditFallbackEvidence = false,
        });

        var records = ReadSummaryRecords(result.MachineReadableSummaryJson);
        var a018Record = records.Single(record =>
            string.Equals(record.GetProperty("acc_id").GetString(), "A-018", StringComparison.Ordinal));

        result.ExitCode.Should().Be(1);
        result.Status.Should().Be("fail");
        a018Record.GetProperty("state").GetString().Should().Be("fail");
    }

    // ACC:T174.2
    [Fact]
    public void ShouldReturnGateFailure_WhenAuditRotationCapEvidenceIsDisabled()
    {
        var result = CoreAssertionGateRunner.RunAuditFallbackRotationBundle(CoreAssertionGateExecutionInputs.AllPassing with
        {
            HasAuditRotationCapEvidence = false,
        });

        var records = ReadSummaryRecords(result.MachineReadableSummaryJson);
        var a019Record = records.Single(record =>
            string.Equals(record.GetProperty("acc_id").GetString(), "A-019", StringComparison.Ordinal));

        result.ExitCode.Should().Be(1);
        result.Status.Should().Be("fail");
        a019Record.GetProperty("state").GetString().Should().Be("fail");
    }

    private static JsonElement[] ReadSummaryRecords(string summaryJson)
    {
        using var doc = JsonDocument.Parse(summaryJson);
        var records = new List<JsonElement>();

        foreach (var record in doc.RootElement.GetProperty("records").EnumerateArray())
        {
            records.Add(record.Clone());
        }

        return records.ToArray();
    }
}
