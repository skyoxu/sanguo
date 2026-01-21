using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Services;
using MoneyValue = Game.Core.Domain.ValueObjects.Money;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task51MultiplierCompositionTests
{
    // ACC:T51.1
    [Fact]
    public void ShouldKeepAppliedMultipliersRulesStable_WhenUsingFixedStepSystem()
    {
        AppliedMultipliers.Step.Should().Be(0.5m);
        AppliedMultipliers.BaseDefaultSteps.Should().Be(2);
        AppliedMultipliers.MinSteps.Should().Be(1);
        AppliedMultipliers.MaxSteps.Should().Be(6);

        AppliedMultipliers.ClampSteps(0).Should().Be(1);
        AppliedMultipliers.ClampSteps(1).Should().Be(1);
        AppliedMultipliers.ClampSteps(6).Should().Be(6);
        AppliedMultipliers.ClampSteps(999).Should().Be(6);

        AppliedMultipliers.IsHalfStepMultiplier(0.5m).Should().BeTrue();
        AppliedMultipliers.IsHalfStepMultiplier(1.0m).Should().BeTrue();
        AppliedMultipliers.IsHalfStepMultiplier(1.5m).Should().BeTrue();
        AppliedMultipliers.IsHalfStepMultiplier(1.25m).Should().BeFalse();

        var placeholder = new AppliedMultipliers(
            BaseSteps: 2,
            CharacterStepDelta: 0,
            BuildingStepDelta: 0,
            EventStepDelta: 0,
            ActionCardStepDelta: 0,
            RelicStepDelta: 0,
            RegionStepDelta: 0,
            EffectiveSteps: 2);
        placeholder.Sources.Should().Be(AppliedMultiplierSources.None);
        placeholder.EffectiveMultiplier.Should().Be(1.0m);
    }

    // ACC:T51.1
    [Fact]
    public async Task ShouldRejectNonHalfStepMultiplier_WhenBuyingCity()
    {
        var bus = new InMemoryEventBus();
        var economy = new SanguoEconomyManager(bus);
        var published = 0;
        using var _ = bus.Subscribe(_ => { published++; return Task.CompletedTask; });

        var player = new SanguoPlayer(
            playerId: "p1",
            money: 1000m,
            positionIndex: 0,
            economyRules: SanguoEconomyRules.Default);

        var citiesById = new Dictionary<string, City>
        {
            ["c1"] = new City(
                id: "c1",
                name: "City 1",
                regionId: "r1",
                basePrice: MoneyValue.FromDecimal(100m),
                baseToll: MoneyValue.FromDecimal(10m),
                positionIndex: 0),
        };

        var act = async () => await economy.TryBuyCityAndPublishEventAsync(
            gameId: "g1",
            turnNumber: 1,
            players: new[] { player },
            citiesById: citiesById,
            buyerId: "p1",
            cityId: "c1",
            priceMultiplier: 1.25m,
            correlationId: "corr-1",
            causationId: null,
            occurredAt: DateTimeOffset.UtcNow);

        await act.Should().ThrowAsync<ArgumentOutOfRangeException>();
        player.Money.ToDecimal().Should().Be(1000m);
        published.Should().Be(0);
    }
}
