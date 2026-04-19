using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task123SplitTests
{
    private const int TaskId = 123;
    private const string ExpectedCoreRef = "Game.Core.Tests/Tasks/Task123SplitTests.cs";

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    // ACC:T123.1
    [Fact]
    [Trait("acceptance", "ACC:T123.1")]
    public void ShouldKeepTaskSpecificRefs_WhenReadingTask123FromBothViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptance = ReadStringArray(task, "acceptance");
            var testRefs = ReadStringArray(task, "test_refs");

            acceptance.Should().HaveCount(3);
            acceptance[0].Should().Contain("ACC:T123.1");
            acceptance[1].Should().Contain("ACC:T123.2");
            acceptance[2].Should().Contain("ACC:T123.3");
            acceptance.Should().OnlyContain(item => item.Contains(ExpectedCoreRef, StringComparison.Ordinal));
            acceptance.Should().NotContain(item => item.Contains("SanguoEventOrderingRulesTests.cs", StringComparison.Ordinal));

            testRefs.Should().ContainSingle().Which.Should().Be(ExpectedCoreRef);
        }
    }

    // ACC:T123.1
    [Fact]
    [Trait("acceptance", "ACC:T123.1")]
    public void ShouldRouteThroughSingleSequencerPath_WhenNominalAndPreemptedFlowsReplay()
    {
        var nominalReplay = ReplayEventTypes(
            SanguoGameTurnAdvanced.EventType,
            SanguoTokenMoved.EventType,
            SanguoCombatEnded.EventType);

        var preemptedReplay = ReplayEventTypes(
            SanguoGameTurnAdvanced.EventType,
            SanguoBossChallengePrompted.EventType,
            SanguoCombatStarted.EventType,
            SanguoCombatEnded.EventType,
            SanguoTokenMoved.EventType);

        var nominalPathIds = ReadStringListProperty(nominalReplay, "SequencerPathIds");
        var preemptedPathIds = ReadStringListProperty(preemptedReplay, "SequencerPathIds");

        nominalPathIds.Should().NotBeEmpty();
        preemptedPathIds.Should().NotBeEmpty();

        nominalPathIds.Distinct(StringComparer.Ordinal).Should().ContainSingle(
            "nominal flow should route transition triggers and side effects through one sequencer path");
        preemptedPathIds.Distinct(StringComparer.Ordinal).Should().ContainSingle(
            "preempted flow should route transition triggers and side effects through one sequencer path");

        nominalPathIds[0].Should().Be(
            preemptedPathIds[0],
            "both flows should use the same sequencer path identity rather than split orchestration pipelines");
    }

    // ACC:T123.2
    [Fact]
    [Trait("acceptance", "ACC:T123.2")]
    public void ShouldEmitOrderedCheckpointsWithReasonCodes_WhenBossPreemptedFlowReplays()
    {
        var replayResult = ReplayEventTypes(
            SanguoGameTurnAdvanced.EventType,
            SanguoBossChallengePrompted.EventType,
            SanguoCombatStarted.EventType,
            SanguoCombatEnded.EventType,
            SanguoTokenMoved.EventType);

        var checkpoints = ReadStringListProperty(replayResult, "Checkpoints");
        var reasonCodes = ReadStringListProperty(replayResult, "CheckpointReasonCodes");

        checkpoints.Should().ContainInOrder(
            "camp_entered",
            "pressure_entered",
            "pressure_preempted_by_boss",
            "board_entered");

        reasonCodes.Should().ContainInOrder(
            "nominal",
            "nominal",
            "boss_preempted",
            "boss_preempted");
    }

    // ACC:T123.2
    [Fact]
    [Trait("acceptance", "ACC:T123.2")]
    public void ShouldKeepFrozenPhaseOrderWithoutDrift_WhenComparingNominalAndBossPreemptedBranches()
    {
        var nominalReplay = ReplayEventTypes(
            SanguoGameTurnAdvanced.EventType,
            SanguoTokenMoved.EventType,
            SanguoCombatEnded.EventType);

        var preemptedReplay = ReplayEventTypes(
            SanguoGameTurnAdvanced.EventType,
            SanguoBossChallengePrompted.EventType,
            SanguoCombatStarted.EventType,
            SanguoCombatEnded.EventType,
            SanguoTokenMoved.EventType);

        var nominalPhaseOrder = ReadStringListProperty(nominalReplay, "FrozenPhaseOrder");
        var preemptedPhaseOrder = ReadStringListProperty(preemptedReplay, "FrozenPhaseOrder");

        nominalPhaseOrder.Should().Equal("camp", "pressure", "board");
        preemptedPhaseOrder.Should().Equal("camp", "pressure", "board");

        var nominalBranch = ReadRequiredProperty<string>(nominalReplay, "BoardEntryBranch");
        var preemptedBranch = ReadRequiredProperty<string>(preemptedReplay, "BoardEntryBranch");

        nominalBranch.Should().Be("standard_board_entry");
        preemptedBranch.Should().Be("boss_preempted_board_entry");
    }

    // ACC:T123.3
    [Fact]
    [Trait("acceptance", "ACC:T123.3")]
    public void ShouldKeepObservableSideEffectsOnSameSequencerPath_WhenComparingNominalAndBossPreemptedFlows()
    {
        var nominalReplay = ReplayEventTypes(
            SanguoGameTurnAdvanced.EventType,
            SanguoTokenMoved.EventType,
            SanguoCombatEnded.EventType);

        var preemptedReplay = ReplayEventTypes(
            SanguoGameTurnAdvanced.EventType,
            SanguoBossChallengePrompted.EventType,
            SanguoCombatStarted.EventType,
            SanguoCombatEnded.EventType,
            SanguoTokenMoved.EventType);

        var nominalPathIds = ReadStringListProperty(nominalReplay, "SequencerPathIds");
        var preemptedPathIds = ReadStringListProperty(preemptedReplay, "SequencerPathIds");
        var nominalCheckpoints = ReadStringListProperty(nominalReplay, "Checkpoints");
        var preemptedCheckpoints = ReadStringListProperty(preemptedReplay, "Checkpoints");
        var nominalReasonCodes = ReadStringListProperty(nominalReplay, "CheckpointReasonCodes");
        var preemptedReasonCodes = ReadStringListProperty(preemptedReplay, "CheckpointReasonCodes");

        nominalPathIds.Distinct(StringComparer.Ordinal).Should().ContainSingle();
        preemptedPathIds.Distinct(StringComparer.Ordinal).Should().ContainSingle();
        nominalPathIds[0].Should().Be(preemptedPathIds[0], "observable side effects must be emitted through one sequencer identity");

        nominalCheckpoints.Should().HaveCount(nominalReasonCodes.Count);
        preemptedCheckpoints.Should().HaveCount(preemptedReasonCodes.Count);

        nominalCheckpoints.Zip(nominalReasonCodes).Should().ContainInOrder(
            ("camp_entered", "nominal"),
            ("pressure_entered", "nominal"),
            ("board_entered", "nominal"));

        preemptedCheckpoints.Zip(preemptedReasonCodes).Should().ContainInOrder(
            ("camp_entered", "nominal"),
            ("pressure_entered", "nominal"),
            ("pressure_preempted_by_boss", "boss_preempted"),
            ("board_entered", "boss_preempted"));
    }

    private static object ReplayEventTypes(params string[] eventTypes)
    {
        var replayMethod = ResolveReplayMethod();

        try
        {
            var replayResult = replayMethod.Invoke(null, new object[] { eventTypes });
            replayResult.Should().NotBeNull("transition replay should return an observable result object");
            return replayResult!;
        }
        catch (TargetInvocationException ex) when (ex.InnerException is not null)
        {
            throw ex.InnerException;
        }
    }

    private static MethodInfo ResolveReplayMethod()
    {
        var candidateTypeNames = new[]
        {
            "Game.Core.Services.Sanguo.CampPressureBoardTransitionSequencer",
            "Game.Core.Services.Sanguo.CampPressureBoardSequencer",
            "Game.Core.Services.Sanguo.CampPressureBoardTransitionTimeline",
            "Game.Core.Services.Sanguo.CampPressureBoardTransitionEngine",
        };

        foreach (var candidateTypeName in candidateTypeNames)
        {
            var candidateType = FindTypeOrNull(candidateTypeName);
            if (candidateType is null)
            {
                continue;
            }

            var replayMethod = candidateType.GetMethod(
                "ReplayEventTypes",
                BindingFlags.Public | BindingFlags.Static,
                binder: null,
                types: new[] { typeof(IEnumerable<string>) },
                modifiers: null);

            if (replayMethod is not null)
            {
                return replayMethod;
            }
        }

        return typeof(MissingCampPressureBoardTransitionSequencer).GetMethod(
            nameof(MissingCampPressureBoardTransitionSequencer.ReplayEventTypes),
            BindingFlags.Public | BindingFlags.Static)!;
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
        var text = File.ReadAllText(path);
        return JsonDocument.Parse(text);
    }

    private static T ReadRequiredProperty<T>(object source, string propertyName)
    {
        var property = source.GetType().GetProperty(propertyName, BindingFlags.Public | BindingFlags.Instance);
        property.Should().NotBeNull($"Replay result must expose '{propertyName}' for transition-sequencer checks.");

        var value = property!.GetValue(source);
        value.Should().NotBeNull($"Replay result property '{propertyName}' must not be null.");
        value.Should().BeAssignableTo<T>();

        return (T)value!;
    }

    private static IReadOnlyList<string> ReadStringListProperty(object source, string propertyName)
    {
        var property = source.GetType().GetProperty(propertyName, BindingFlags.Public | BindingFlags.Instance);
        property.Should().NotBeNull($"Replay result must expose '{propertyName}' for checkpoint assertions.");

        var value = property!.GetValue(source);
        value.Should().NotBeNull($"Replay result property '{propertyName}' must not be null.");
        value.Should().BeAssignableTo<IEnumerable>();

        return ((IEnumerable)value!)
            .Cast<object?>()
            .Select(item => item?.ToString() ?? string.Empty)
            .ToArray();
    }

    private sealed record MissingCampPressureBoardTransitionReplayResult(
        IReadOnlyList<string> SequencerPathIds,
        IReadOnlyList<string> Checkpoints,
        IReadOnlyList<string> CheckpointReasonCodes,
        IReadOnlyList<string> FrozenPhaseOrder,
        string BoardEntryBranch);

    private static class MissingCampPressureBoardTransitionSequencer
    {
        public static object ReplayEventTypes(IEnumerable<string> eventTypes)
        {
            var eventTypeStream = eventTypes.ToArray();
            var isBossPreempted = eventTypeStream.Contains(SanguoBossChallengePrompted.EventType, StringComparer.Ordinal);

            return isBossPreempted
                ? new MissingCampPressureBoardTransitionReplayResult(
                    SequencerPathIds: new[] { "nominal_path", "boss_preempted_path" },
                    Checkpoints: new[] { "board_entered", "camp_entered", "pressure_preempted_by_boss" },
                    CheckpointReasonCodes: new[] { "boss_preempted", "nominal", "boss_preempted" },
                    FrozenPhaseOrder: new[] { "camp", "board", "pressure" },
                    BoardEntryBranch: "standard_board_entry")
                : new MissingCampPressureBoardTransitionReplayResult(
                    SequencerPathIds: new[] { "nominal_path", "drift_path" },
                    Checkpoints: new[] { "board_entered", "camp_entered", "pressure_entered" },
                    CheckpointReasonCodes: new[] { "nominal", "nominal", "nominal" },
                    FrozenPhaseOrder: new[] { "camp", "board", "pressure" },
                    BoardEntryBranch: "boss_preempted_board_entry");
        }
    }
}
