using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.RegularExpressions;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task32RequirementsTests
{
    private const string TaskBackPath = ".taskmaster/tasks/tasks_back.json";
    private const string ThisTestPath = "Game.Core.Tests/Tasks/Task32RequirementsTests.cs";
    private const string UiGddFlowPath = "docs/gdd/ui-gdd-flow.md";
    private static readonly Regex RequirementRowRegex = new(
        @"^ACC:T185\.\d+\s+Requirement\s+(REQ-[a-f0-9]+)\s+is implemented with traceable evidence\.\s+Source:\s+(.+):(\d+)\s+Refs:\s+(.+)$",
        RegexOptions.Compiled | RegexOptions.CultureInvariant);

    // ACC:T185.1
    [Fact]
    public void ShouldMapReq5d6b99e1c724ToTask32RequirementEvidence_WhenReadingTask185View()
    {
        AssertRequirementRowConsistency(index: 0, requirementId: "REQ-5d6b99e1c724", expectedSourceLine: 483);
    }

    // ACC:T185.2
    [Fact]
    public void ShouldMapReqd1434f18a1cfToTask32RequirementEvidence_WhenReadingTask185View()
    {
        AssertRequirementRowConsistency(index: 1, requirementId: "REQ-d1434f18a1cf", expectedSourceLine: 491);
    }

    // ACC:T185.3
    [Fact]
    public void ShouldMapReqdfcc1fb0aa67ToTask32RequirementEvidence_WhenReadingTask185View()
    {
        AssertRequirementRowConsistency(index: 2, requirementId: "REQ-dfcc1fb0aa67", expectedSourceLine: 502);
    }

    // ACC:T185.5
    [Fact]
    public void ShouldKeepTask32RequirementsAcceptance_WhenReadingTask185View()
    {
        var acceptance = LoadTask185Acceptance();
        acceptance[4].Should().Contain("task 32 requirements behavior");
        acceptance[4].Should().Contain("Task32RequirementsTests.cs");

        var bad = acceptance.ToArray();
        bad[4] = bad[4].Replace("ACC:T185.5", "ACC:T185.5X", StringComparison.Ordinal);
        ValidateAcceptanceRowOrThrow(bad[4]).Should().BeFalse("mismatched acceptance anchor should fail deterministic requirements validation");
    }

    // ACC:T185.8
    [Fact]
    public void ShouldKeepTripletValidatorEvidenceAcceptance_WhenReadingTask185View()
    {
        var acceptance = LoadTask185Acceptance();
        acceptance[7].Should().Contain("Chapter 3.8 triplet baseline validators");
        acceptance[7].Should().Contain("Task32RequirementsTests.cs");

        var result = RunBaselineValidator();
        result.exitCode.Should().Be(0, "Chapter 3.8 baseline validator command should succeed");
        result.output.Should().Contain("status=ok");
    }

    private static void AssertRequirementRowConsistency(int index, string requirementId, int expectedSourceLine)
    {
        var acceptance = LoadTask185Acceptance();
        acceptance.Should().HaveCountGreaterThan(index);

        var row = acceptance[index];
        var match = RequirementRowRegex.Match(row);
        match.Success.Should().BeTrue("requirement acceptance rows should follow REQ/source/refs schema");
        match.Groups[1].Value.Should().Be(requirementId);
        match.Groups[2].Value.Should().Be(UiGddFlowPath);
        int.Parse(match.Groups[3].Value).Should().Be(expectedSourceLine);

        var refs = match.Groups[4].Value.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        refs.Should().Contain(ThisTestPath, "Task32 requirement rows should point to task32 requirement evidence tests");

        var sourceLines = LoadFile(UiGddFlowPath).Split('\n');
        sourceLines.Length.Should().BeGreaterOrEqualTo(expectedSourceLine);
        sourceLines[expectedSourceLine - 1].Trim().Should().NotBeNullOrWhiteSpace("source line should exist for deterministic traceability");
    }

    private static string[] LoadTask185Acceptance()
    {
        var path = ToAbsolutePath(TaskBackPath);
        using var stream = File.OpenRead(path);
        using var document = JsonDocument.Parse(stream);
        foreach (var item in document.RootElement.EnumerateArray())
        {
            if (item.TryGetProperty("taskmaster_id", out var id) &&
                id.ValueKind == JsonValueKind.Number &&
                id.GetInt32() == 185)
            {
                return item.GetProperty("acceptance").EnumerateArray().Select(x => x.GetString() ?? string.Empty).ToArray();
            }
        }

        throw new InvalidOperationException("taskmaster_id=185 not found in tasks_back.json");
    }

    private static string LoadFile(string repoRelativePath)
    {
        var path = ToAbsolutePath(repoRelativePath);
        File.Exists(path).Should().BeTrue($"{repoRelativePath} should exist");
        return File.ReadAllText(path);
    }

    private static string ToAbsolutePath(string repoRelativePath)
    {
        var cursor = new DirectoryInfo(AppContext.BaseDirectory);
        while (cursor is not null)
        {
            if (File.Exists(Path.Combine(cursor.FullName, "AGENTS.md")))
            {
                return Path.Combine(cursor.FullName, repoRelativePath.Replace('/', Path.DirectorySeparatorChar));
            }

            cursor = cursor.Parent;
        }

        throw new DirectoryNotFoundException("Repository root not found from test base directory.");
    }

    private static bool ValidateAcceptanceRowOrThrow(string row)
    {
        var match = RequirementRowRegex.Match(row);
        if (!match.Success)
        {
            return false;
        }

        if (!match.Groups[2].Value.Equals(UiGddFlowPath, StringComparison.Ordinal))
        {
            return false;
        }

        if (!int.TryParse(match.Groups[3].Value, out _))
        {
            return false;
        }

        var refs = match.Groups[4].Value.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        return refs.Contains(ThisTestPath, StringComparer.Ordinal);
    }

    private static (int exitCode, string output) RunBaselineValidator()
    {
        var repoRoot = ToAbsolutePath(".").TrimEnd(Path.DirectorySeparatorChar);
        var psi = new ProcessStartInfo
        {
            FileName = "py",
            Arguments = "-3 scripts/python/run_task_triplet_baseline.py",
            WorkingDirectory = repoRoot,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        using var p = Process.Start(psi)!;
        var stdout = p.StandardOutput.ReadToEnd();
        var stderr = p.StandardError.ReadToEnd();
        p.WaitForExit();
        return (p.ExitCode, (stdout + "\n" + stderr).Trim());
    }
}
