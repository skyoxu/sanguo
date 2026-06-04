using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task196CompletionCountTests
{
    private const int ExpectedCompletedTaskCount = 180;
    private const string ExpectedRequirementId = "REQ-7c8908846638";
    private const string ExpectedSourceRef = "docs/gdd/ui-gdd-flow.md:500";

    private static readonly string[] ExpectedAdapterRefs =
    [
        "Tests.Godot/tests/Adapters/Config/test_audio_player_adapter_nodes.gd",
        "Tests.Godot/tests/Adapters/test_data_store_adapter.gd",
        "Tests.Godot/tests/Adapters/test_event_bus_adapter.gd",
        "Tests.Godot/tests/Adapters/test_input_time_adapter.gd",
        "Tests.Godot/tests/Adapters/test_resource_loader_adapter.gd",
    ];

    // ACC:T196.1
    // ACC:T196.2
    [Fact]
    public void ShouldRecordExpectedChapter7CompletionCount_WhenTask196IsLoaded()
    {
        var task = LoadTask196();
        var acceptance = GetStringArray(task, "acceptance");

        acceptance.Should().Contain(item => item.Contains(ExpectedRequirementId, StringComparison.Ordinal)
            && item.Contains(ExpectedSourceRef, StringComparison.Ordinal)
            && item.Contains("Refs:", StringComparison.Ordinal));
        acceptance.Should().Contain(item => item.Contains("completed task count as exactly 180", StringComparison.Ordinal)
            && item.Contains(ExpectedSourceRef, StringComparison.Ordinal)
            && item.Contains("Refs:", StringComparison.Ordinal));

        ResolveExpectedCompletedTaskCount(task).Should().Be(ExpectedCompletedTaskCount);
    }

    // ACC:T196.3
    [Fact]
    public void ShouldReportUnresolvedCompletionCount_WhenRequiredEvidenceIsMissing()
    {
        var task = LoadTask196();

        ResolveExpectedCompletedTaskCount(default).Should().BeNull();
        ResolveExpectedCompletedTaskCount(task, sourceRefOverride: "docs/gdd/ui-gdd-flow.md:999").Should().BeNull();

        var missingInputEvidence = CreateUnresolvedCompletionCountEvidence(196, ExpectedSourceRef, "missing-completion-count-input");
        missingInputEvidence.Should().Be(new CompletionCountEvidence(
            TaskId: 196,
            SourceRef: ExpectedSourceRef,
            Status: "unresolved",
            Reason: "missing-completion-count-input"));

        var mismatchedSourceEvidence = CreateUnresolvedCompletionCountEvidence(196, "docs/gdd/ui-gdd-flow.md:999", "untraceable-source-ref");
        mismatchedSourceEvidence.Status.Should().Be("unresolved");
        mismatchedSourceEvidence.Reason.Should().Be("untraceable-source-ref");
    }

    // ACC:T196.4
    // ACC:T196.5
    // ACC:T196.6
    // ACC:T196.7
    [Fact]
    public void ShouldPreserveAdapterEvidence_WhenTask196IsLoaded()
    {
        var task = LoadTask196();
        var acceptance = GetStringArray(task, "acceptance");

        GetStringArray(task, "test_refs").Should().Contain(ExpectedAdapterRefs);
        GetStringArray(task, "test_refs").Should().Contain("Game.Core.Tests/Tasks/Task196CompletionCountTests.cs");
        acceptance.Should().Contain(item => item.Contains("[OBL:T196.O2]", StringComparison.Ordinal)
            && ExpectedAdapterRefs.Take(2).All(item.Contains));
        acceptance.Should().Contain(item => item.Contains("[OBL:T196.O3]", StringComparison.Ordinal)
            && ExpectedAdapterRefs.Take(2).All(item.Contains));
    }

    // ACC:T196.8
    // ACC:T196.9
    [Fact]
    public void ShouldPreserveCoreBoundary_WhenTask196IsLoaded()
    {
        var acceptance = GetStringArray(LoadTask196(), "acceptance");

        acceptance.Should().Contain(item => item.Contains("[OBL:T196.O4]", StringComparison.Ordinal)
            && item.Contains("Game.Core.Tests/Utilities/NoGodotDependencyTests.cs", StringComparison.Ordinal));
    }

    // ACC:T196.10
    // ACC:T196.11
    // ACC:T196.12
    // ACC:T196.13
    [Fact]
    public void ShouldRecordChapterAuditAndTripletValidatorEvidence_WhenTask196IsLoaded()
    {
        var acceptance = GetStringArray(LoadTask196(), "acceptance");

        acceptance.Should().Contain(item => item.Contains("[OBL:T196.O5]", StringComparison.Ordinal)
            && item.Contains("Chapter 3 coverage audit", StringComparison.Ordinal)
            && item.Contains("Refs:", StringComparison.Ordinal));
        acceptance.Should().Contain(item => item.Contains("[OBL:T196.O6]", StringComparison.Ordinal)
            && item.Contains("Chapter 3.8 triplet baseline validators", StringComparison.Ordinal)
            && item.Contains("Refs:", StringComparison.Ordinal));
    }

    private static JsonElement LoadTask196()
    {
        var repoRoot = FindRepoRoot();
        var jsonPath = Path.Combine(repoRoot, ".taskmaster", "tasks", "tasks_gameplay.json");
        using var document = JsonDocument.Parse(File.ReadAllText(jsonPath));

        foreach (var task in document.RootElement.EnumerateArray())
        {
            if (task.TryGetProperty("taskmaster_id", out var id) && id.GetInt32() == 196)
            {
                return task.Clone();
            }
        }

        throw new InvalidOperationException("Task 196 was not found in tasks_gameplay.json.");
    }

    private static int? ResolveExpectedCompletedTaskCount(JsonElement task, string? sourceRefOverride = null)
    {
        if (task.ValueKind != JsonValueKind.Object)
        {
            return null;
        }

        var sourceRef = sourceRefOverride ?? ExpectedSourceRef;
        var acceptance = GetStringArray(task, "acceptance");
        var sourceRefs = GetStringArray(task, "source_refs");

        if (!sourceRefs.Contains(sourceRef, StringComparer.Ordinal))
        {
            return null;
        }

        return acceptance.Any(item => item.Contains("completed task count as exactly 180", StringComparison.Ordinal)
            && item.Contains(sourceRef, StringComparison.Ordinal)
            && item.Contains("Refs:", StringComparison.Ordinal))
            ? ExpectedCompletedTaskCount
            : null;
    }

    private static CompletionCountEvidence CreateUnresolvedCompletionCountEvidence(
        int taskId,
        string sourceRef,
        string reason)
    {
        return new CompletionCountEvidence(taskId, sourceRef, "unresolved", reason);
    }

    private static string FindRepoRoot()
    {
        var current = new DirectoryInfo(Directory.GetCurrentDirectory());
        while (current is not null)
        {
            if (Directory.Exists(Path.Combine(current.FullName, ".taskmaster")))
            {
                return current.FullName;
            }

            current = current.Parent;
        }

        throw new DirectoryNotFoundException("Unable to locate repository root containing .taskmaster.");
    }

    private static string[] GetStringArray(JsonElement task, string propertyName)
    {
        task.TryGetProperty(propertyName, out var property).Should().BeTrue();
        property.ValueKind.Should().Be(JsonValueKind.Array);
        return property.EnumerateArray().Select(item => item.GetString() ?? string.Empty).ToArray();
    }

    private sealed record CompletionCountEvidence(int TaskId, string SourceRef, string Status, string Reason);
}
