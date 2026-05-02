using FluentAssertions;
using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task158SplitIntegrationTests
{
    private const int TaskId = 158;
    private const string SplitTask164Ref = "Game.Core.Tests/Tasks/Task164SplitTests.cs";
    private const string SplitTask165Ref = "Game.Core.Tests/Tasks/Task165SplitTests.cs";
    private const string RuntimeIntegrationRef = "Tests.Godot/tests/Integration/Security/test_signal_subscription_lifecycle.gd";

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    // ACC:T158.1
    [Fact]
    public void ShouldMarkClosureComplete_WhenTask164AndTask165EvidenceAreDelivered()
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

        var first = SignalSubscriptionLifecycleIntegrationPack.BuildEvidence(task164, task165);
        var second = SignalSubscriptionLifecycleIntegrationPack.EvaluateSplitEvidence(
            hasTask164Evidence: true,
            hasTask165Evidence: true,
            splitScopes: new[]
            {
                SignalSubscriptionLifecycleIntegrationPack.SplitScopeT165,
                SignalSubscriptionLifecycleIntegrationPack.SplitScopeT164,
            });

        first.IsClosureComplete.Should().BeTrue(
            "Task 158 closure requires deterministic evidence from both split tasks 164 and 165.");
        second.IsClosureComplete.Should().BeTrue();
        first.CompletionSignature.Should().Be(
            second.CompletionSignature,
            "closure signature must stay deterministic under evidence reordering.");
    }

    [Fact]
    [Trait("acceptance", "ACC:T158.1")]
    public void ShouldBindTask158ClosureToSplitTask164AndTask165Evidence_WhenReadingTaskViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptance = ReadStringArray(task, "acceptance");
            var testRefs = ReadStringArray(task, "test_refs");

            acceptance.Should().ContainSingle();
            acceptance[0].Should().Contain("split-task evidence confirms tasks 164 and 165");
            acceptance[0].Should().Contain("test_task158_runtime_signal_subscription_lifecycle_guard.gd");
            acceptance[0].Should().Contain("test_task158_signal_lifecycle_leak_fixtures.gd");
            acceptance[0].Should().Contain("Task158SplitIntegrationTests.cs");

            testRefs.Should().Contain("Game.Core.Tests/Tasks/Task158SplitIntegrationTests.cs");
            testRefs.Should().Contain("Tests.Godot/tests/Adapters/test_task158_runtime_signal_subscription_lifecycle_guard.gd");
            testRefs.Should().Contain("Tests.Godot/tests/Adapters/test_task158_signal_lifecycle_leak_fixtures.gd");
        }
    }

    [Fact]
    [Trait("acceptance", "ACC:T158.1")]
    public void ShouldKeepSplitEvidenceFilesAcceptanceAddressable_WhenReadingEvidenceFiles()
    {
        var repoRoot = FindRepoRoot();
        var task164Path = Path.Combine(repoRoot, SplitTask164Ref.Replace('/', Path.DirectorySeparatorChar));
        var task165Path = Path.Combine(repoRoot, SplitTask165Ref.Replace('/', Path.DirectorySeparatorChar));
        var integrationPath = Path.Combine(repoRoot, RuntimeIntegrationRef.Replace('/', Path.DirectorySeparatorChar));

        File.Exists(task164Path).Should().BeTrue();
        File.Exists(task165Path).Should().BeTrue();
        File.Exists(integrationPath).Should().BeTrue();

        ContainsTokenInFile(task164Path, "ACC:T164").Should().BeTrue();
        ContainsTokenInFile(task165Path, "ACC:T165").Should().BeTrue();
        ContainsTokenInFile(integrationPath, "ACC:T164").Should().BeTrue();
        ContainsTokenInFile(integrationPath, "ACC:T165").Should().BeTrue();
        ContainsTokenInFile(integrationPath, "EventBusAdapter.cs").Should().BeTrue();
    }

    [Fact]
    public void ShouldRemainIncomplete_WhenAnySplitEvidenceIsMissing()
    {
        var missing165 = SignalSubscriptionLifecycleIntegrationPack.EvaluateSplitEvidence(
            hasTask164Evidence: true,
            hasTask165Evidence: false,
            splitScopes: new[]
            {
                SignalSubscriptionLifecycleIntegrationPack.SplitScopeT164,
            });
        var missing164 = SignalSubscriptionLifecycleIntegrationPack.EvaluateSplitEvidence(
            hasTask164Evidence: false,
            hasTask165Evidence: true,
            splitScopes: new[]
            {
                SignalSubscriptionLifecycleIntegrationPack.SplitScopeT165,
            });

        missing165.IsClosureComplete.Should().BeFalse();
        missing164.IsClosureComplete.Should().BeFalse();
    }

    [Fact]
    public void ShouldRejectClosure_WhenScopesDoNotContainBothSplitTasks()
    {
        var result = SignalSubscriptionLifecycleIntegrationPack.EvaluateSplitEvidence(
            hasTask164Evidence: true,
            hasTask165Evidence: true,
            splitScopes: new[]
            {
                "T164-OTHER-SCOPE",
                SignalSubscriptionLifecycleIntegrationPack.SplitScopeT165,
            });

        result.IsClosureComplete.Should().BeFalse(
            "closure must bind to the expected split scopes instead of arbitrary scope labels.");
    }

    [Fact]
    [Trait("acceptance", "ACC:T158.1")]
    public void ShouldKeepTask158ClosureOnly_WhenScanningForAdditionalImplementationArtifacts()
    {
        var repoRoot = FindRepoRoot();
        var implementationCandidates = Directory
            .GetFiles(Path.Combine(repoRoot, "Game.Core"), "*Task158*.cs", SearchOption.AllDirectories)
            .Where(path => !path.Contains("Game.Core.Tests", StringComparison.OrdinalIgnoreCase))
            .ToArray();

        implementationCandidates.Should().BeEmpty(
            "Task 158 is closure-only and should not add new production implementation artifacts.");
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

    private static bool ContainsTokenInFile(string absolutePath, string token)
    {
        return File.ReadLines(absolutePath).Any(line => line.Contains(token, StringComparison.Ordinal));
    }
}
