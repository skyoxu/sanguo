using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using System;
using Xunit;

namespace Game.Core.Tests.Contracts;

public sealed class SanguoEventOrderingRulesTests
{
    [Fact]
    public void Validate_ShouldThrow_WhenEventTypesNull()
    {
        Action act = () => SanguoEventOrderingRules.Validate(null!);

        act.Should().Throw<ArgumentNullException>();
    }

    [Fact]
    public void Validate_ShouldReturn_WhenEventTypesEmpty()
    {
        SanguoEventOrderingRules.Validate(Array.Empty<string>());
    }

    [Fact]
    public void Validate_ShouldThrow_WhenPlayerStatePrecedesTurnStarted()
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
    public void Validate_ShouldThrow_WhenTurnEndedNotLast()
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
    public void Validate_ShouldPass_WhenEventsOrdered()
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
