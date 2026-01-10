using System;
using System.IO;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks
{
    public sealed class Task47QualityGatesGdUnitAggregationTests
    {
        // ACC:T47.3
        [Fact]
        public void ShouldAggregateGdUnitAdaptersSecurityResultsIntoQualityGatesSummaryJson_WhenQualityGatesRuns()
        {
            var qualityGatesPy = RepoFile.ReadAllText("scripts/python/quality_gates.py");

            qualityGatesPy.Should().NotBeNullOrWhiteSpace();
            qualityGatesPy.Should().MatchRegex(
                "(?is)run_gdunit(\\.py)?",
                because: "quality_gates.py should invoke run_gdunit.py (or an equivalent wrapper) to execute GdUnit4 suites"
            );
            qualityGatesPy.Should().MatchRegex(
                "(?is)quality[-_]gates[-_]summary\\.json",
                because: "quality_gates.py should write an aggregated quality-gates-summary.json artifact"
            );
            qualityGatesPy.Should().MatchRegex(
                "(?is)(adapters.{0,200}security|security.{0,200}adapters)",
                because: "quality_gates.py should reference the Adapters+Security GdUnit4 hard gate collection"
            );
        }

        // ACC:T47.4
        [Fact]
        public void ShouldWriteWindowsWorkflowStepSummaryIncludingCoverageAndGdUnitAdaptersSecurity_WhenQualityGateWorkflowRunsAll()
        {
            var workflow = RepoFile.ReadAllText(".github/workflows/windows-quality-gate.yml");

            workflow.Should().NotBeNullOrWhiteSpace();
            workflow.Should().ContainEquivalentOf(
                "GITHUB_STEP_SUMMARY",
                because: "workflow should write a human-readable step summary"
            );
            workflow.Should().MatchRegex(
                "(?is)quality_gates\\.py\\s+all",
                because: "workflow should run quality_gates.py all"
            );
            workflow.Should().ContainEquivalentOf(
                "coverage",
                because: "step summary should mention dotnet coverage gates (measured values, thresholds, and pass/fail)"
            );
            workflow.Should().ContainEquivalentOf(
                "gdunit",
                because: "step summary should mention GdUnit4 aggregation results (Adapters+Security)"
            );
        }
    }

    internal static class RepoFile
    {
        public static string ReadAllText(string repoRelativePath)
        {
            var root = FindRepoRoot();
            var normalizedRelative = repoRelativePath.Replace('/', Path.DirectorySeparatorChar);
            var fullPath = Path.GetFullPath(Path.Combine(root, normalizedRelative));

            File.Exists(fullPath)
                .Should()
                .BeTrue($"Expected file to exist: {repoRelativePath} resolved to {fullPath}");

            return File.ReadAllText(fullPath);
        }

        private static string FindRepoRoot()
        {
            var startCandidates = new[]
            {
                Directory.GetCurrentDirectory(),
                AppContext.BaseDirectory,
            };

            foreach (var start in startCandidates)
            {
                if (string.IsNullOrWhiteSpace(start))
                {
                    continue;
                }

                var candidate = start;
                for (var i = 0; i < 20 && !string.IsNullOrWhiteSpace(candidate); i++)
                {
                    var sentinel = Path.Combine(candidate, "project.godot");
                    var scriptsDir = Path.Combine(candidate, "scripts", "python");

                    if (File.Exists(sentinel) && Directory.Exists(scriptsDir))
                    {
                        return candidate;
                    }

                    var parent = Directory.GetParent(candidate);
                    candidate = parent?.FullName ?? string.Empty;
                }
            }

            throw new DirectoryNotFoundException(
                "Could not locate repository root (expected to find project.godot and scripts/python)."
            );
        }
    }
}
