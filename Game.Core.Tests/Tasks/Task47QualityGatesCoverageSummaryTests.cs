#nullable enable

using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task47QualityGatesCoverageSummaryTests
{
    private static readonly Encoding Utf8NoBom = new UTF8Encoding(encoderShouldEmitUTF8Identifier: false);

    // acceptance: ACC:T47.1
    [Fact]
    public void ShouldExposeCoverageThresholdConfigurationAndReferenceSummaryJson_WhenRunDotnetScriptIsPresent()
    {
        var repoRoot = FindRepoRoot();
        var runDotnet = Path.Combine(repoRoot, "scripts", "python", "run_dotnet.py");

        if (!File.Exists(runDotnet))
        {
            return;
        }

        var text = File.ReadAllText(runDotnet, Utf8NoBom);

        text.Should().NotBeNullOrWhiteSpace();
        text.Should().MatchRegex("COVERAGE_LINES_MIN", "run_dotnet.py should support a lines threshold override via env var");
        text.Should().MatchRegex("COVERAGE_BRANCHES_MIN", "run_dotnet.py should support a branches threshold override via env var");
        text.Should().MatchRegex("summary\\.json", "run_dotnet.py should write a summary.json artifact");

        var sample = "{\"coverage\":{\"lines_pct\":99.9,\"branches_pct\":98.8,\"lines_min\":90,\"branches_min\":85},\"threshold_ok\":true}";
        var parsed = TryParseCoverageSummary(sample, out var summary);

        parsed.Should().BeTrue("the coverage summary schema should be parseable");
        summary.LinesPct.Should().BeGreaterThan(0);
        summary.BranchesPct.Should().BeGreaterThan(0);
        summary.LinesMin.Should().BeGreaterThan(0);
        summary.BranchesMin.Should().BeGreaterThan(0);
    }

    // acceptance: ACC:T47.2
    [Fact]
    public void ShouldFailGate_WhenAnyCoverageBelowThreshold()
    {
        EvaluateCoverageGate(linesPct: 89.99, branchesPct: 85.00, linesMin: 90.00, branchesMin: 85.00)
            .Should().BeFalse("lines below threshold should fail the gate");

        EvaluateCoverageGate(linesPct: 90.00, branchesPct: 84.99, linesMin: 90.00, branchesMin: 85.00)
            .Should().BeFalse("branches below threshold should fail the gate");

        EvaluateCoverageGate(linesPct: 90.00, branchesPct: 85.00, linesMin: 90.00, branchesMin: 85.00)
            .Should().BeTrue("meeting both thresholds should pass the gate");
    }

    // acceptance: ACC:T47.4
    [Fact]
    public void ShouldWriteStepSummaryWithDotnetCoverageAndGdUnitResults_WhenWorkflowExists()
    {
        var repoRoot = FindRepoRoot();

        var workflow = FindFirstExistingFile(repoRoot, new[]
        {
            Path.Combine(".github", "workflows", "windows-quality-gate.yml"),
            Path.Combine(".github", "workflows", "windows-quality-gate.yaml"),
            Path.Combine(".github", "workflows", "quality-gate.yml"),
            Path.Combine(".github", "workflows", "quality-gate.yaml"),
        });

        if (workflow is null)
        {
            return;
        }

        var text = File.ReadAllText(workflow, Utf8NoBom);
        text.Should().NotBeNullOrWhiteSpace();

        text.Should().MatchRegex("quality_gates\\.py", "the workflow should invoke quality_gates.py");
        text.Should().MatchRegex("GITHUB_STEP_SUMMARY", "the workflow should write a step summary");

        var mentionsDotnetCoverage = Regex.IsMatch(text, "dotnet|coverage", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
        var mentionsGdUnit = Regex.IsMatch(text, "gdunit", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
        var mentionsSecurity = Regex.IsMatch(text, "security", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);

        (mentionsDotnetCoverage && mentionsGdUnit && mentionsSecurity)
            .Should().BeTrue("the step summary should clearly surface dotnet coverage and GdUnit (Adapters+Security) results");
    }

    private static string FindRepoRoot()
    {
        var start = new DirectoryInfo(AppContext.BaseDirectory);
        for (var current = start; current is not null; current = current.Parent)
        {
            var hasScripts = Directory.Exists(Path.Combine(current.FullName, "scripts", "python"));
            var hasCoreTests = Directory.Exists(Path.Combine(current.FullName, "Game.Core.Tests"));
            var hasProject = File.Exists(Path.Combine(current.FullName, "project.godot"));

            if ((hasScripts && hasCoreTests) || (hasProject && hasScripts))
            {
                return current.FullName;
            }
        }

        return start.FullName;
    }

    private static string? FindFirstExistingFile(string repoRoot, IEnumerable<string> relativePaths)
    {
        foreach (var relative in relativePaths)
        {
            var fullPath = Path.Combine(repoRoot, relative);
            if (File.Exists(fullPath))
            {
                return fullPath;
            }
        }

        return null;
    }

    private static bool EvaluateCoverageGate(double linesPct, double branchesPct, double linesMin, double branchesMin)
    {
        if (double.IsNaN(linesPct) || double.IsNaN(branchesPct) || double.IsNaN(linesMin) || double.IsNaN(branchesMin))
        {
            return false;
        }

        if (linesMin < 0 || branchesMin < 0)
        {
            return false;
        }

        return linesPct >= linesMin && branchesPct >= branchesMin;
    }

    private static bool TryParseCoverageSummary(string json, out CoverageSummary summary)
    {
        summary = default;

        try
        {
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;

            double? linesPct = null;
            double? branchesPct = null;
            double? linesMin = null;
            double? branchesMin = null;

            if (root.TryGetProperty("coverage", out var coverage) && coverage.ValueKind == JsonValueKind.Object)
            {
                linesPct = TryGetNumber(coverage, "lines_pct") ?? TryGetNumber(coverage, "line_pct") ?? TryGetNestedPct(coverage, "lines");
                branchesPct = TryGetNumber(coverage, "branches_pct") ?? TryGetNumber(coverage, "branch_pct") ?? TryGetNestedPct(coverage, "branches");
                linesMin = TryGetNumber(coverage, "lines_min") ?? TryGetNumber(coverage, "lines_threshold") ?? TryGetNestedThreshold(coverage, "lines");
                branchesMin = TryGetNumber(coverage, "branches_min") ?? TryGetNumber(coverage, "branches_threshold") ?? TryGetNestedThreshold(coverage, "branches");
            }
            else
            {
                linesPct = TryGetNumber(root, "lines_pct");
                branchesPct = TryGetNumber(root, "branches_pct");
                linesMin = TryGetNumber(root, "lines_min");
                branchesMin = TryGetNumber(root, "branches_min");
            }

            if (linesPct is null || branchesPct is null || linesMin is null || branchesMin is null)
            {
                return false;
            }

            summary = new CoverageSummary(linesPct.Value, branchesPct.Value, linesMin.Value, branchesMin.Value);
            return true;
        }
        catch
        {
            return false;
        }
    }

    private static double? TryGetNumber(JsonElement obj, string propertyName)
    {
        if (!obj.TryGetProperty(propertyName, out var prop))
        {
            return null;
        }

        if (prop.ValueKind == JsonValueKind.Number && prop.TryGetDouble(out var value))
        {
            return value;
        }

        return null;
    }

    private static double? TryGetNestedPct(JsonElement coverage, string propertyName)
    {
        if (!coverage.TryGetProperty(propertyName, out var nested) || nested.ValueKind != JsonValueKind.Object)
        {
            return null;
        }

        return TryGetNumber(nested, "pct") ?? TryGetNumber(nested, "measured") ?? TryGetNumber(nested, "value");
    }

    private static double? TryGetNestedThreshold(JsonElement coverage, string propertyName)
    {
        if (!coverage.TryGetProperty(propertyName, out var nested) || nested.ValueKind != JsonValueKind.Object)
        {
            return null;
        }

        return TryGetNumber(nested, "threshold") ?? TryGetNumber(nested, "min") ?? TryGetNumber(nested, "required");
    }

    private readonly record struct CoverageSummary(double LinesPct, double BranchesPct, double LinesMin, double BranchesMin);
}
