using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task80PrdV3AssertionGateIntegrationTests
{
    private const int TaskId = 80;
    private const string ExpectedTaskRef = "Game.Core.Tests/Tasks/Task80PrdV3AssertionGateIntegrationTests.cs";

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    // ACC:T80.1
    [Fact]
    [Trait("acceptance", "ACC:T80.1")]
    public void ShouldConfirmIntegrationClosureFromSplitTasks_WhenReadingTask80Evidence()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task80 = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptance = ReadStringArray(task80, "acceptance");
            var testRefs = ReadStringArray(task80, "test_refs");

            acceptance.Should().ContainSingle();
            acceptance[0].Should().Contain("split tasks 91 and 92");
            acceptance[0].Should().Contain(ExpectedTaskRef);
            testRefs.Should().Contain(ExpectedTaskRef);

            var task91 = GetTaskByTaskmasterId(repoRoot, viewFile, taskmasterId: 91);
            var task92 = GetTaskByTaskmasterId(repoRoot, viewFile, taskmasterId: 92);
            var task91TestRefs = ReadStringArray(task91, "test_refs");
            var task92TestRefs = ReadStringArray(task92, "test_refs");

            task91TestRefs.Should().Contain("Game.Core.Tests/Tasks/Task91SplitTests.cs");
            task92TestRefs.Should().Contain("Game.Core.Tests/Tasks/Task92SplitTests.cs");

            var task91EvidencePath = Path.Combine(repoRoot, "Game.Core.Tests", "Tasks", "Task91SplitTests.cs");
            var task92EvidencePath = Path.Combine(repoRoot, "Game.Core.Tests", "Tasks", "Task92SplitTests.cs");

            File.Exists(task91EvidencePath).Should().BeTrue();
            File.Exists(task92EvidencePath).Should().BeTrue();
            File.ReadAllText(task91EvidencePath).Should().Contain("ACC:T91");
            File.ReadAllText(task92EvidencePath).Should().Contain("ACC:T92");

            var isClosureComplete = EvaluateClosure(
                hasTask91Evidence: task91TestRefs.Any(),
                hasTask92Evidence: task92TestRefs.Any());

            isClosureComplete.Should().BeTrue(
                "Task 80 is closure-only and must confirm integration closure from split evidence of tasks 91 and 92.");
        }
    }

    [Fact]
    public void ShouldRefuseClosure_WhenAnySplitEvidenceIsMissing()
    {
        var isMissingTask91 = EvaluateClosure(hasTask91Evidence: false, hasTask92Evidence: true);
        var isMissingTask92 = EvaluateClosure(hasTask91Evidence: true, hasTask92Evidence: false);

        isMissingTask91.Should().BeFalse();
        isMissingTask92.Should().BeFalse();
    }

    [Fact]
    public void ShouldKeepTask80AsClosureOnly_WhenScanningForNewImplementationArtifacts()
    {
        var repoRoot = FindRepoRoot();
        var gameCoreRoot = Path.Combine(repoRoot, "Game.Core");

        var implementationCandidates = Directory
            .GetFiles(gameCoreRoot, "*Task80*.cs", SearchOption.AllDirectories)
            .Where(path => !path.Contains("Game.Core.Tests", StringComparison.OrdinalIgnoreCase))
            .ToArray();

        implementationCandidates.Should().BeEmpty(
            "Task 80 must not introduce new implementation files and should only integrate split-task evidence.");
    }

    [Fact]
    public void ShouldFailRedFirst_WhenOnlyTask91EvidenceIsPresent()
    {
        var isClosureComplete = EvaluateClosure(hasTask91Evidence: true, hasTask92Evidence: false);

        isClosureComplete.Should().BeFalse(
            "closure cannot pass before task 92 evidence is integrated.");
    }

    private static bool EvaluateClosure(bool hasTask91Evidence, bool hasTask92Evidence)
    {
        return hasTask91Evidence && hasTask92Evidence;
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
