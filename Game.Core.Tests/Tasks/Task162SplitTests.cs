using System;
using System.Collections.Generic;
using System.Linq;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task162SplitTests
{
    // ACC:T162.1
    [Fact]
    public void ShouldProduceOneComplianceReportCoveringNamingDocumentationAndLifecycle_WhenAggregatingDeterministicChecks()
    {
        var aggregator = new SignalComplianceAggregator();
        var checks = new[]
        {
            new SignalComplianceCheckResult("naming", true, "logs/ci/2026-04-16/naming-check.json"),
            new SignalComplianceCheckResult("documentation", true, "logs/ci/2026-04-16/documentation-check.json"),
            new SignalComplianceCheckResult("lifecycle", true, "logs/ci/2026-04-16/lifecycle-check.json"),
        };

        var reports = aggregator.Aggregate("T162", checks);

        reports.Should().HaveCount(1, "deterministic aggregation must emit one signal compliance report per task");

        var report = reports.Single();
        report.TaskId.Should().Be("T162");
        report.CoveredChecks.Should().Equal("naming", "documentation", "lifecycle");
        report.AcceptanceRefs.Should().Equal("R11", "PH9-B4");
        report.EvidencePaths.Should().Equal(
            "logs/ci/2026-04-16/naming-check.json",
            "logs/ci/2026-04-16/documentation-check.json",
            "logs/ci/2026-04-16/lifecycle-check.json");
        report.IsCompliant.Should().BeTrue();
    }

    // ACC:T162.2
    [Fact]
    public void ShouldRefuseCompliance_WhenAnyRequiredCheckIsMissing()
    {
        var aggregator = new SignalComplianceAggregator();
        var checks = new[]
        {
            new SignalComplianceCheckResult("naming", true, "logs/ci/2026-04-16/naming-check.json"),
            new SignalComplianceCheckResult("documentation", true, "logs/ci/2026-04-16/documentation-check.json"),
        };

        var reports = aggregator.Aggregate("T162", checks);
        reports.Should().HaveCount(1, "deterministic aggregation must keep one task-scoped report");
        var report = reports.Single();

        report.IsCompliant.Should().BeFalse("missing lifecycle evidence must keep the report non-compliant");
        report.MissingChecks.Should().Equal("lifecycle");
        report.FailedChecks.Should().BeEmpty("missing checks and failed checks must be distinguished");
    }

    // ACC:T162.3
    [Fact]
    public void ShouldRefuseCompliance_WhenAnyRequiredCheckIsPresentButNotPassed()
    {
        var aggregator = new SignalComplianceAggregator();
        var checks = new[]
        {
            new SignalComplianceCheckResult("naming", true, "logs/ci/2026-04-16/naming-check.json"),
            new SignalComplianceCheckResult("documentation", true, "logs/ci/2026-04-16/documentation-check.json"),
            new SignalComplianceCheckResult("lifecycle", false, "logs/ci/2026-04-16/lifecycle-check.json"),
        };

        var reports = aggregator.Aggregate("T162", checks);
        reports.Should().HaveCount(1, "deterministic aggregation must keep one task-scoped report");
        var report = reports.Single();

        report.IsCompliant.Should().BeFalse("a failed required check must keep the report non-compliant");
        report.MissingChecks.Should().BeEmpty("failed checks should not be downgraded into missing semantics");
        report.FailedChecks.Should().Equal("lifecycle");
    }
}
