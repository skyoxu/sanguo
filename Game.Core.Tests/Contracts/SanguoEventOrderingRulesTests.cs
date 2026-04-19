using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using System;
using System.Collections.Generic;
using Xunit;

namespace Game.Core.Tests.Contracts;

public sealed class SanguoEventOrderingRulesTests
{
    // ACC:T91.1
    [Fact]
    [Trait("acceptance", "ACC:T91.1")]
    public void ShouldExposeDeterministicTurnOrderRuleSet_WhenTask91RunnerBuildsCoreGateUnits()
    {
        SanguoEventOrderingRules.EventTypeOrderIndex.Should().ContainKey(SanguoGameTurnStarted.EventType);
        SanguoEventOrderingRules.EventTypeOrderIndex.Should().ContainKey(SanguoPlayerStateChanged.EventType);
        SanguoEventOrderingRules.EventTypeOrderIndex.Should().ContainKey(SanguoGameTurnEnded.EventType);

        SanguoEventOrderingRules.EventTypeOrderIndex[SanguoGameTurnStarted.EventType]
            .Should().BeLessThan(SanguoEventOrderingRules.EventTypeOrderIndex[SanguoPlayerStateChanged.EventType]);
        SanguoEventOrderingRules.EventTypeOrderIndex[SanguoPlayerStateChanged.EventType]
            .Should().BeLessThan(SanguoEventOrderingRules.EventTypeOrderIndex[SanguoGameTurnEnded.EventType]);
    }

    [Fact]
    public void ShouldThrowArgumentNullException_WhenEventTypesIsNull()
    {
        Action act = () => SanguoEventOrderingRules.Validate(null!);

        act.Should().Throw<ArgumentNullException>();
    }

    [Fact]
    public void ShouldNotThrow_WhenEventTypesIsEmpty()
    {
        SanguoEventOrderingRules.Validate(Array.Empty<string>());
    }

    [Fact]
    public void ShouldThrowInvalidOperationException_WhenPlayerStatePrecedesTurnStarted()
    {
        var events = new[]
        {
            SanguoPlayerStateChanged.EventType,
            SanguoGameTurnStarted.EventType,
        };

        Action act = () => SanguoEventOrderingRules.Validate(events);

        act.Should().Throw<InvalidOperationException>();
    }

    [Fact]
    public void ShouldThrowInvalidOperationException_WhenTurnEndedIsNotLast()
    {
        var events = new[]
        {
            SanguoGameTurnStarted.EventType,
            SanguoGameTurnEnded.EventType,
            SanguoPlayerStateChanged.EventType,
        };

        Action act = () => SanguoEventOrderingRules.Validate(events);

        act.Should().Throw<InvalidOperationException>();
    }

    [Fact]
    public void ShouldNotThrow_WhenEventsAreOrdered()
    {
        var events = new[]
        {
            SanguoGameTurnStarted.EventType,
            SanguoPlayerStateChanged.EventType,
            SanguoGameTurnEnded.EventType,
        };

        SanguoEventOrderingRules.Validate(events);
    }

    // ACC:T124.1
    [Fact]
    public void ShouldKeepGlobalRunStateTransitionedAfterTurnEnded_WhenEventOrderIndexIsReplayStable()
    {
        SanguoEventOrderingRules.EventTypeOrderIndex.Should().ContainKey(EventTypes.RunStateTransitioned);
        SanguoEventOrderingRules.EventTypeOrderIndex[EventTypes.RunStateTransitioned]
            .Should()
            .BeGreaterThan(SanguoEventOrderingRules.EventTypeOrderIndex[SanguoGameTurnEnded.EventType]);
    }

    // ACC:T124.1
    [Fact]
    public void ShouldSortSameRoundAndTickByExplicitReplayStableKeys_WhenBuildingReplaySnapshot()
    {
        var snapshot = SanguoEventOrderingRules.BuildReplayStableSnapshot(
            new[]
            {
                new SanguoEventOrderingRules.ReplayStableEvent(1, 8, EventTypes.RunStateTransitioned, 0),
                new SanguoEventOrderingRules.ReplayStableEvent(1, 8, SanguoGameTurnStarted.EventType, 9),
                new SanguoEventOrderingRules.ReplayStableEvent(1, 8, SanguoPlayerStateChanged.EventType, 2),
                new SanguoEventOrderingRules.ReplayStableEvent(1, 8, SanguoPlayerStateChanged.EventType, 5),
                new SanguoEventOrderingRules.ReplayStableEvent(1, 8, SanguoGameTurnEnded.EventType, 7),
            });

        snapshot.Should().Equal(
            $"round=0001|tick=00000008|slot=0001|source=0009|type={SanguoGameTurnStarted.EventType}",
            $"round=0001|tick=00000008|slot=0002|source=0002|type={SanguoPlayerStateChanged.EventType}",
            $"round=0001|tick=00000008|slot=0002|source=0005|type={SanguoPlayerStateChanged.EventType}",
            $"round=0001|tick=00000008|slot=0003|source=0007|type={SanguoGameTurnEnded.EventType}",
            $"round=0001|tick=00000008|slot=0004|source=0000|type={EventTypes.RunStateTransitioned}");
    }

    // ACC:T124.1
    [Fact]
    public void ShouldProduceEquivalentBoundarySnapshots_WhenReplayingWithIdenticalInputs()
    {
        var firstRun = SanguoEventOrderingRules.BuildReplayStableSnapshot(CreateRoundBoundaryReplayEvents());
        var secondRun = SanguoEventOrderingRules.BuildReplayStableSnapshot(CreateRoundBoundaryReplayEventsShuffled());

        firstRun.Should().Equal(secondRun);
    }

    // ACC:T124.1
    [Fact]
    public void ShouldThrowClearDiffMessage_WhenReplaySnapshotOrderDrifts()
    {
        var expected = SanguoEventOrderingRules.BuildReplayStableSnapshot(CreateRoundBoundaryReplayEvents());
        var drifted = SanguoEventOrderingRules.BuildReplayStableSnapshot(CreateDriftedRoundBoundaryReplayEvents());

        Action act = () => SanguoEventOrderingRules.AssertReplayStableSnapshot(expected, drifted);

        act.Should()
            .Throw<InvalidOperationException>()
            .WithMessage("*replay snapshot drift*index*expected=*actual=*");
    }

    private static IReadOnlyList<SanguoEventOrderingRules.ReplayStableEvent> CreateRoundBoundaryReplayEvents()
    {
        return new[]
        {
            new SanguoEventOrderingRules.ReplayStableEvent(1, 1, SanguoGameTurnStarted.EventType, 0),
            new SanguoEventOrderingRules.ReplayStableEvent(1, 1, SanguoPlayerStateChanged.EventType, 1),
            new SanguoEventOrderingRules.ReplayStableEvent(1, 1, SanguoGameTurnEnded.EventType, 2),
            new SanguoEventOrderingRules.ReplayStableEvent(1, 1, EventTypes.RunStateTransitioned, 3),
            new SanguoEventOrderingRules.ReplayStableEvent(2, 1, SanguoGameTurnStarted.EventType, 0),
            new SanguoEventOrderingRules.ReplayStableEvent(2, 1, SanguoPlayerStateChanged.EventType, 1),
            new SanguoEventOrderingRules.ReplayStableEvent(2, 1, SanguoGameTurnEnded.EventType, 2),
            new SanguoEventOrderingRules.ReplayStableEvent(2, 1, EventTypes.RunStateTransitioned, 3),
        };
    }

    private static IReadOnlyList<SanguoEventOrderingRules.ReplayStableEvent> CreateRoundBoundaryReplayEventsShuffled()
    {
        return new[]
        {
            new SanguoEventOrderingRules.ReplayStableEvent(2, 1, EventTypes.RunStateTransitioned, 3),
            new SanguoEventOrderingRules.ReplayStableEvent(2, 1, SanguoGameTurnEnded.EventType, 2),
            new SanguoEventOrderingRules.ReplayStableEvent(2, 1, SanguoPlayerStateChanged.EventType, 1),
            new SanguoEventOrderingRules.ReplayStableEvent(2, 1, SanguoGameTurnStarted.EventType, 0),
            new SanguoEventOrderingRules.ReplayStableEvent(1, 1, EventTypes.RunStateTransitioned, 3),
            new SanguoEventOrderingRules.ReplayStableEvent(1, 1, SanguoGameTurnEnded.EventType, 2),
            new SanguoEventOrderingRules.ReplayStableEvent(1, 1, SanguoPlayerStateChanged.EventType, 1),
            new SanguoEventOrderingRules.ReplayStableEvent(1, 1, SanguoGameTurnStarted.EventType, 0),
        };
    }

    private static IReadOnlyList<SanguoEventOrderingRules.ReplayStableEvent> CreateDriftedRoundBoundaryReplayEvents()
    {
        return new[]
        {
            new SanguoEventOrderingRules.ReplayStableEvent(1, 1, SanguoGameTurnStarted.EventType, 0),
            new SanguoEventOrderingRules.ReplayStableEvent(1, 1, SanguoPlayerStateChanged.EventType, 1),
            new SanguoEventOrderingRules.ReplayStableEvent(1, 1, SanguoGameTurnEnded.EventType, 2),
            new SanguoEventOrderingRules.ReplayStableEvent(1, 1, EventTypes.RunStateTransitioned, 3),
            new SanguoEventOrderingRules.ReplayStableEvent(2, 1, SanguoGameTurnStarted.EventType, 0),
            new SanguoEventOrderingRules.ReplayStableEvent(2, 1, SanguoPlayerStateChanged.EventType, 1),
            new SanguoEventOrderingRules.ReplayStableEvent(2, 2, SanguoGameTurnEnded.EventType, 2),
            new SanguoEventOrderingRules.ReplayStableEvent(2, 1, EventTypes.RunStateTransitioned, 3),
        };
    }
}
