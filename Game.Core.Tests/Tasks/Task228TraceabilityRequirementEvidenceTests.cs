using System;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task228TraceabilityRequirementEvidenceTests
{
    private const string TaskBackPath = ".taskmaster/tasks/tasks_back.json";
    private const string MatrixPath = "docs/prd/PRD_V4_TRACEABILITY_MATRIX.md";
    private const string ThisTestPath = "Game.Core.Tests/Tasks/Task228TraceabilityRequirementEvidenceTests.cs";
    private static readonly Regex AcceptanceRegex = new(
        @"^Requirement\s+(REQ-[a-f0-9]+)\s+is implemented with traceable evidence\.\s+Source:\s+(.+):(\d+)\s+Refs:\s+(.+)$",
        RegexOptions.Compiled | RegexOptions.CultureInvariant);
    private static readonly string[] AllowedStatuses = { "Implemented", "Partial", "Gap" };

    // ACC:T228.1
    // ACC:T185.1
    [Fact]
    public void ShouldExposeRequirementEvidence_WhenReq0fc29954ba84IsValidated()
    {
        AssertRequirementEvidence("REQ-0fc29954ba84", 7, "Requirement Traceability");
    }

    // ACC:T228.2
    // ACC:T185.2
    [Fact]
    public void ShouldExposeRequirementEvidence_WhenReq1994b9ffab06IsValidated()
    {
        AssertRequirementEvidence("REQ-1994b9ffab06", 113, "result application to player HP, rewards, and map return");
    }

    // ACC:T228.3
    // ACC:T185.3
    [Fact]
    public void ShouldExposeRequirementEvidence_WhenReq08202eb39b59IsValidated()
    {
        AssertRequirementEvidence("REQ-08202eb39b59", 124, "Chapter 3 should consume all PRD v4 files as the same requirement source set.");
    }

    // ACC:T228.4
    // ACC:T185.5
    [Fact]
    public void ShouldExposeRequirementEvidence_WhenReq9b21ada5b7c7IsValidated()
    {
        AssertRequirementEvidence("REQ-9b21ada5b7c7", 125, "Chapter 4 should decide contract changes from `PRD_V4_RULES_FREEZE.md` and `PRD_V4_TRACEABILITY_MATRIX.md`.");
    }

    // ACC:T228.5
    // ACC:T185.8
    [Fact]
    public void ShouldExposeRequirementEvidence_WhenReq429139de1ca2IsValidated()
    {
        AssertRequirementEvidence("REQ-429139de1ca2", 126, "Contract changes are expected, but they should be additive and preserve existing event names.");
    }

    private static void AssertRequirementEvidence(string requirementId, int expectedSourceLine, string expectedLineEvidence)
    {
        var repoRoot = FindRepoRoot();
        var acceptanceEntries = LoadTask228Acceptance(repoRoot);
        var matrixLines = File.ReadAllLines(Path.Combine(repoRoot, MatrixPath.Replace('/', Path.DirectorySeparatorChar)));

        matrixLines.Length.Should().BeGreaterOrEqualTo(expectedSourceLine, "source line should exist in traceability matrix");
        var sourceLine = matrixLines[expectedSourceLine - 1];
        sourceLine.Should().NotBeNullOrWhiteSpace("source line should carry evidence text");
        sourceLine.Should().Contain(expectedLineEvidence, "each requirement must map to a deterministic line-level evidence snippet");
        ValidateTraceabilityMatrixStructure(matrixLines);

        var acceptance = acceptanceEntries
            .FirstOrDefault(x => x.Contains(requirementId, StringComparison.Ordinal));

        acceptance.Should().NotBeNull($"task 228 acceptance should include {requirementId}");
        var match = AcceptanceRegex.Match(acceptance!);
        match.Success.Should().BeTrue("acceptance row should follow requirement/source/refs contract");
        match.Groups[1].Value.Should().Be(requirementId);
        match.Groups[2].Value.Should().Be("docs/prd/PRD_V4_TRACEABILITY_MATRIX.md");
        int.Parse(match.Groups[3].Value).Should().Be(expectedSourceLine);
        match.Groups[4].Value.Split(' ', StringSplitOptions.RemoveEmptyEntries)
            .Should()
            .Contain(ThisTestPath, "requirement-level refs should map to dedicated traceability evidence assertions");
    }

    private static string[] LoadTask228Acceptance(string repoRoot)
    {
        var path = Path.Combine(repoRoot, TaskBackPath.Replace('/', Path.DirectorySeparatorChar));
        using var stream = File.OpenRead(path);
        using var document = JsonDocument.Parse(stream);
        foreach (var item in document.RootElement.EnumerateArray())
        {
            if (!item.TryGetProperty("taskmaster_id", out var id) ||
                id.ValueKind != JsonValueKind.Number ||
                id.GetInt32() != 228)
            {
                continue;
            }

            var acceptance = item.GetProperty("acceptance")
                .EnumerateArray()
                .Select(x => x.GetString() ?? string.Empty)
                .ToArray();

            return acceptance;
        }

        throw new InvalidOperationException("taskmaster_id=228 not found in tasks_back.json");
    }

    private static void ValidateTraceabilityMatrixStructure(string[] matrixLines)
    {
        matrixLines.Should().Contain(line => line.Contains("Status legend:", StringComparison.Ordinal), "matrix must define status legend");
        var tableRows = matrixLines
            .Select(line => line.Trim())
            .Where(line => line.StartsWith("| V4-R", StringComparison.Ordinal) && line.EndsWith("|", StringComparison.Ordinal))
            .ToArray();
        tableRows.Should().NotBeEmpty("traceability matrix should expose requirement rows");

        foreach (var row in tableRows)
        {
            var cells = row.Split('|', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries);
            cells.Length.Should().BeGreaterOrEqualTo(6, "traceability row should contain ReqID/Requirement/Status/Code/Test/Assessment columns");
            var statusCell = cells[2];
            AllowedStatuses.Should().Contain(statusCell, "status should remain within legend enum");
        }
    }

    private static string FindRepoRoot()
    {
        var cursor = new DirectoryInfo(AppContext.BaseDirectory);
        while (cursor is not null)
        {
            if (File.Exists(Path.Combine(cursor.FullName, "AGENTS.md")) &&
                File.Exists(Path.Combine(cursor.FullName, TaskBackPath.Replace('/', Path.DirectorySeparatorChar))))
            {
                return cursor.FullName;
            }

            cursor = cursor.Parent;
        }

        throw new DirectoryNotFoundException("Repository root not found from test base directory.");
    }
}
