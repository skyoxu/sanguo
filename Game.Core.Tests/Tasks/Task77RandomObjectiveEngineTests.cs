using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task77RandomObjectiveEngineTests
{
    private const int TaskId = 77;
    private const int SplitTask117Id = 117;
    private const string Task117SplitTestRef = "Game.Core.Tests/Tasks/Task117SplitTests.cs";

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    private static readonly string[] ExpectedTaskRefs =
    {
        "Game.Core.Tests/Tasks/Task77RandomObjectiveEngineTests.cs",
        "Tests.Godot/tests/UI/test_task77_random_objective_hud_visibility.gd",
    };

    // ACC:T77.1
    [Fact]
    [Trait("acceptance", "ACC:T77.1")]
    public void ShouldBindTask77AcceptanceToTask117SplitEvidence_WhenReadingTaskViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task77 = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptance = ReadStringArray(task77, "acceptance");
            var testRefs = ReadStringArray(task77, "test_refs");

            acceptance.Should().HaveCount(2);
            acceptance[0].Should().Contain("split implementation evidence for task 117");
            acceptance[0].Should().Contain("Task77RandomObjectiveEngineTests.cs");
            testRefs.Should().Equal(ExpectedTaskRefs);

            var task117Refs = ReadTaskTestRefs(repoRoot, viewFile, SplitTask117Id);
            task117Refs.Should().Contain(Task117SplitTestRef);

            task117Refs
                .Select(testRef => Path.Combine(repoRoot, testRef.Replace('/', Path.DirectorySeparatorChar)))
                .Should().OnlyContain(path => File.Exists(path), "Task 77 backend closure requires deterministic evidence file from task 117.");

            var splitTestPath = Path.Combine(repoRoot, Task117SplitTestRef.Replace('/', Path.DirectorySeparatorChar));
            var splitTestSource = File.ReadAllText(splitTestPath);
            splitTestSource.Should().Contain("ACC:T117.1");
            splitTestSource.Should().Contain(nameof(SanguoObjectiveGenerationDeterminismEngine.GenerateObjectiveSnapshot));
        }
    }

    // ACC:T77.1
    [Fact]
    [Trait("acceptance", "ACC:T77.1")]
    public void ShouldAcceptTask77BackendClosure_WhenTask117SplitEvidenceIsPresentAndDeterminismSemanticsPass()
    {
        var baseline = SanguoObjectiveGenerationDeterminismEngine.GenerateObjectiveSnapshot(
            seed: 117001,
            modeName: "Campaign",
            roundIndex: 1);
        var repeated = SanguoObjectiveGenerationDeterminismEngine.GenerateObjectiveSnapshot(
            seed: 117001,
            modeName: "Campaign",
            roundIndex: 1);
        var differentRound = SanguoObjectiveGenerationDeterminismEngine.GenerateObjectiveSnapshot(
            seed: 117001,
            modeName: "Campaign",
            roundIndex: 2);
        var differentMode = SanguoObjectiveGenerationDeterminismEngine.GenerateObjectiveSnapshot(
            seed: 117001,
            modeName: "Skirmish",
            roundIndex: 1);

        baseline.Should().Be(repeated,
            "Task 77 backend closure requires deterministic objective generation behavior delivered by split task 117.");
        baseline.Should().NotBe(differentRound,
            "Task 77 backend closure requires deterministic but round-sensitive objective output.");
        baseline.Should().NotBe(differentMode,
            "Task 77 backend closure requires deterministic output constrained by mode semantics.");
    }

    // ACC:T77.1
    [Fact]
    [Trait("acceptance", "ACC:T77.1")]
    public void ShouldRejectTask77BackendClosure_WhenTask117SplitEvidenceReferenceIsMissingFromTaskView()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task117Refs = ReadTaskTestRefs(repoRoot, viewFile, SplitTask117Id);
            task117Refs.Should().Contain(
                Task117SplitTestRef,
                "Task 77 must not be accepted when split evidence from task 117 is missing.");
        }
    }

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var marker = Path.Combine(dir.FullName, ".taskmaster", "tasks", "tasks.json");
            if (File.Exists(marker))
            {
                return dir.FullName;
            }

            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException("Repo root not found (missing .taskmaster/tasks/tasks.json).");
    }

    private static JsonElement GetTaskByTaskmasterId(string repoRoot, string fileName, int taskmasterId)
    {
        using var doc = LoadJson(repoRoot, ".taskmaster", "tasks", fileName);
        foreach (var task in doc.RootElement.EnumerateArray())
        {
            if (task.TryGetProperty("taskmaster_id", out var idProperty) &&
                idProperty.ValueKind == JsonValueKind.Number &&
                idProperty.TryGetInt32(out var idValue) &&
                idValue == taskmasterId)
            {
                return task.Clone();
            }
        }

        throw new InvalidOperationException($"Task {taskmasterId} not found in {fileName}.");
    }

    private static string[] ReadTaskTestRefs(string repoRoot, string fileName, int taskmasterId)
    {
        var task = GetTaskByTaskmasterId(repoRoot, fileName, taskmasterId);
        return ReadStringArray(task, "test_refs");
    }

    private static string[] ReadStringArray(JsonElement task, string propertyName)
    {
        task.TryGetProperty(propertyName, out var property)
            .Should().BeTrue($"Task {TaskId} must contain '{propertyName}'.");

        property.ValueKind.Should().Be(JsonValueKind.Array);

        return property
            .EnumerateArray()
            .Select(static item => item.GetString() ?? string.Empty)
            .ToArray();
    }

    private static JsonDocument LoadJson(string repoRoot, params string[] relativeParts)
    {
        var path = Path.Combine(new[] { repoRoot }.Concat(relativeParts).ToArray());
        var text = File.ReadAllText(path);
        return JsonDocument.Parse(text);
    }
}
