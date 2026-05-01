using System;
using System.Collections.Generic;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task167SplitTests
{
    private const string TaskSpecificEvidenceRef = "Game.Core.Tests/Tasks/Task167SplitTests.cs";

    // ACC:T167.1
    [Fact]
    [Trait("acceptance", "ACC:T167.1")]
    public void ShouldFailCompleteness_WhenMandatoryReportSectionIsMissing()
    {
        var report = new MigrationCompatibilityReport(
            new[] { "Assertions", "Gates", "DeterministicTests" });
        var evidenceLinks = new[]
        {
            "logs/ci/2026-05-01/task167/assertions.json",
            TaskSpecificEvidenceRef,
        };

        var result = MigrationCompatibilityCompletenessValidator.Validate(report, evidenceLinks, TaskSpecificEvidenceRef);

        result.IsComplete.Should().BeFalse("a report missing mandatory sections must not pass completeness validation");
        result.FailureCodes.Should().Contain("missing_mandatory_section:ScenarioEvidence");
    }

    // ACC:T167.2
    [Fact]
    [Trait("acceptance", "ACC:T167.2")]
    public void ShouldEmitDeterministicFailureOutput_WhenCompletenessChecksFail()
    {
        var report = new MigrationCompatibilityReport(
            new[] { "Assertions", "DeterministicTests" });
        var evidenceLinks = Array.Empty<string>();

        var first = MigrationCompatibilityCompletenessValidator.Validate(report, evidenceLinks, TaskSpecificEvidenceRef);
        var second = MigrationCompatibilityCompletenessValidator.Validate(report, evidenceLinks, TaskSpecificEvidenceRef);

        first.IsComplete.Should().BeFalse();
        second.IsComplete.Should().BeFalse();
        first.FailureOutput.Should().Be(second.FailureOutput);
        first.FailureCodes.Should().Equal(second.FailureCodes);
        first.FailureCodes.Should().Contain("missing_evidence_links");
    }

    // ACC:T167.3
    [Fact]
    [Trait("acceptance", "ACC:T167.3")]
    public void ShouldRefuseValidation_WhenTaskSpecificDeterministicEvidenceIsMissing()
    {
        var report = new MigrationCompatibilityReport(
            new[] { "Assertions", "Gates", "DeterministicTests" });
        var evidenceLinks = new[] { "logs/ci/2026-05-01/task167/completeness.json" };

        var result = MigrationCompatibilityCompletenessValidator.Validate(report, evidenceLinks, TaskSpecificEvidenceRef);

        result.IsComplete.Should().BeFalse("task-specific deterministic test evidence is required for completeness validation");
        result.FailureCodes.Should().Contain("missing_task_specific_test_evidence");
    }

    // ACC:T167.4
    [Fact]
    [Trait("acceptance", "ACC:T167.4")]
    public void ShouldPassCompleteness_WhenMandatorySectionsAndTaskSpecificEvidenceArePresent()
    {
        var report = new MigrationCompatibilityReport(
            new[] { "Assertions", "Gates", "ScenarioEvidence", "DeterministicTests" });
        var evidenceLinks = new[]
        {
            "logs/ci/2026-05-01/task167/assertions.json",
            "logs/ci/2026-05-01/task167/completeness.json",
            TaskSpecificEvidenceRef,
        };

        var result = MigrationCompatibilityCompletenessValidator.Validate(report, evidenceLinks, TaskSpecificEvidenceRef);

        result.IsComplete.Should().BeTrue("all mandatory sections and task-scoped deterministic evidence are present");
        result.FailureCodes.Should().BeEmpty();
        result.FailureOutput.Should().Be("ok");
    }
}
