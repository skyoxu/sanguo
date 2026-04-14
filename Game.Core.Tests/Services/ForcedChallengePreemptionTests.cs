using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Services;

public sealed class ForcedChallengePreemptionTests
{
    // ACC:T90.1
    [Fact]
    [Trait("acceptance", "ACC:T90.1")]
    public void ShouldSwitchToForcedChallengeFlowAndRecordAudit_WhenForcedChallengePreemptsActiveChallenge()
    {
        var replayResult = ReplayEventTypes(
            SanguoCombatStarted.EventType,
            SanguoBossChallengePrompted.EventType,
            SanguoCombatStarted.EventType);

        var preemptionApplied = ReadRequiredProperty<bool>(replayResult, "PreemptionApplied");
        var activeFlow = ReadRequiredProperty<string>(replayResult, "ActiveFlow");
        var auditTrail = ReadStringListProperty(replayResult, "AuditTrail");

        preemptionApplied.Should().BeTrue("forced challenge trigger must explicitly preempt an active challenge flow");
        activeFlow.Should().Be("forced_challenge", "control must switch to forced-challenge flow after preemption");
        auditTrail.Should().ContainInOrder(
            "challenge_started",
            "forced_challenge_preempted",
            "forced_challenge_started");
    }

    // ACC:T90.2
    [Fact]
    [Trait("acceptance", "ACC:T90.2")]
    public void ShouldKeepPreemptedFlowLockedAndNotAdvancingInParallel_WhenPreemptionHasNotBeenRestoredOrTerminated()
    {
        var replayResult = ReplayEventTypes(
            SanguoCombatStarted.EventType,
            SanguoBossChallengePrompted.EventType,
            SanguoCombatStarted.EventType,
            SanguoCombatEnded.EventType);

        var isPreemptedFlowLocked = ReadRequiredProperty<bool>(replayResult, "IsPreemptedFlowLocked");
        var preemptedFlowAdvancedInParallel = ReadRequiredProperty<bool>(replayResult, "PreemptedFlowAdvancedInParallel");
        var preemptedFlowResolvedInParallel = ReadRequiredProperty<bool>(replayResult, "PreemptedFlowResolvedInParallel");

        isPreemptedFlowLocked.Should().BeTrue("preempted flow must stay locked until an explicit restore or termination command is processed");
        preemptedFlowAdvancedInParallel.Should().BeFalse("preempted flow must not continue advancing in parallel after forced-challenge takeover");
        preemptedFlowResolvedInParallel.Should().BeFalse("preempted flow must not resolve in parallel while forced-challenge flow is active");
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

    private static T ReadRequiredProperty<T>(object source, string propertyName)
    {
        var property = source.GetType().GetProperty(propertyName, BindingFlags.Public | BindingFlags.Instance);
        property.Should().NotBeNull($"Replay result must expose '{propertyName}' for deterministic acceptance checks.");

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
