using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task174DiagnosticPayloadRetentionHardGateTests
{
    private static readonly string[] ExpectedDiagnosticAccIds =
    {
        "A-016",
        "A-017",
    };

    // ACC:T174.1
    [Fact]
    [Trait("acceptance", "ACC:T174.1")]
    public void ShouldExposeOnlyDiagnosticPayloadAndRetentionAssertions_WhenRunningTask174HardGateBundle()
    {
        var result = CoreAssertionGateRunner.RunDiagnosticPayloadProtectionBundle();

        var mandatoryAccIds = result.Records
            .Where(static record => record.IsMandatory)
            .Select(record => record.AccId)
            .Distinct(StringComparer.Ordinal)
            .OrderBy(static accId => accId, StringComparer.Ordinal)
            .ToArray();

        mandatoryAccIds.Should().Equal(
            ExpectedDiagnosticAccIds,
            "Task 174 diagnostic hard-gate bundle should be scoped to A-016 and A-017 only.");
    }

    // ACC:T174.2
    [Fact]
    public void ShouldReportFailureForA016_WhenPayloadDesensitizationEvidenceIsDisabled()
    {
        var result = CoreAssertionGateRunner.RunDiagnosticPayloadProtectionBundle(CoreAssertionGateExecutionInputs.AllPassing with
        {
            HasPayloadDesensitizationEvidence = false,
        });

        var records = ReadSummaryRecords(result.MachineReadableSummaryJson);
        var a016Record = records.Single(record =>
            string.Equals(record.GetProperty("acc_id").GetString(), "A-016", StringComparison.Ordinal));

        result.ExitCode.Should().Be(1);
        result.Status.Should().Be("fail");
        a016Record.GetProperty("state").GetString().Should().Be("fail");
    }

    [Fact]
    public void ShouldReportFailureForA017_WhenRetentionWindowEvidenceIsDisabled()
    {
        var result = CoreAssertionGateRunner.RunDiagnosticPayloadProtectionBundle(CoreAssertionGateExecutionInputs.AllPassing with
        {
            HasRetentionWindowEvidence = false,
        });

        var records = ReadSummaryRecords(result.MachineReadableSummaryJson);
        var a017Record = records.Single(record =>
            string.Equals(record.GetProperty("acc_id").GetString(), "A-017", StringComparison.Ordinal));

        result.ExitCode.Should().Be(1);
        result.Status.Should().Be("fail");
        a017Record.GetProperty("state").GetString().Should().Be("fail");
    }

    [Fact]
    public void ShouldKeepMachineReadableSummaryDeterministic_WhenRunningWithSameInputsTwice()
    {
        var inputs = CoreAssertionGateExecutionInputs.AllPassing with
        {
            HasPayloadDesensitizationEvidence = false,
            HasRetentionWindowEvidence = true,
        };

        var firstResult = CoreAssertionGateRunner.RunDiagnosticPayloadProtectionBundle(inputs);
        var secondResult = CoreAssertionGateRunner.RunDiagnosticPayloadProtectionBundle(inputs);

        firstResult.ExitCode.Should().Be(secondResult.ExitCode);
        firstResult.Status.Should().Be(secondResult.Status);
        firstResult.MachineReadableSummaryJson.Should().Be(secondResult.MachineReadableSummaryJson);
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
