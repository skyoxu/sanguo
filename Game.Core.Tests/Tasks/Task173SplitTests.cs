using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task173SplitTests
{
    private static readonly string[] ExpectedTask173AccIds =
    {
        "A-013",
        "A-014",
        "A-015",
    };

    // ACC:T173.1
    [Fact]
    [Trait("acceptance", "ACC:T173.1")]
    public void ShouldExposeOnlyA013ToA015_WhenRunningTask173BundleScope()
    {
        var result = CoreAssertionGateRunner.RunReplayIntegrityBundle();

        var mandatoryAccIds = result.Records
            .Where(static record => record.IsMandatory)
            .Select(record => record.AccId)
            .Distinct(StringComparer.Ordinal)
            .OrderBy(static accId => accId, StringComparer.Ordinal)
            .ToArray();

        mandatoryAccIds.Should().Equal(
            ExpectedTask173AccIds,
            "Task 173 split bundle should expose only A-013 to A-015 instead of an opaque broader bundle.");
    }

    // ACC:T173.2
    [Fact]
    [Trait("acceptance", "ACC:T173.2")]
    public void ShouldReturnDeterministicReplayGateEvidence_WhenEvaluatingHashUntrustedAndMismatchChecks()
    {
        var firstEvidence = ReplayIntegrityIntegrationPack.BuildEvidence(
            new Task83ReplayIntegritySplitEvidence(
                HasDeterministicEvidence: true,
                CoversA013A014Semantics: true,
                SplitScopes: new[] { ReplayIntegrityIntegrationPack.SplitScopeT83 }),
            new Task84ReplayMismatchSplitEvidence(
                HasDeterministicEvidence: true,
                CoversA015Semantics: true,
                EntersDefinedMismatchModeOnTrustFailure: true,
                SplitScopes: new[] { ReplayIntegrityIntegrationPack.SplitScopeT84 }));

        var secondEvidence = ReplayIntegrityIntegrationPack.BuildEvidence(
            new Task83ReplayIntegritySplitEvidence(
                HasDeterministicEvidence: true,
                CoversA013A014Semantics: true,
                SplitScopes: new[] { ReplayIntegrityIntegrationPack.SplitScopeT83 }),
            new Task84ReplayMismatchSplitEvidence(
                HasDeterministicEvidence: true,
                CoversA015Semantics: true,
                EntersDefinedMismatchModeOnTrustFailure: true,
                SplitScopes: new[] { ReplayIntegrityIntegrationPack.SplitScopeT84 }));

        firstEvidence.Task83Delivered.Should().BeTrue();
        firstEvidence.Task84Delivered.Should().BeTrue();
        firstEvidence.IsClosureComplete.Should().BeTrue();
        firstEvidence.Task83Delivered.Should().BeTrue();
        firstEvidence.Task84Delivered.Should().BeTrue();
        firstEvidence.HasScope(ReplayIntegrityIntegrationPack.SplitScopeT83).Should().BeTrue();
        firstEvidence.HasScope(ReplayIntegrityIntegrationPack.SplitScopeT84).Should().BeTrue();
        firstEvidence.SplitScopes.Should().Equal(
            ReplayIntegrityIntegrationPack.SplitScopeT83,
            ReplayIntegrityIntegrationPack.SplitScopeT84);
        firstEvidence.Should().BeEquivalentTo(secondEvidence);
    }

    // ACC:T173.3
    [Fact]
    [Trait("acceptance", "ACC:T173.3")]
    public void ShouldProduceReusableDeterministicSummaries_WhenRunningTrustedAndUntrustedReplayFixtures()
    {
        var trustedFirst = CoreAssertionGateRunner.RunReplayIntegrityBundle(CoreAssertionGateExecutionInputs.AllPassing);
        var trustedSecond = CoreAssertionGateRunner.RunReplayIntegrityBundle(CoreAssertionGateExecutionInputs.AllPassing);

        var untrustedInputs = CoreAssertionGateExecutionInputs.AllPassing with
        {
            HasSaveUntrustedEvidence = false,
        };

        var untrustedFirst = CoreAssertionGateRunner.RunReplayIntegrityBundle(untrustedInputs);
        var untrustedSecond = CoreAssertionGateRunner.RunReplayIntegrityBundle(untrustedInputs);

        trustedFirst.ExitCode.Should().Be(0);
        trustedFirst.MachineReadableSummaryJson.Should().Be(trustedSecond.MachineReadableSummaryJson);

        untrustedFirst.ExitCode.Should().NotBe(0);
        untrustedFirst.MachineReadableSummaryJson.Should().Be(untrustedSecond.MachineReadableSummaryJson);

        var untrustedRecords = ReadSummaryRecords(untrustedFirst.MachineReadableSummaryJson);
        untrustedRecords.Should().Contain(record =>
            string.Equals(record.GetProperty("acc_id").GetString(), "A-014", StringComparison.Ordinal) &&
            string.Equals(record.GetProperty("state").GetString(), CoreAssertionGateRunner.StateFail, StringComparison.Ordinal));
        untrustedRecords.Should().Contain(record =>
            string.Equals(record.GetProperty("acc_id").GetString(), "A-015", StringComparison.Ordinal) &&
            string.Equals(record.GetProperty("state").GetString(), CoreAssertionGateRunner.StatePass, StringComparison.Ordinal),
            "A-015 mismatch policy should stay mode-stable when only save_untrusted evidence is disabled.");
    }

    // ACC:T173.4
    [Fact]
    [Trait("acceptance", "ACC:T173.4")]
    public void ShouldReturnNonZeroExitAndActionableSummary_WhenReplayPolicyCheckFailsByMode()
    {
        const string expectedMode = "mismatch";

        var failingInputs = CoreAssertionGateExecutionInputs.AllPassing with
        {
            HasMismatchModeEvidence = false,
        };

        var result = CoreAssertionGateRunner.RunReplayIntegrityBundle(failingInputs);
        var records = ReadSummaryRecords(result.MachineReadableSummaryJson);

        result.ExitCode.Should().NotBe(0);
        result.Status.Should().Be("fail");

        records.Should().Contain(record =>
            string.Equals(record.GetProperty("acc_id").GetString(), "A-015", StringComparison.Ordinal) &&
            string.Equals(record.GetProperty("state").GetString(), CoreAssertionGateRunner.StateFail, StringComparison.Ordinal) &&
            record.GetProperty("mandatory").GetBoolean() &&
            !string.IsNullOrWhiteSpace(record.GetProperty("stable_id").GetString()) &&
            !string.IsNullOrWhiteSpace(record.GetProperty("check").GetString()) &&
            (record.GetProperty("message").GetString() ?? string.Empty).Contains("Mismatch-mode", StringComparison.Ordinal) &&
            string.Equals(expectedMode, "mismatch", StringComparison.Ordinal));
    }

    // ACC:T173.5
    [Fact]
    [Trait("acceptance", "ACC:T173.5")]
    public void ShouldKeepAcceptanceAlignmentAndSummaryContract_WhenReportingTask173Bundle()
    {
        var result = CoreAssertionGateRunner.RunReplayIntegrityBundleWithForcedFailures(new[] { "A-013", "A-015" });
        var records = ReadSummaryRecords(result.MachineReadableSummaryJson);

        var task173Records = records
            .Where(record => ExpectedTask173AccIds.Contains(record.GetProperty("acc_id").GetString() ?? string.Empty, StringComparer.Ordinal))
            .ToArray();

        task173Records.Should().HaveCount(3);

        var recordedAccIds = task173Records
            .Select(record => record.GetProperty("acc_id").GetString() ?? string.Empty)
            .OrderBy(static accId => accId, StringComparer.Ordinal)
            .ToArray();

        recordedAccIds.Should().Equal(ExpectedTask173AccIds);

        foreach (var record in task173Records)
        {
            var accId = record.GetProperty("acc_id").GetString() ?? string.Empty;
            var stableId = record.GetProperty("stable_id").GetString() ?? string.Empty;
            var checkName = record.GetProperty("check").GetString() ?? string.Empty;
            var state = record.GetProperty("state").GetString() ?? string.Empty;

            stableId.Should().StartWith(accId + ".", "stable id should stay aligned with acceptance id");
            checkName.Should().NotBeNullOrWhiteSpace();
            state.Should().Match(s =>
                string.Equals(s, CoreAssertionGateRunner.StatePass, StringComparison.Ordinal) ||
                string.Equals(s, CoreAssertionGateRunner.StateFail, StringComparison.Ordinal) ||
                string.Equals(s, CoreAssertionGateRunner.StateSkipped, StringComparison.Ordinal));
        }
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
