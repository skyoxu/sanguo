using System;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task175SplitTests
{
    // ACC:T175.1
    [Fact]
    [Trait("acceptance", "ACC:T175.1")]
    public void ShouldReportAdditiveOnlyCompatibilityEvidence_WhenRunningCoreHardGateForA020()
    {
        var result = CoreAssertionGateRunner.Run();

        using var doc = JsonDocument.Parse(result.MachineReadableSummaryJson);
        var record = FindA020Record(doc.RootElement);
        var message = record.GetProperty("message").GetString();

        result.ExitCode.Should().Be(0);
        result.Status.Should().Be("ok");
        record.GetProperty("state").GetString().Should().Be(CoreAssertionGateRunner.StatePass);
        record.GetProperty("stable_id").GetString().Should().Be("A-020.ContractCompatibility");
        record.GetProperty("check").GetString().Should().Be("ContractCompatibilityPolicy");
        message.Should().NotBeNullOrWhiteSpace();
        message.Should().Contain("additive-only", "A-020 compatibility evidence must report the additive-only assertion result.");
        message.Should().Contain("R11", "A-020 compatibility evidence must identify the R11 contract rule it validates.");
    }

    private static JsonElement FindA020Record(JsonElement root)
    {
        foreach (var record in root.GetProperty("records").EnumerateArray())
        {
            if (string.Equals(record.GetProperty("acc_id").GetString(), "A-020", StringComparison.Ordinal))
            {
                return record.Clone();
            }
        }

        throw new InvalidOperationException("A-020 record was not emitted by the core assertion gate runner.");
    }
}
