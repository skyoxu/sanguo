using System;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task59CombatDeterminismTests
{
    // ACC:T59.2
    [Fact]
    public void ShouldExposeStableEventType_WhenCombatEnds()
    {
        SanguoCombatEnded.EventType.Should().Be("core.sanguo.combat.ended");
    }

    // ACC:T59.3
    [Fact]
    public void ShouldReturnSameResult_WhenSeedAndInputsAreSame()
    {
        var firstResult = SanguoCombatResolver.ResolvePveCombat(combatRating: 12, encounterTarget: 10, seed: 123);
        var secondResult = SanguoCombatResolver.ResolvePveCombat(combatRating: 12, encounterTarget: 10, seed: 123);

        firstResult.Should().Be(secondResult);
    }

    [Fact]
    public void ShouldLoseWithZeroMoneyDelta_WhenCombatRatingBelowEncounterTarget()
    {
        var result = SanguoCombatResolver.ResolvePveCombat(combatRating: 5, encounterTarget: 10, seed: 123);

        result.Outcome.Should().Be("lose");
        result.MoneyDelta.Should().Be(0m);
    }

    [Fact]
    public void ShouldThrow_WhenCombatRatingIsNegative()
    {
        var act = () => SanguoCombatResolver.ResolvePveCombat(combatRating: -1, encounterTarget: 10, seed: 0);
        act.Should().Throw<ArgumentOutOfRangeException>().And.ParamName.Should().Be("combatRating");
    }

    [Fact]
    public void ShouldThrow_WhenEncounterTargetIsNegative()
    {
        var act = () => SanguoCombatResolver.ResolvePveCombat(combatRating: 10, encounterTarget: -1, seed: 0);
        act.Should().Throw<ArgumentOutOfRangeException>().And.ParamName.Should().Be("encounterTarget");
    }
}

