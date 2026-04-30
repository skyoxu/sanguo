using System;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task152UiHardGateTests
{
    // ACC:T152.1
    [Fact]
    public void ShouldPassHardGate_WhenExplainabilityAndI18nAssertionsArePresent()
    {
        var result = UiAssertionHardGateOrchestrator.Evaluate(new UiAssertionHardGateFixture(
            FixtureId: "ui-pass",
            HasExplainabilityAssertions: true,
            HasI18nExposureAssertions: true,
            RawLog: "irrelevant"));

        result.IsPassed.Should().BeTrue();
        result.ExitCode.Should().Be(0);
        result.Status.Should().Be("ok");
        result.ExecutedAccIds.Should().Contain(new[] { "A-011", "A-012" });
    }

    // ACC:T152.2
    [Fact]
    public void ShouldProduceDeterministicOutcome_WhenEvaluatingSameFixtureTwice()
    {
        var fixture = new UiAssertionHardGateFixture(
            FixtureId: "ui-deterministic",
            HasExplainabilityAssertions: true,
            HasI18nExposureAssertions: true,
            RawLog: "noise");
        var firstResult = UiAssertionHardGateOrchestrator.Evaluate(fixture);
        var secondResult = UiAssertionHardGateOrchestrator.Evaluate(fixture);

        firstResult.Should().BeEquivalentTo(secondResult);
        firstResult.MachineReadableSummaryJson.Should().Be(secondResult.MachineReadableSummaryJson);
    }

    // ACC:T152.3
    [Fact]
    public void ShouldContainRequiredUiChecks_WhenBuildingGateManifest()
    {
        var requiredAccIds = UiAssertionGateRunner.GetRequiredGateUnits()
            .Where(unit => unit.IsMandatory && (unit.AccId == "A-011" || unit.AccId == "A-012"))
            .Select(unit => unit.AccId)
            .OrderBy(id => id, StringComparer.Ordinal)
            .ToArray();

        requiredAccIds.Should().Equal(
            new[]
            {
                "A-011",
                "A-012"
            });
    }

    // ACC:T152.4
    [Fact]
    public void ShouldIgnoreRawLogNoise_WhenCreatingStableUiSummary()
    {
        var baseline = UiAssertionHardGateOrchestrator.Evaluate(new UiAssertionHardGateFixture(
            FixtureId: "ui-noise",
            HasExplainabilityAssertions: true,
            HasI18nExposureAssertions: true,
            RawLog: "normal line"));
        var noisy = UiAssertionHardGateOrchestrator.Evaluate(new UiAssertionHardGateFixture(
            FixtureId: "ui-noise",
            HasExplainabilityAssertions: true,
            HasI18nExposureAssertions: true,
            RawLog: "ERROR line\nWARN line\nTRACE line"));

        baseline.Status.Should().Be("ok");
        noisy.Status.Should().Be("ok");
        baseline.ExecutedAccIds.Should().Equal(noisy.ExecutedAccIds);
        baseline.FailingAccIds.Should().Equal(noisy.FailingAccIds);
        baseline.Diagnostics.Should().Equal(noisy.Diagnostics);

        using var baselineDoc = JsonDocument.Parse(baseline.MachineReadableSummaryJson);
        using var noisyDoc = JsonDocument.Parse(noisy.MachineReadableSummaryJson);
        baselineDoc.RootElement.GetProperty("records").ToString()
            .Should().Be(noisyDoc.RootElement.GetProperty("records").ToString());
    }

    // ACC:T152.5
    [Fact]
    public void ShouldProvideActionableFailureMessage_WhenUiFixtureFailsHardGate()
    {
        var result = UiAssertionHardGateOrchestrator.Evaluate(new UiAssertionHardGateFixture(
            FixtureId: "ui-fail-a011",
            HasExplainabilityAssertions: false,
            HasI18nExposureAssertions: true,
            RawLog: "irrelevant"));

        result.IsPassed.Should().BeFalse();
        result.ExitCode.Should().Be(1);
        result.FailingAccIds.Should().ContainSingle().Which.Should().Be("A-011");
        result.Diagnostics.Should().ContainSingle(message =>
            message.Contains("A-011", StringComparison.Ordinal) &&
            message.Contains("Action:", StringComparison.Ordinal));
    }

    [Fact]
    public void ShouldReportBothChecks_WhenExplainabilityAndI18nAreBothMissing()
    {
        var result = UiAssertionHardGateOrchestrator.Evaluate(new UiAssertionHardGateFixture(
            FixtureId: "ui-fail-both",
            HasExplainabilityAssertions: false,
            HasI18nExposureAssertions: false,
            RawLog: "irrelevant"));

        result.IsPassed.Should().BeFalse();
        result.ExitCode.Should().Be(1);
        result.FailingAccIds.Should().BeEquivalentTo(new[] { "A-011", "A-012" }, options => options.WithStrictOrdering());
        result.Diagnostics.Should().HaveCount(2);
    }

    [Fact]
    public void ShouldFail_WhenOnlyI18nExposureAssertionIsMissing()
    {
        var result = UiAssertionHardGateOrchestrator.Evaluate(new UiAssertionHardGateFixture(
            FixtureId: "ui-fail-a012",
            HasExplainabilityAssertions: true,
            HasI18nExposureAssertions: false,
            RawLog: "irrelevant"));

        result.IsPassed.Should().BeFalse();
        result.ExitCode.Should().Be(1);
        result.FailingAccIds.Should().ContainSingle().Which.Should().Be("A-012");
        result.Diagnostics.Should().ContainSingle(message =>
            message.Contains("A-012", StringComparison.Ordinal) &&
            message.Contains("Action:", StringComparison.Ordinal));
    }
}
