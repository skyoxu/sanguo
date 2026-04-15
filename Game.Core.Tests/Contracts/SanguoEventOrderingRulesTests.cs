using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using System;
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
}
