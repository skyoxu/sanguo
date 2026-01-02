using System;
using System.Collections.Generic;
using FluentAssertions;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Services;

public sealed class SanguoEconomyManagerSeasonYieldAdjustmentTests
{
    [Fact]
    public void ShouldApplyAndClearSeasonYieldAdjustment_WhenCalculatingMonthSettlements()
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);

        var player = new SanguoPlayer(playerId: "p1", money: 1_000m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new City("c1", "City1", "r1", Money.FromMajorUnits(1), Money.FromMajorUnits(10)),
            ["c2"] = new City("c2", "City2", "r2", Money.FromMajorUnits(1), Money.FromMajorUnits(20)),
        };
        var boardState = new SanguoBoardState(players: new[] { player }, citiesById: citiesById);
        boardState.TryBuyCity(buyerId: "p1", cityId: "c1", priceMultiplier: 1.0m).Should().BeTrue();
        boardState.TryBuyCity(buyerId: "p1", cityId: "c2", priceMultiplier: 1.0m).Should().BeTrue();

        economy.SetActiveSeasonYieldAdjustment(
            year: 1,
            season: 2,
            affectedRegionIds: new[] { "r1" },
            yieldMultiplier: 0.9m);

        var adjusted = economy.CalculateMonthSettlements(
            players: new[] { player },
            citiesById: boardState.GetCitiesSnapshot());
        adjusted.Should().ContainSingle();
        adjusted[0].AmountDelta.Should().Be(29m);

        economy.SetActiveSeasonYieldAdjustment(
            year: 1,
            season: 3,
            affectedRegionIds: new[] { "r1" },
            yieldMultiplier: 1.0m);

        var baseline = economy.CalculateMonthSettlements(
            players: new[] { player },
            citiesById: boardState.GetCitiesSnapshot());
        baseline.Should().ContainSingle();
        baseline[0].AmountDelta.Should().Be(30m);
    }

    [Fact]
    public void ShouldClearSeasonYieldAdjustment_WhenAffectedRegionsAreWhitespaceOnly()
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);

        var player = new SanguoPlayer(playerId: "p1", money: 1_000m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        var boardState = new SanguoBoardState(
            players: new[] { player },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal)
            {
                ["c1"] = new City("c1", "City1", "r1", Money.FromMajorUnits(1), Money.FromMajorUnits(10)),
            });
        boardState.TryBuyCity(buyerId: "p1", cityId: "c1", priceMultiplier: 1.0m).Should().BeTrue();

        economy.SetActiveSeasonYieldAdjustment(
            year: 1,
            season: 2,
            affectedRegionIds: new[] { " ", "\t", "\n" },
            yieldMultiplier: 0.9m);

        var settlements = economy.CalculateMonthSettlements(
            players: new[] { player },
            citiesById: boardState.GetCitiesSnapshot());
        settlements.Should().ContainSingle();
        settlements[0].AmountDelta.Should().Be(10m);
    }

    [Fact]
    public void ShouldThrow_WhenSettingSeasonYieldAdjustmentWithInvalidParameters()
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);

        economy.Invoking(e => e.SetActiveSeasonYieldAdjustment(
                year: -1,
                season: 1,
                affectedRegionIds: Array.Empty<string>(),
                yieldMultiplier: 1.0m))
            .Should().Throw<ArgumentOutOfRangeException>();

        economy.Invoking(e => e.SetActiveSeasonYieldAdjustment(
                year: 1,
                season: 0,
                affectedRegionIds: Array.Empty<string>(),
                yieldMultiplier: 1.0m))
            .Should().Throw<ArgumentOutOfRangeException>();

        economy.Invoking(e => e.SetActiveSeasonYieldAdjustment(
                year: 1,
                season: 1,
                affectedRegionIds: Array.Empty<string>(),
                yieldMultiplier: -0.1m))
            .Should().Throw<ArgumentOutOfRangeException>();
    }
}
