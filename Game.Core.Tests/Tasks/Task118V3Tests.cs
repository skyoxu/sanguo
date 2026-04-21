using System;
using System.Collections.Generic;
using System.Reflection;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task118V3Tests
{
    // ACC:T118.2
    [Fact]
    [Trait("acceptance", "ACC:T118.2")]
    public void ShouldExposeClosedLifecycleMarker_WhenObjectiveSnapshotIsGeneratedForRepeatedIdenticalRuns()
    {
        var generateMethod = ResolveRequiredStaticMethod(
            "Game.Core.Services.Sanguo.SanguoObjectiveGenerationDeterminismEngine, Game.Core",
            "GenerateObjectiveSnapshot",
            typeof(int),
            typeof(string),
            typeof(int));

        var firstSnapshot = (string)generateMethod.Invoke(null, new object[] { 118002, "Campaign", 2 })!;
        var secondSnapshot = (string)generateMethod.Invoke(null, new object[] { 118002, "Campaign", 2 })!;

        firstSnapshot.Should().Be(secondSnapshot,
            "objective generation must stay deterministic for repeated identical runs before settlement closure validation");

        firstSnapshot.Should().StartWith(
            "OBJECTIVE_SNAPSHOT_CAMPAIGN_SEED_118002_ROUND_2_LIFECYCLE_CLOSED_OBJ_",
            "objective closure evidence should be encoded as a structured deterministic snapshot prefix");
    }

    [Fact]
    public void ShouldKeepSettlementPayloadDeterministic_WhenRunInputsAreIdentical()
    {
        var occurredAt = new DateTimeOffset(2026, 1, 1, 0, 0, 0, TimeSpan.Zero);
        var playerSettlements = new[]
        {
            new PlayerSettlement("p1", 12m),
            new PlayerSettlement("p2", -4m),
        };

        var firstSettlement = new SanguoMonthSettled(
            GameId: "g-task118",
            TurnNumber: 10,
            Year: 1,
            Month: 2,
            PlayerSettlements: playerSettlements,
            OccurredAt: occurredAt,
            CorrelationId: "corr-task118",
            CausationId: "ut.task118",
            AppliedMultipliers: CreateIdentityMultipliers());

        var secondSettlement = new SanguoMonthSettled(
            GameId: "g-task118",
            TurnNumber: 10,
            Year: 1,
            Month: 2,
            PlayerSettlements: playerSettlements,
            OccurredAt: occurredAt,
            CorrelationId: "corr-task118",
            CausationId: "ut.task118",
            AppliedMultipliers: CreateIdentityMultipliers());

        var firstJson = JsonSerializer.Serialize(firstSettlement);
        var secondJson = JsonSerializer.Serialize(secondSettlement);

        firstJson.Should().Be(secondJson,
            "repeated identical run inputs should produce identical settlement payloads");
    }

    [Fact]
    public void ShouldChangeObjectiveSnapshot_WhenRoundIndexChangesUnderSameSeedAndMode()
    {
        var generateMethod = ResolveRequiredStaticMethod(
            "Game.Core.Services.Sanguo.SanguoObjectiveGenerationDeterminismEngine, Game.Core",
            "GenerateObjectiveSnapshot",
            typeof(int),
            typeof(string),
            typeof(int));

        var roundTwoSnapshot = (string)generateMethod.Invoke(null, new object[] { 118002, "Campaign", 2 })!;
        var roundThreeSnapshot = (string)generateMethod.Invoke(null, new object[] { 118002, "Campaign", 3 })!;

        roundTwoSnapshot.Should().NotBe(roundThreeSnapshot,
            "objective lifecycle timeline should remain deterministic but still vary by round index");
    }

    [Fact]
    public void ShouldKeepReplayStableOrdering_WhenSettlementAndObjectiveSkipAreReplayedWithIdenticalInputs()
    {
        var firstReplay = SanguoEventOrderingRules.BuildReplayStableSnapshot(CreateReplayStableEventsForTask118());
        var secondReplay = SanguoEventOrderingRules.BuildReplayStableSnapshot(CreateReplayStableEventsForTask118Shuffled());

        firstReplay.Should().Equal(secondReplay,
            "replay-safe ordering must stay deterministic for settlement and objective skip events under identical inputs");
        SanguoEventOrderingRules.AssertReplayStableSnapshot(firstReplay, secondReplay);
    }

    [Fact]
    public void ShouldDetectReplayOrderingDrift_WhenTimelineTickChangesBetweenReplays()
    {
        var expected = SanguoEventOrderingRules.BuildReplayStableSnapshot(CreateReplayStableEventsForTask118());
        var drifted = SanguoEventOrderingRules.BuildReplayStableSnapshot(CreateReplayStableEventsForTask118Drifted());

        Action act = () => SanguoEventOrderingRules.AssertReplayStableSnapshot(expected, drifted);
        act.Should()
            .Throw<InvalidOperationException>()
            .WithMessage("*replay snapshot drift*");
    }

    private static MethodInfo ResolveRequiredStaticMethod(
        string assemblyQualifiedTypeName,
        string methodName,
        params Type[] parameterTypes)
    {
        var targetType = Type.GetType(assemblyQualifiedTypeName, throwOnError: false, ignoreCase: false);
        targetType.Should().NotBeNull($"required type was not found: {assemblyQualifiedTypeName}");

        var methodInfo = targetType!.GetMethod(
            methodName,
            BindingFlags.Public | BindingFlags.Static,
            binder: null,
            types: parameterTypes,
            modifiers: null);

        methodInfo.Should().NotBeNull($"required method was not found: {targetType.FullName}.{methodName}");
        return methodInfo!;
    }

    private static AppliedMultipliers CreateIdentityMultipliers()
    {
        return new AppliedMultipliers(
            BaseSteps: AppliedMultipliers.BaseDefaultSteps,
            CharacterStepDelta: 0,
            BuildingStepDelta: 0,
            EventStepDelta: 0,
            ActionCardStepDelta: 0,
            RelicStepDelta: 0,
            RegionStepDelta: 0,
            EffectiveSteps: AppliedMultipliers.BaseDefaultSteps);
    }

    private static IReadOnlyList<SanguoEventOrderingRules.ReplayStableEvent> CreateReplayStableEventsForTask118()
    {
        return new[]
        {
            new SanguoEventOrderingRules.ReplayStableEvent(
                RoundNumber: 2,
                Tick: 20,
                EventType: SanguoMonthSettled.EventType,
                SourceOrder: 1),
            new SanguoEventOrderingRules.ReplayStableEvent(
                RoundNumber: 2,
                Tick: 20,
                EventType: SanguoObjectiveSkipped.EventType,
                SourceOrder: 2),
        };
    }

    private static IReadOnlyList<SanguoEventOrderingRules.ReplayStableEvent> CreateReplayStableEventsForTask118Shuffled()
    {
        return new[]
        {
            new SanguoEventOrderingRules.ReplayStableEvent(
                RoundNumber: 2,
                Tick: 20,
                EventType: SanguoObjectiveSkipped.EventType,
                SourceOrder: 2),
            new SanguoEventOrderingRules.ReplayStableEvent(
                RoundNumber: 2,
                Tick: 20,
                EventType: SanguoMonthSettled.EventType,
                SourceOrder: 1),
        };
    }

    private static IReadOnlyList<SanguoEventOrderingRules.ReplayStableEvent> CreateReplayStableEventsForTask118Drifted()
    {
        return new[]
        {
            new SanguoEventOrderingRules.ReplayStableEvent(
                RoundNumber: 2,
                Tick: 20,
                EventType: SanguoMonthSettled.EventType,
                SourceOrder: 1),
            new SanguoEventOrderingRules.ReplayStableEvent(
                RoundNumber: 2,
                Tick: 21,
                EventType: SanguoObjectiveSkipped.EventType,
                SourceOrder: 2),
        };
    }
}
