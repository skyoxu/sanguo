using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.RegularExpressions;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task185UiGddPart2CoverageTests
{
    private const string TaskBackPath = ".taskmaster/tasks/tasks_back.json";
    private const string ThisTestPath = "Game.Core.Tests/Tasks/Task185UiGddPart2CoverageTests.cs";
    private const string UiGddFlowPath = "docs/gdd/ui-gdd-flow.md";
    private const string Task42Path = "Game.Core.Tests/Tasks/Task42PerformanceGateTests.cs";
    private const string Task228Path = "Game.Core.Tests/Tasks/Task228TraceabilityRequirementEvidenceTests.cs";
    private const string HealthTestsPath = "Game.Core.Tests/Domain/ValueObjects/HealthTests.cs";
    private const string DbHandleReleasePath = "Tests.Godot/tests/Adapters/Db/test_db_handle_release.gd";
    private static readonly Regex RequirementRowRegex = new(
        @"^ACC:T185\.\d+\s+Requirement\s+(REQ-[a-f0-9]+)\s+is implemented with traceable evidence\.\s+Source:\s+(.+):(\d+)\s+Refs:\s+(.+)$",
        RegexOptions.Compiled | RegexOptions.CultureInvariant);

    // ACC:T185.1
    [Fact]
    public void ShouldExposeReq5d6b99e1c724Coverage_WhenLoadingTask185Acceptance()
    {
        AssertRequirementRowConsistency(index: 0, requirementId: "REQ-5d6b99e1c724", expectedSourceLine: 483);
    }

    // ACC:T185.2
    [Fact]
    public void ShouldExposeReqd1434f18a1cfCoverage_WhenLoadingTask185Acceptance()
    {
        AssertRequirementRowConsistency(index: 1, requirementId: "REQ-d1434f18a1cf", expectedSourceLine: 491);
    }

    // ACC:T185.3
    [Fact]
    public void ShouldExposeReqdfcc1fb0aa67Coverage_WhenLoadingTask185Acceptance()
    {
        AssertRequirementRowConsistency(index: 2, requirementId: "REQ-dfcc1fb0aa67", expectedSourceLine: 502);
    }

    // ACC:T185.4
    [Fact]
    public void ShouldExposePerformanceGateCoverage_WhenLoadingTask185Acceptance()
    {
        var acceptance = LoadTask185AcceptanceLines();
        acceptance[3].Should().Contain("task 31 performance gate behavior");
        acceptance[3].Should().Contain(Task42Path);
        LoadFile(Task42Path).Should().Contain("ShouldSkipBuildAndTestSteps_WhenTask42PerformanceWorkflowRuns");
    }

    // ACC:T185.5
    [Fact]
    public void ShouldExposeRequirementCoverage_WhenLoadingTask185Acceptance()
    {
        var acceptance = LoadTask185AcceptanceLines();
        acceptance[4].Should().Contain("task 32 requirements behavior");
        acceptance[4].Should().Contain(Task228Path);
        LoadFile(Task228Path).Should().Contain("ShouldExposeRequirementEvidence_WhenReq9b21ada5b7c7IsValidated");
    }

    // ACC:T185.6
    [Fact]
    public void ShouldExposeDbHandleReleaseCoverage_WhenLoadingTask185Acceptance()
    {
        var acceptance = LoadTask185AcceptanceLines();
        acceptance[5].Should().Contain("database handle release behavior");
        acceptance[5].Should().Contain(DbHandleReleasePath);
        var dbTest = LoadFile(DbHandleReleasePath);
        dbTest.Should().Contain("test_handle_released_after_close_allows_rw_open");
        dbTest.Should().Contain("TryOpen");
        dbTest.Should().Contain("db.Close()");
    }

    // ACC:T185.7
    [Fact]
    public void ShouldExposeHealthCoverage_WhenLoadingTask185Acceptance()
    {
        var acceptance = LoadTask185AcceptanceLines();
        acceptance[6].Should().Contain("Health value object coverage");
        acceptance[6].Should().Contain(HealthTestsPath);
        var healthTest = LoadFile(HealthTestsPath);
        healthTest.Should().Contain("ShouldThrowArgumentOutOfRange_WhenTakingNegativeDamage");
        healthTest.Should().Contain("ShouldClampAtZeroAndRemainImmutable_WhenTakingDamage");
    }

    // ACC:T185.8
    [Fact]
    public void ShouldExposeTripletBaselineCoverage_WhenLoadingTask185Acceptance()
    {
        var acceptance = LoadTask185AcceptanceLines();
        acceptance[7].Should().Contain("Chapter 3.8 triplet baseline validators");
        acceptance[7].Should().Contain(Task228Path);
        LoadFile(Task228Path).Should().Contain("ValidateTraceabilityMatrixStructure");
    }

    private static string[] LoadTask185AcceptanceLines()
    {
        var task = LoadTask185BackEntry();
        task.TryGetProperty("acceptance", out var acceptanceElement).Should().BeTrue();
        acceptanceElement.ValueKind.Should().Be(JsonValueKind.Array);
        return acceptanceElement.EnumerateArray().Select(x => x.GetString() ?? string.Empty).ToArray();
    }

    private static JsonElement LoadTask185BackEntry()
    {
        var path = ToAbsolutePath(TaskBackPath);
        using var stream = File.OpenRead(path);
        using var document = JsonDocument.Parse(stream);
        foreach (var item in document.RootElement.EnumerateArray())
        {
            if (item.TryGetProperty("taskmaster_id", out var id) && id.ValueKind == JsonValueKind.Number && id.GetInt32() == 185)
            {
                return item.Clone();
            }
        }

        throw new InvalidOperationException("taskmaster_id=185 not found in tasks_back.json");
    }

    private static string ToAbsolutePath(string repoRelativePath)
    {
        var root = FindRepoRoot();
        return Path.Combine(root, repoRelativePath.Replace('/', Path.DirectorySeparatorChar));
    }

    private static string LoadFile(string repoRelativePath)
    {
        var path = ToAbsolutePath(repoRelativePath);
        File.Exists(path).Should().BeTrue($"{repoRelativePath} should exist");
        return File.ReadAllText(path);
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

    private static void AssertRequirementRowConsistency(int index, string requirementId, int expectedSourceLine)
    {
        var acceptance = LoadTask185AcceptanceLines();
        acceptance.Should().HaveCountGreaterThan(index);

        var row = acceptance[index];
        var match = RequirementRowRegex.Match(row);
        match.Success.Should().BeTrue("requirement acceptance rows should follow REQ/source/refs schema");
        match.Groups[1].Value.Should().Be(requirementId);
        match.Groups[2].Value.Should().Be(UiGddFlowPath);
        int.Parse(match.Groups[3].Value).Should().Be(expectedSourceLine);

        var refs = match.Groups[4].Value.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        refs.Should().Contain(ThisTestPath, "Task185 requirement rows should point to the task-scoped requirement evidence test");

        var sourceLines = LoadFile(UiGddFlowPath).Split('\n');
        sourceLines.Length.Should().BeGreaterOrEqualTo(expectedSourceLine);
        sourceLines[expectedSourceLine - 1].Trim().Should().NotBeNullOrWhiteSpace("source line should exist for deterministic traceability");
    }
}
