using System;
using System.Collections.Generic;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public class Task166SplitTests
{
    // ACC:T166.1
    [Fact]
    public void ShouldIncludeAssertionsGatesAndScenarioEvidence_WhenGeneratingMigrationCompatibilityReport()
    {
        var assertions = new[] { "assertion:a1" };
        var gates = new[] { "gate:g1" };
        var scenarioEvidence = new[] { "scenario:s1" };
        var deterministicTestEvidence = new[] { "test:t166_case1" };
        var sut = new MigrationCompatibilityReportGenerator();

        var report = sut.Generate(assertions, gates, scenarioEvidence, deterministicTestEvidence);

        report.Sections.Should().Equal(
            "Assertions",
            "Gates",
            "ScenarioEvidence",
            "DeterministicTests");
    }

    [Fact]
    public void ShouldOnlyIncludeDeterministicTestsSection_WhenOptionalInputsAreEmpty()
    {
        var sut = new MigrationCompatibilityReportGenerator();

        var report = sut.Generate(
            assertions: Array.Empty<string>(),
            gates: Array.Empty<string>(),
            scenarioEvidence: Array.Empty<string>(),
            deterministicTestEvidence: new[] { "test:t166_case1" });

        report.Sections.Should().Equal("DeterministicTests");
    }

    // ACC:T166.2
    [Fact]
    public void ShouldRefuseReport_WhenDeterministicTestEvidenceMissing()
    {
        var assertions = new[] { "assertion:a1" };
        var gates = new[] { "gate:g1" };
        var scenarioEvidence = new[] { "scenario:s1" };
        var deterministicTestEvidence = Array.Empty<string>();
        var sut = new MigrationCompatibilityReportGenerator();

        Action act = () => sut.Generate(assertions, gates, scenarioEvidence, deterministicTestEvidence);

        act.Should().Throw<InvalidOperationException>()
            .WithMessage("*deterministic test evidence*");
    }

}
