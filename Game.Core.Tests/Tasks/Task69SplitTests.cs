using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task69SplitTests
{
    private const int TaskId = 69;
    private const string CsharpTestRef = "Game.Core.Tests/Tasks/Task69SplitTests.cs";
    private const string PolicyTestRef = "Game.Core.Tests/Tasks/Task69I18nMissingKeyExposurePolicyTests.cs";
    private const string LocalizationGateTestRef = "Game.Core.Tests/Tasks/Task69ExplanationLocalizationGateTests.cs";
    private const string UiWiringTestRef = "Game.Core.Tests/Tasks/Task69UiLocalizationWiringTests.cs";

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

    private static JsonDocument LoadJson(string repoRoot, params string[] rel)
    {
        var path = Path.Combine(new[] { repoRoot }.Concat(rel).ToArray());
        var text = File.ReadAllText(path);
        return JsonDocument.Parse(text);
    }

    private static JsonElement GetTaskFromView(string repoRoot, string viewFileName)
    {
        using var doc = LoadJson(repoRoot, ".taskmaster", "tasks", viewFileName);
        foreach (var task in doc.RootElement.EnumerateArray())
        {
            if (task.TryGetProperty("taskmaster_id", out var taskmasterId) && taskmasterId.GetInt32() == TaskId)
            {
                return task.Clone();
            }
        }

        throw new InvalidOperationException($"Task {TaskId} not found in {viewFileName}.");
    }

    [Fact]
    public void ShouldDeclareTaskScopedCsharpTestRefs_WhenTaskContainsContractRefs()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFileName in new[] { "tasks_back.json", "tasks_gameplay.json" })
        {
            var task = GetTaskFromView(repoRoot, viewFileName);

            task.TryGetProperty("contractRefs", out var contractRefs).Should().BeTrue();
            contractRefs.ValueKind.Should().Be(JsonValueKind.Array);
            contractRefs.GetArrayLength().Should().BeGreaterThan(0);

            task.TryGetProperty("test_refs", out var testRefs).Should().BeTrue();
            testRefs.ValueKind.Should().Be(JsonValueKind.Array);

            var refs = testRefs
                .EnumerateArray()
                .Select(static item => item.GetString() ?? string.Empty)
                .ToList();
            refs.Should().Contain(CsharpTestRef);
            refs.Should().Contain(PolicyTestRef);
            refs.Should().Contain(LocalizationGateTestRef);
            refs.Should().Contain(UiWiringTestRef);
            refs.Should().OnlyContain(static item => item.EndsWith(".cs", StringComparison.OrdinalIgnoreCase));
        }
    }

    [Fact]
    public void ShouldDescribeReleaseAndDevPolicy_WhenAcceptanceDefinesMissingKeyBehavior()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFileName in new[] { "tasks_back.json", "tasks_gameplay.json" })
        {
            var task = GetTaskFromView(repoRoot, viewFileName);
            var acceptance = task.GetProperty("acceptance")
                .EnumerateArray()
                .Select(static item => item.GetString() ?? string.Empty)
                .ToList();

            acceptance.Should().NotBeEmpty();
            acceptance.Should().Contain(item => item.Contains("release mode", StringComparison.OrdinalIgnoreCase));
            acceptance.Should().Contain(item => item.Contains("dev", StringComparison.OrdinalIgnoreCase));
            acceptance.Should().Contain(item => item.Contains("friendly fallback", StringComparison.OrdinalIgnoreCase));
            acceptance.Should().Contain(item => item.Contains("raw i18n key", StringComparison.OrdinalIgnoreCase));
        }
    }
}
