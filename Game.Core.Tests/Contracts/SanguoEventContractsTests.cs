using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Contracts;

public sealed class SanguoEventContractsTests
{
    [Fact]
    public void ShouldExposeExpectedEventTypes()
    {
        SanguoActionCardPlayed.EventType.Should().Be("core.sanguo.action_card.played");
        SanguoRandomEventApplied.EventType.Should().Be("core.sanguo.random_event.applied");
        SanguoBuildingBuilt.EventType.Should().Be("core.sanguo.building.built");
        SanguoLootGranted.EventType.Should().Be("core.sanguo.loot.granted");
        SanguoRelicApplied.EventType.Should().Be("core.sanguo.relic.applied");
    }

    [Fact]
    public void ShouldExposeExpectedEffectKindConstants()
    {
        SanguoEffectKinds.MoneyDelta.Should().Be("moneyDelta");
        SanguoEffectKinds.EconomyStepDelta.Should().Be("economyStepDelta");
    }
}

