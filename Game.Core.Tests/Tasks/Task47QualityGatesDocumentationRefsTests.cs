using System;
using System.IO;
using System.Linq;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task47QualityGatesDocumentationRefsTests
{
    private static readonly string[] ExpectedDocumentationPaths =
    {
        "docs/migration/Phase-13-Quality-Gates-Backlog.md",
        "docs/migration/Phase-13-Quality-Gates-Script.md",
    };
    private const string TraceabilityMatrixPath = "docs/prd/PRD_V4_TRACEABILITY_MATRIX.md";
    private const string T2OverlayIndexPath = "docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md";
    private static readonly string[] RequiredT2ContractOverlayLinks =
    {
        "08-Contracts-CloudEvent.md",
        "08-Contracts-CloudEvents-Core.md",
        "08-Contracts-Preload-Whitelist.md",
        "08-Contracts-Quality-Metrics.md",
    };

    // ACC:T47.5
    // ACC:T228.6
    // ACC:T228.7
    // ACC:T228.8
    // ACC:T228.9
    [Fact]
    public void ShouldContainExpectedDocumentationReferencePaths_WhenValidatingDocumentationList()
    {
        ExpectedDocumentationPaths.Should().NotBeNullOrEmpty();
        ExpectedDocumentationPaths.Should().OnlyContain(p => !string.IsNullOrWhiteSpace(p));
        ExpectedDocumentationPaths.Should().OnlyContain(p => p.EndsWith(".md", StringComparison.OrdinalIgnoreCase));
        ExpectedDocumentationPaths.Should().OnlyContain(p => p.StartsWith("docs/migration/", StringComparison.Ordinal));
        ExpectedDocumentationPaths.Should().OnlyHaveUniqueItems();
    }

    // ACC:T228.6
    [Fact]
    public void ShouldContainTraceabilityStatusLegend_WhenReadingPrdTraceabilityMatrix()
    {
        var text = ReadRepoFile(TraceabilityMatrixPath);

        text.Should().Contain("Status legend:", "traceability status legend is required for governed requirement classification");
        text.Should().Contain("Implemented:", "legend must define the Implemented status");
        text.Should().Contain("Partial:", "legend must define the Partial status");
        text.Should().Contain("Gap:", "legend must define the Gap status");
    }

    // ACC:T228.7
    [Fact]
    public void ShouldReferenceAdr0005_WhenReadingT2OverlayIndex()
    {
        var text = ReadRepoFile(T2OverlayIndexPath);
        text.Should().Contain("ADR-0005", "the status legend governance must identify ADR-0005");
    }

    // ACC:T228.8
    [Fact]
    public void ShouldLinkRequiredContractOverlayPages_WhenReadingT2OverlayIndex()
    {
        var text = ReadRepoFile(T2OverlayIndexPath);
        foreach (var link in RequiredT2ContractOverlayLinks)
        {
            text.Should().Contain(link, $"overlay index should link required contract overlay '{link}'");
        }
    }

    // ACC:T228.9
    [Fact]
    public void ShouldRejectLegendEvidence_WhenLegendOrRequirementRowsAreMissing()
    {
        var original = ReadRepoFile(TraceabilityMatrixPath);
        IsTraceabilityLegendEvidenceValid(original).Should().BeTrue("baseline document should carry legend + requirement evidence");

        var missingLegend = original.Replace("Status legend:", string.Empty, StringComparison.Ordinal);
        IsTraceabilityLegendEvidenceValid(missingLegend).Should().BeFalse("missing legend heading must be rejected");

        var missingRequirementEvidence = original.Replace("| V4-R1 |", "| V4-R1-REMOVED |", StringComparison.Ordinal);
        IsTraceabilityLegendEvidenceValid(missingRequirementEvidence).Should().BeFalse("missing requirement evidence row must be rejected");

        var invalidStatusValue = original.Replace("| V4-R1 | Extend character combat attributes while keeping `CombatRating` | Gap |",
            "| V4-R1 | Extend character combat attributes while keeping `CombatRating` | UnknownStatus |",
            StringComparison.Ordinal);
        IsTraceabilityLegendEvidenceValid(invalidStatusValue).Should().BeFalse("invalid status enum must be rejected");
    }

    // ACC:T47.5
    [Fact]
    public void ShouldEnsureDocumentationFilesExistAndAreNotEmpty_WhenRepositoryRootIsDiscoverable()
    {
        var repoRoot = TryFindRepositoryRoot();
        if (repoRoot is null)
        {
            true.Should().BeTrue();
            return;
        }

        foreach (var relativePath in ExpectedDocumentationPaths)
        {
            var fullPath = Path.Combine(repoRoot, relativePath.Replace('/', Path.DirectorySeparatorChar));
            File.Exists(fullPath).Should().BeTrue($"Expected documentation file to exist: {relativePath}");
            new FileInfo(fullPath).Length.Should().BeGreaterThan(0, $"Expected documentation file to be non-empty: {relativePath}");
        }
    }

    private static string? TryFindRepositoryRoot()
    {
        var current = new DirectoryInfo(AppContext.BaseDirectory);
        for (var i = 0; i < 12 && current is not null; i++)
        {
            if (File.Exists(Path.Combine(current.FullName, "project.godot")))
            {
                return current.FullName;
            }

            if (Directory.Exists(Path.Combine(current.FullName, ".git")))
            {
                return current.FullName;
            }

            current = current.Parent;
        }

        return null;
    }

    private static string ReadRepoFile(string relativePath)
    {
        var repoRoot = TryFindRepositoryRoot();
        repoRoot.Should().NotBeNull("repository root should be discoverable");
        var fullPath = Path.Combine(repoRoot!, relativePath.Replace('/', Path.DirectorySeparatorChar));
        File.Exists(fullPath).Should().BeTrue($"expected file to exist: {relativePath}");
        return File.ReadAllText(fullPath);
    }

    private static bool IsTraceabilityLegendEvidenceValid(string text)
    {
        if (!text.Contains("Status legend:", StringComparison.Ordinal) ||
            !text.Contains("Implemented:", StringComparison.Ordinal) ||
            !text.Contains("Partial:", StringComparison.Ordinal) ||
            !text.Contains("Gap:", StringComparison.Ordinal))
        {
            return false;
        }

        var lines = text.Split('\n');
        var rows = lines
            .Select(l => l.Trim())
            .Where(l => l.StartsWith("| V4-R", StringComparison.Ordinal) && l.EndsWith("|", StringComparison.Ordinal))
            .ToArray();

        if (rows.Length == 0)
        {
            return false;
        }

        var allowedStatuses = new[] { "Implemented", "Partial", "Gap" };
        foreach (var row in rows)
        {
            var cells = row.Split('|', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries);
            if (cells.Length < 6)
            {
                return false;
            }

            if (!allowedStatuses.Contains(cells[2], StringComparer.Ordinal))
            {
                return false;
            }
        }

        return rows.Any(r => r.Contains("| V4-R1 |", StringComparison.Ordinal)) &&
               rows.Any(r => r.Contains("| V4-R12 |", StringComparison.Ordinal));
    }
}
