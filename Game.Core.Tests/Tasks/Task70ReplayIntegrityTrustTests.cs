using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task70ReplayIntegrityTrustTests
{
    private const int TaskId = 70;

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    private static readonly string[] ExpectedTaskRefs =
    {
        "Game.Core.Tests/Tasks/Task70ReplayIntegrityTrustTests.cs",
    };

    // ACC:T70.1
    [Fact]
    [Trait("acceptance", "ACC:T70.1")]
    public void ShouldBindTask70AcceptanceToTaskScopedEvidence_WhenReadingTaskViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptanceRefs = ReadStringArray(task, "acceptanceRefs");
            var acceptance = ReadStringArray(task, "acceptance");
            var testRefs = ReadStringArray(task, "test_refs");

            acceptanceRefs.Should().Equal("A-013", "A-014", "A-015");
            acceptance.Should().ContainSingle();
            acceptance[0].Should().Contain("split tasks 83 and 84");
            acceptance[0].Should().Contain("Task70ReplayIntegrityTrustTests.cs");

            testRefs.Should().Equal(ExpectedTaskRefs);
            testRefs.Should().OnlyContain(testRef => ExpectedTaskRefs.Contains(testRef, StringComparer.Ordinal));
        }
    }

    // ACC:T70.2
    [Fact]
    [Trait("acceptance", "ACC:T70.2")]
    public void ShouldRequireSplitTaskEvidenceFromTask83AndTask84_WhenReadingTaskViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task83Refs = ReadTaskTestRefs(repoRoot, viewFile, taskmasterId: 83);
            var task84Refs = ReadTaskTestRefs(repoRoot, viewFile, taskmasterId: 84);

            task83Refs.Should().NotBeEmpty("Task 70 closure depends on deterministic evidence from split task 83.");
            task84Refs.Should().NotBeEmpty("Task 70 closure depends on deterministic evidence from split task 84.");

            task83Refs.Concat(task84Refs)
                .Select(testRef => Path.Combine(repoRoot, testRef.Replace('/', Path.DirectorySeparatorChar)))
                .Should().OnlyContain(path => File.Exists(path), "split-task evidence files must exist in repository.");
        }
    }

    // ACC:T70.3
    [Fact]
    [Trait("acceptance", "ACC:T70.3")]
    public void ShouldKeepSplitTaskEvidenceAcceptanceAddressable_WhenReadingEvidenceFiles()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task83Refs = ReadTaskTestRefs(repoRoot, viewFile, taskmasterId: 83);
            var task84Refs = ReadTaskTestRefs(repoRoot, viewFile, taskmasterId: 84);

            ValidateReferencedEvidence(taskRefs: task83Refs, repoRoot: repoRoot, expectedAcceptanceMarker: "ACC:T83");
            ValidateReferencedEvidence(taskRefs: task84Refs, repoRoot: repoRoot, expectedAcceptanceMarker: "ACC:T84");
        }
    }

    // ACC:T70.4
    [Fact]
    [Trait("acceptance", "ACC:T70.4")]
    public void ShouldAggregateTask83AndTask84Evidence_WhenBuildingReplayIntegrationPackEvidence()
    {
        var evidence = ReplayIntegrityIntegrationPack.BuildEvidence(
            new Task83ReplayIntegritySplitEvidence(
                HasDeterministicEvidence: true,
                CoversA013A014Semantics: true,
                SplitScopes: new[] { ReplayIntegrityIntegrationPack.SplitScopeT83 }),
            new Task84ReplayMismatchSplitEvidence(
                HasDeterministicEvidence: true,
                CoversA015Semantics: true,
                EntersDefinedMismatchModeOnTrustFailure: true,
                SplitScopes: new[] { ReplayIntegrityIntegrationPack.SplitScopeT84 }));

        evidence.Task83Delivered.Should().BeTrue();
        evidence.Task84Delivered.Should().BeTrue();
        evidence.IsClosureComplete.Should().BeTrue();
    }

    // ACC:T70.5
    [Fact]
    [Trait("acceptance", "ACC:T70.5")]
    [Trait("acceptance", "ACC:T70.1")]
    public void ShouldRejectClosure_WhenTask83EvidenceIsMissingOrUnsupported()
    {
        var missingDeterministicEvidence = ReplayIntegrityIntegrationPack.BuildEvidence(
            new Task83ReplayIntegritySplitEvidence(
                HasDeterministicEvidence: false,
                CoversA013A014Semantics: true,
                SplitScopes: new[] { ReplayIntegrityIntegrationPack.SplitScopeT83 }),
            new Task84ReplayMismatchSplitEvidence(
                HasDeterministicEvidence: true,
                CoversA015Semantics: true,
                EntersDefinedMismatchModeOnTrustFailure: true,
                SplitScopes: new[] { ReplayIntegrityIntegrationPack.SplitScopeT84 }));

        var missingA013A014Coverage = ReplayIntegrityIntegrationPack.BuildEvidence(
            new Task83ReplayIntegritySplitEvidence(
                HasDeterministicEvidence: true,
                CoversA013A014Semantics: false,
                SplitScopes: new[] { ReplayIntegrityIntegrationPack.SplitScopeT83 }),
            new Task84ReplayMismatchSplitEvidence(
                HasDeterministicEvidence: true,
                CoversA015Semantics: true,
                EntersDefinedMismatchModeOnTrustFailure: true,
                SplitScopes: new[] { ReplayIntegrityIntegrationPack.SplitScopeT84 }));

        missingDeterministicEvidence.IsClosureComplete.Should().BeFalse();
        missingA013A014Coverage.IsClosureComplete.Should().BeFalse();
    }

    // ACC:T70.6
    [Fact]
    [Trait("acceptance", "ACC:T70.6")]
    [Trait("acceptance", "ACC:T70.1")]
    public void ShouldRejectClosure_WhenTask84EvidenceIsMissingUnsupportedOrScopeIncomplete()
    {
        var missingDeterministicEvidence = ReplayIntegrityIntegrationPack.BuildEvidence(
            new Task83ReplayIntegritySplitEvidence(
                HasDeterministicEvidence: true,
                CoversA013A014Semantics: true,
                SplitScopes: new[] { ReplayIntegrityIntegrationPack.SplitScopeT83 }),
            new Task84ReplayMismatchSplitEvidence(
                HasDeterministicEvidence: false,
                CoversA015Semantics: true,
                EntersDefinedMismatchModeOnTrustFailure: true,
                SplitScopes: new[] { ReplayIntegrityIntegrationPack.SplitScopeT84 }));

        var unsupportedMismatchMode = ReplayIntegrityIntegrationPack.BuildEvidence(
            new Task83ReplayIntegritySplitEvidence(
                HasDeterministicEvidence: true,
                CoversA013A014Semantics: true,
                SplitScopes: new[] { ReplayIntegrityIntegrationPack.SplitScopeT83 }),
            new Task84ReplayMismatchSplitEvidence(
                HasDeterministicEvidence: true,
                CoversA015Semantics: true,
                EntersDefinedMismatchModeOnTrustFailure: false,
                SplitScopes: new[] { ReplayIntegrityIntegrationPack.SplitScopeT84 }));

        var missingA015Coverage = ReplayIntegrityIntegrationPack.BuildEvidence(
            new Task83ReplayIntegritySplitEvidence(
                HasDeterministicEvidence: true,
                CoversA013A014Semantics: true,
                SplitScopes: new[] { ReplayIntegrityIntegrationPack.SplitScopeT83 }),
            new Task84ReplayMismatchSplitEvidence(
                HasDeterministicEvidence: true,
                CoversA015Semantics: false,
                EntersDefinedMismatchModeOnTrustFailure: true,
                SplitScopes: new[] { ReplayIntegrityIntegrationPack.SplitScopeT84 }));

        var missingRequiredScope = ReplayIntegrityIntegrationPack.BuildEvidence(
            new Task83ReplayIntegritySplitEvidence(
                HasDeterministicEvidence: true,
                CoversA013A014Semantics: true,
                SplitScopes: new[] { ReplayIntegrityIntegrationPack.SplitScopeT83 }),
            new Task84ReplayMismatchSplitEvidence(
                HasDeterministicEvidence: true,
                CoversA015Semantics: true,
                EntersDefinedMismatchModeOnTrustFailure: true,
                SplitScopes: Array.Empty<string>()));

        missingDeterministicEvidence.IsClosureComplete.Should().BeFalse();
        unsupportedMismatchMode.IsClosureComplete.Should().BeFalse();
        missingA015Coverage.IsClosureComplete.Should().BeFalse();
        missingRequiredScope.IsClosureComplete.Should().BeFalse();
    }

    // ACC:T70.7
    [Fact]
    [Trait("acceptance", "ACC:T70.7")]
    [Trait("acceptance", "ACC:T70.1")]
    public void ShouldRejectClosure_WhenTask83ScopeIsMissing()
    {
        var missingTask83Scope = ReplayIntegrityIntegrationPack.BuildEvidence(
            new Task83ReplayIntegritySplitEvidence(
                HasDeterministicEvidence: true,
                CoversA013A014Semantics: true,
                SplitScopes: Array.Empty<string>()),
            new Task84ReplayMismatchSplitEvidence(
                HasDeterministicEvidence: true,
                CoversA015Semantics: true,
                EntersDefinedMismatchModeOnTrustFailure: true,
                SplitScopes: new[] { ReplayIntegrityIntegrationPack.SplitScopeT84 }));

        missingTask83Scope.IsClosureComplete.Should().BeFalse();
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

    private static void ValidateReferencedEvidence(string[] taskRefs, string repoRoot, string expectedAcceptanceMarker)
    {
        var csRefs = taskRefs.Where(static testRef => testRef.EndsWith(".cs", StringComparison.OrdinalIgnoreCase)).ToArray();
        csRefs.Should().NotBeEmpty("split-task evidence should include C# test files.");

        foreach (var testRef in csRefs)
        {
            var evidencePath = Path.Combine(repoRoot, testRef.Replace('/', Path.DirectorySeparatorChar));
            File.Exists(evidencePath).Should().BeTrue("referenced evidence file must exist on disk.");

            ContainsTokenInFile(evidencePath, expectedAcceptanceMarker).Should().BeTrue(
                "evidence should remain acceptance-addressable.");
            ContainsTokenInFile(evidencePath, "[Fact]").Should().BeTrue(
                "evidence file should contain executable xUnit test cases.");
            File.ReadLines(evidencePath).Any(static line =>
                    line.Contains(".Should(", StringComparison.Ordinal)
                    || line.Contains("Assert.", StringComparison.Ordinal))
                .Should().BeTrue("evidence should include behavior assertions.");
        }
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

    private static bool ContainsTokenInFile(string path, string token)
    {
        foreach (var line in File.ReadLines(path))
        {
            if (line.Contains(token, StringComparison.Ordinal))
            {
                return true;
            }
        }

        return false;
    }
}
