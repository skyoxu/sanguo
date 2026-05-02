using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task89SplitTests
{
    private const int TaskId = 89;

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    private static readonly string[] ExpectedTaskRefs =
    {
        "Game.Core.Tests/Tasks/Task89SplitTests.cs",
        "Game.Core.Tests/Tasks/Task89BossPressureTimelineTests.cs",
    };

    // ACC:T89.2
    [Fact]
    [Trait("acceptance", "ACC:T89.2")]
    public void ShouldKeepT76SplitBoundaryEvidence_WhenValidatingTask89ScopeMetadata()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptanceRefs = ReadStringArray(task, "acceptanceRefs");
            var acceptance = ReadStringArray(task, "acceptance");
            var testRefs = ReadStringArray(task, "test_refs");
            var contractRefs = ReadStringArray(task, "contractRefs");

            acceptanceRefs.Should().Equal("R6");
            acceptance.Should().HaveCount(2);
            acceptance[1].Should().Contain("scope drifts away from the T76-origin split boundary");
            acceptance[1].Should().Contain("mixes in responsibilities from non-T76 workstreams");
            acceptance[1].Should().Contain("Game.Core.Tests/Tasks/Task89SplitTests.cs");

            testRefs.Should().Equal(ExpectedTaskRefs);
            testRefs.Should().OnlyContain(testRef => ExpectedTaskRefs.Contains(testRef, StringComparer.Ordinal));

            contractRefs.Should().Equal(
                SanguoGameTurnAdvanced.EventType,
                SanguoCombatStarted.EventType);
            contractRefs.Should().NotContain(
                SanguoBossChallengePrompted.EventType,
                "forced challenge preemption belongs to the non-T76 split workstream of Task 90.");
        }
    }

    // ACC:T89.2
    [Fact]
    [Trait("acceptance", "ACC:T89.2")]
    public void ShouldRejectNonT76WorkstreamEventType_WhenReplayingBossPressureTimeline()
    {
        var timelineType = FindTypeOrNull("Game.Core.Services.Sanguo.BossPressureTimeline");
        timelineType.Should().NotBeNull(
            "Task 89 split must provide an explicit timeline boundary that can reject out-of-scope workstream events.");

        var replayMethod = timelineType!.GetMethod(
            "ReplayEventTypes",
            BindingFlags.Public | BindingFlags.Static,
            binder: null,
            types: new[] { typeof(IEnumerable<string>) },
            modifiers: null);

        replayMethod.Should().NotBeNull(
            "Task 89 split must expose deterministic replay over event-type stream inputs.");

        var eventTypes = new[]
        {
            SanguoGameTurnAdvanced.EventType,
            SanguoBossChallengePrompted.EventType,
            SanguoCombatStarted.EventType,
        };

        Action act = () => replayMethod!.Invoke(null, new object[] { eventTypes });

        var invocationException = act.Should().Throw<TargetInvocationException>().Which;

        invocationException.InnerException.Should().NotBeNull();
        invocationException.InnerException.Should().BeOfType<ArgumentException>();
        invocationException.InnerException!.Message.Should().Contain(
            SanguoBossChallengePrompted.EventType,
            "the split boundary must refuse non-T76 workstream event types rather than silently mixing responsibilities.");
    }

    private static Type? FindTypeOrNull(string fullName)
    {
        foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
        {
            var type = assembly.GetType(fullName, throwOnError: false, ignoreCase: false);
            if (type is not null)
            {
                return type;
            }
        }

        return null;
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
