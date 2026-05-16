using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task31PerformanceGateTests
{
    private const string TaskBackPath = ".taskmaster/tasks/tasks_back.json";
    private const string Task42Path = "Game.Core.Tests/Tasks/Task42PerformanceGateTests.cs";

    // ACC:T185.4
    [Fact]
    public void ShouldKeepTask31PerformanceGateAcceptance_WhenReadingTask185View()
    {
        var acceptance = LoadTask185Acceptance();
        acceptance[3].Should().Contain("task 31 performance gate behavior");
        acceptance[3].Should().Contain("Task31PerformanceGateTests.cs");

        var task42 = LoadFile(Task42Path);
        task42.Should().Contain("ShouldSkipBuildAndTestSteps_WhenTask42PerformanceWorkflowRuns");
        task42.Should().Contain("ShouldEmitPerformanceGatesSummaryJson_WhenTask42WorkflowRuns");
        task42.Should().Contain("NotContain(\"dotnet test\"");
        task42.Should().Contain("NotContain(\"dotnet build\"");
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

    private static string LoadFile(string repoRelativePath)
    {
        var path = ToAbsolutePath(repoRelativePath);
        File.Exists(path).Should().BeTrue($"{repoRelativePath} should exist");
        return File.ReadAllText(path);
    }
}
