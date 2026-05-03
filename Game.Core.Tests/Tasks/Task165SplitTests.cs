using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task165SplitTests
{
    private const int TaskId = 165;
    private const string ExpectedCoreRef = "Game.Core.Tests/Tasks/Task165SplitTests.cs";
    private const string ExpectedIntegrationRef = "Tests.Godot/tests/Integration/Security/test_task165_signal_subscription_lifecycle.gd";

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    // ACC:T165.1
    [Fact]
    [Trait("acceptance", "ACC:T165.1")]
    public void ShouldKeepTask165LeakFixtureRefsBoundToDeterministicEvidence_WhenReadingTaskViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptanceRefs = ReadStringArray(task, "acceptanceRefs");
            var acceptance = ReadStringArray(task, "acceptance");
            var testRefs = ReadStringArray(task, "test_refs");

            acceptanceRefs.Should().Contain(new[] { "R11", "PH9-B5" });
            acceptance.Should().ContainSingle();
            acceptance[0].Should().Contain("stale signal handler leak");
            acceptance[0].Should().Contain(ExpectedCoreRef);
            acceptance[0].Should().Contain(ExpectedIntegrationRef);

            testRefs.Should().Contain(ExpectedCoreRef);
            testRefs.Should().Contain(ExpectedIntegrationRef);
            testRefs.Should().OnlyContain(testRef =>
                testRef.EndsWith(".cs", StringComparison.OrdinalIgnoreCase) ||
                testRef.EndsWith(".gd", StringComparison.OrdinalIgnoreCase));
        }
    }

    // ACC:T165.1
    [Fact]
    [Trait("acceptance", "ACC:T165.1")]
    public void ShouldMarkTask165SplitEvidenceDelivered_WhenLeakFixtureSignalIsControlled()
    {
        var task164 = new Task164SignalSubscriptionEvidence(
            HasDeterministicEvidence: true,
            CoversSubscribeUnsubscribeLifecycle: true,
            NoActiveRegistrationsAfterNodeExit: true,
            SplitScopes: new[] { SignalSubscriptionLifecycleIntegrationPack.SplitScopeT164 });
        var task165 = new Task165SignalLeakFixtureEvidence(
            HasDeterministicEvidence: true,
            DetectsStaleHandlerLeak: true,
            ValidatesCleanFixtureWithoutLeak: true,
            SplitScopes: new[] { SignalSubscriptionLifecycleIntegrationPack.SplitScopeT165 });

        var result = SignalSubscriptionLifecycleIntegrationPack.BuildEvidence(task164, task165);

        result.Task165Delivered.Should().BeTrue();
        result.HasScope(SignalSubscriptionLifecycleIntegrationPack.SplitScopeT165).Should().BeTrue();
        result.IsClosureComplete.Should().BeTrue();
    }

    // ACC:T165.1
    [Fact]
    [Trait("acceptance", "ACC:T165.1")]
    public void ShouldRejectTask165SplitEvidence_WhenLeakFixtureSignalContractBreaks()
    {
        var task164 = new Task164SignalSubscriptionEvidence(
            HasDeterministicEvidence: true,
            CoversSubscribeUnsubscribeLifecycle: true,
            NoActiveRegistrationsAfterNodeExit: true,
            SplitScopes: new[] { SignalSubscriptionLifecycleIntegrationPack.SplitScopeT164 });
        var task165 = new Task165SignalLeakFixtureEvidence(
            HasDeterministicEvidence: true,
            DetectsStaleHandlerLeak: false,
            ValidatesCleanFixtureWithoutLeak: true,
            SplitScopes: new[] { SignalSubscriptionLifecycleIntegrationPack.SplitScopeT165 });

        var result = SignalSubscriptionLifecycleIntegrationPack.BuildEvidence(task164, task165);

        result.Task164Delivered.Should().BeTrue();
        result.Task165Delivered.Should().BeFalse("leak fixture regression must block task 165 evidence.");
        result.IsClosureComplete.Should().BeFalse();
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
        using var stream = File.OpenRead(path);
        return JsonDocument.Parse(stream);
    }
}
