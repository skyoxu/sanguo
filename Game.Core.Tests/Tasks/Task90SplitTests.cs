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

public sealed class Task90SplitTests
{
    private const int TaskId = 90;

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    private static readonly string[] ExpectedTaskRefs =
    {
        "Game.Core.Tests/Tasks/Task90SplitTests.cs",
        "Game.Core.Tests/Services/ForcedChallengePreemptionTests.cs",
    };

    // ACC:T90.3
    [Fact]
    [Trait("acceptance", "ACC:T90.3")]
    public void ShouldKeepTaskSpecificDeterministicEvidence_WhenReadingTask90FromBothViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptanceRefs = ReadStringArray(task, "acceptanceRefs");
            var acceptance = ReadStringArray(task, "acceptance");
            var testRefs = ReadStringArray(task, "test_refs");
            var contractRefs = ReadStringArray(task, "contractRefs");

            acceptanceRefs.Should().Equal("A-006~A-007");
            acceptance.Should().HaveCount(3);

            acceptance[0].Should().Contain("Forced challenge preemption must be explicit and auditable");
            acceptance[1].Should().Contain("must not continue advancing or resolving in parallel");
            acceptance[2].Should().Contain("deterministic task-specific evidence verifies both preemption transition and non-advance guarantees within split scope");
            acceptance[2].Should().Contain("Game.Core.Tests/Tasks/Task90SplitTests.cs");

            acceptance[0].Should().Contain("Game.Core.Tests/Services/ForcedChallengePreemptionTests.cs");
            acceptance[1].Should().Contain("Game.Core.Tests/Services/ForcedChallengePreemptionTests.cs");

            testRefs.Should().Equal(ExpectedTaskRefs);
            testRefs.Should().OnlyContain(testRef => ExpectedTaskRefs.Contains(testRef, StringComparer.Ordinal));

            contractRefs.Should().Equal(
                SanguoBossChallengePrompted.EventType,
                SanguoCombatStarted.EventType,
                SanguoCombatEnded.EventType);
        }
    }

    // ACC:T90.3
    [Fact]
    [Trait("acceptance", "ACC:T90.3")]
    public void ShouldExposeTransitionAndNonAdvanceSignals_WhenReplayingForcedChallengePreemptionSequence()
    {
        var replayResult = ReplayEventTypes(
            SanguoCombatStarted.EventType,
            SanguoBossChallengePrompted.EventType,
            SanguoCombatStarted.EventType,
            SanguoCombatEnded.EventType);

        var preemptionApplied = ReadRequiredProperty<bool>(replayResult, "PreemptionApplied");
        var activeFlow = ReadRequiredProperty<string>(replayResult, "ActiveFlow");
        var auditTrail = ReadStringListProperty(replayResult, "AuditTrail");
        var isPreemptedFlowLocked = ReadRequiredProperty<bool>(replayResult, "IsPreemptedFlowLocked");
        var preemptedFlowAdvancedInParallel = ReadRequiredProperty<bool>(replayResult, "PreemptedFlowAdvancedInParallel");
        var preemptedFlowResolvedInParallel = ReadRequiredProperty<bool>(replayResult, "PreemptedFlowResolvedInParallel");

        preemptionApplied.Should().BeTrue("forced challenge trigger must explicitly preempt an active challenge flow");
        activeFlow.Should().Be("forced_challenge", "control must switch to forced-challenge flow after preemption");
        auditTrail.Should().ContainInOrder(
            "challenge_started",
            "forced_challenge_preempted",
            "forced_challenge_started");
        isPreemptedFlowLocked.Should().BeTrue("preempted flow must stay locked until explicit restore or termination");
        preemptedFlowAdvancedInParallel.Should().BeFalse("preempted flow must not continue advancing in parallel");
        preemptedFlowResolvedInParallel.Should().BeFalse("preempted flow must not resolve in parallel");
    }

    // ACC:T90.3
    [Fact]
    [Trait("acceptance", "ACC:T90.3")]
    public void ShouldKeepPreemptedFlowUnchanged_WhenForcedFlowReceivesAdditionalCombatEventsWithoutRestore()
    {
        var replayResult = ReplayEventTypes(
            SanguoCombatStarted.EventType,
            SanguoBossChallengePrompted.EventType,
            SanguoCombatStarted.EventType,
            SanguoCombatEnded.EventType,
            SanguoCombatStarted.EventType,
            SanguoCombatEnded.EventType);

        var activeFlow = ReadRequiredProperty<string>(replayResult, "ActiveFlow");
        var isPreemptedFlowLocked = ReadRequiredProperty<bool>(replayResult, "IsPreemptedFlowLocked");
        var preemptedFlowAdvancedInParallel = ReadRequiredProperty<bool>(replayResult, "PreemptedFlowAdvancedInParallel");
        var preemptedFlowResolvedInParallel = ReadRequiredProperty<bool>(replayResult, "PreemptedFlowResolvedInParallel");

        activeFlow.Should().Be("forced_challenge");
        isPreemptedFlowLocked.Should().BeTrue();
        preemptedFlowAdvancedInParallel.Should().BeFalse("extra combat events must not advance the preempted flow while forced flow is active");
        preemptedFlowResolvedInParallel.Should().BeFalse("extra combat events must not resolve the preempted flow without explicit restore/terminate");
    }

    private static object ReplayEventTypes(params string[] eventTypes)
    {
        var replayMethod = ResolveReplayMethod();

        try
        {
            var replayResult = replayMethod.Invoke(null, new object[] { eventTypes });
            replayResult.Should().NotBeNull("forced challenge preemption replay must return an observable result object");
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
            "Game.Core.Services.Sanguo.ForcedChallengePreemption",
            "Game.Core.Services.Sanguo.ForcedChallengePreemptionEngine",
            "Game.Core.Services.Sanguo.ForcedChallengePreemptionTimeline",
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

        throw new InvalidOperationException(
            "Could not locate a public static ReplayEventTypes(IEnumerable<string>) on forced challenge preemption service.");
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

    private static T ReadRequiredProperty<T>(object source, string propertyName)
    {
        var property = source.GetType().GetProperty(propertyName, BindingFlags.Public | BindingFlags.Instance);
        property.Should().NotBeNull($"Replay result must expose '{propertyName}' for deterministic split acceptance checks.");

        var value = property!.GetValue(source);
        value.Should().NotBeNull($"Replay result property '{propertyName}' must not be null.");
        value.Should().BeAssignableTo<T>();

        return (T)value!;
    }

    private static IReadOnlyList<string> ReadStringListProperty(object source, string propertyName)
    {
        var property = source.GetType().GetProperty(propertyName, BindingFlags.Public | BindingFlags.Instance);
        property.Should().NotBeNull($"Replay result must expose '{propertyName}' for auditable transition evidence.");

        var value = property!.GetValue(source);
        value.Should().NotBeNull($"Replay result property '{propertyName}' must not be null.");
        value.Should().BeAssignableTo<IEnumerable>();

        return ((IEnumerable)value!)
            .Cast<object?>()
            .Select(item => item?.ToString() ?? string.Empty)
            .ToArray();
    }
}
