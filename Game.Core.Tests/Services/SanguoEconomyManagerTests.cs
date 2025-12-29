using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Services;
using Xunit;
namespace Game.Core.Tests.Services;
public class SanguoEconomyManagerTests
{
    // ACC:T7.1
    // ACC:T13.1
    [Fact]
    public void ShouldNotReferenceGodotAssemblies_WhenUsingEconomyManagerServices()
    {
        var referenced = typeof(SanguoEconomyManager).Assembly.GetReferencedAssemblies();
        referenced.Should().NotContain(a => a.Name != null && a.Name.StartsWith("Godot", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void ShouldThrowArgumentNullException_WhenBusIsNull()
    {
        Action act = () => _ = new SanguoEconomyManager(null!);
        act.Should().Throw<ArgumentNullException>().WithParameterName("bus");
    }
    [Fact]
    public async Task ShouldPublishCityBoughtAndUpdateBuyer_WhenCityPurchaseSucceeds()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var city = new City(
            id: "c1",
            name: "CityName",
            regionId: "r1",
            basePrice: Money.FromDecimal(100m),
            baseToll: Money.FromDecimal(10m));
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal) { { city.Id, city } };
        var buyer = new SanguoPlayer(playerId: "buyer", money: 200m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        var players = new[] { buyer };
        var occurredAt = new DateTimeOffset(2025, 1, 1, 0, 0, 0, TimeSpan.Zero);
        var bought = await economy.TryBuyCityAndPublishEventAsync(
            gameId: "game-1",
            players: players,
            citiesById: citiesById,
            buyerId: buyer.PlayerId,
            cityId: city.Id,
            priceMultiplier: 1m,
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: occurredAt);
        bought.Should().BeTrue();
        buyer.OwnedCityIds.Should().Contain(city.Id);
        buyer.Money.Should().Be(Money.FromDecimal(100m));
        bus.Published.Should().ContainSingle(e => e.Type == SanguoCityBought.EventType);
        var evt = bus.Published[0];
        evt.Source.Should().Be(nameof(SanguoEconomyManager));
        evt.Data.Should().BeOfType<JsonElementEventData>();
        var payload = ((JsonElementEventData)evt.Data!).Value;
        payload.GetProperty("GameId").GetString().Should().Be("game-1");
        payload.GetProperty("BuyerId").GetString().Should().Be("buyer");
        payload.GetProperty("CityId").GetString().Should().Be("c1");
        payload.GetProperty("Price").GetDecimal().Should().Be(100m);
        payload.GetProperty("OccurredAt").GetDateTimeOffset().Should().Be(occurredAt);
        payload.GetProperty("CorrelationId").GetString().Should().Be("corr-1");
        payload.GetProperty("CausationId").GetString().Should().Be("cmd-1");
    }
    [Fact]
    public async Task ShouldNotPublishAndNotChangeBuyer_WhenCityOwnedByAnotherPlayer()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var city = new City(
            id: "c1",
            name: "CityName",
            regionId: "r1",
            basePrice: Money.FromDecimal(100m),
            baseToll: Money.FromDecimal(10m));
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal) { { city.Id, city } };
        var owner = new SanguoPlayer(playerId: "owner", money: 200m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        var buyer = new SanguoPlayer(playerId: "buyer", money: 200m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        var players = new[] { owner, buyer };
        owner.TryBuyCity(city, priceMultiplier: 1m).Should().BeTrue();
        var buyerMoneyBefore = buyer.Money;
        var bought = await economy.TryBuyCityAndPublishEventAsync(
            gameId: "game-1",
            players: players,
            citiesById: citiesById,
            buyerId: buyer.PlayerId,
            cityId: city.Id,
            priceMultiplier: 1m,
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);
        bought.Should().BeFalse();
        buyer.Money.Should().Be(buyerMoneyBefore);
        buyer.OwnedCityIds.Should().NotContain(city.Id);
        bus.Published.Should().BeEmpty();
    }
    [Fact]
    public async Task ShouldRollbackBuyerAndThrow_WhenPublishCityBoughtFails()
    {
        var bus = new ThrowingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var city = new City(
            id: "c1",
            name: "CityName",
            regionId: "r1",
            basePrice: Money.FromDecimal(100m),
            baseToll: Money.FromDecimal(10m));
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal) { { city.Id, city } };
        var buyer = new SanguoPlayer(playerId: "buyer", money: 200m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        var players = new[] { buyer };
        var moneyBefore = buyer.Money;
        var ownedBefore = buyer.OwnedCityIds;
        Func<Task> act = async () => await economy.TryBuyCityAndPublishEventAsync(
            gameId: "game-1",
            players: players,
            citiesById: citiesById,
            buyerId: buyer.PlayerId,
            cityId: city.Id,
            priceMultiplier: 1m,
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);
        await act.Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("*Event publish failed after city purchase*");
        buyer.Money.Should().Be(moneyBefore);
        buyer.OwnedCityIds.Should().BeEquivalentTo(ownedBefore);
    }
    [Fact]
    public async Task ShouldReturnFalseAndNotPublish_WhenBuyerNotFound()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var city = new City(
            id: "c1",
            name: "CityName",
            regionId: "r1",
            basePrice: Money.FromDecimal(100m),
            baseToll: Money.FromDecimal(10m));
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal) { { city.Id, city } };
        var players = new[] { new SanguoPlayer(playerId: "p1", money: 200m, positionIndex: 0, economyRules: SanguoEconomyRules.Default) };
        var bought = await economy.TryBuyCityAndPublishEventAsync(
            gameId: "game-1",
            players: players,
            citiesById: citiesById,
            buyerId: "missing",
            cityId: city.Id,
            priceMultiplier: 1m,
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);
        bought.Should().BeFalse();
        bus.Published.Should().BeEmpty();
    }
    [Fact]
    public async Task ShouldPublishCityTollPaidAndUpdateBalances_WhenTollPaymentSucceeds()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var city = new City(
            id: "c1",
            name: "CityName",
            regionId: "r1",
            basePrice: Money.FromDecimal(100m),
            baseToll: Money.FromDecimal(10m));
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal) { { city.Id, city } };
        var owner = new SanguoPlayer(playerId: "owner", money: 200m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        var payer = new SanguoPlayer(playerId: "payer", money: 50m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        var players = new[] { owner, payer };
        owner.TryBuyCity(city, priceMultiplier: 1m).Should().BeTrue();
        var treasury = new SanguoTreasury();
        var occurredAt = new DateTimeOffset(2025, 1, 1, 0, 0, 0, TimeSpan.Zero);
        var paid = await economy.TryPayTollAndPublishEventAsync(
            gameId: "game-1",
            players: players,
            citiesById: citiesById,
            payerId: payer.PlayerId,
            cityId: city.Id,
            tollMultiplier: 1m,
            treasury: treasury,
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: occurredAt);
        paid.Should().BeTrue();
        payer.Money.Should().Be(Money.FromDecimal(40m));
        owner.Money.Should().Be(Money.FromDecimal(110m));
        bus.Published.Should().ContainSingle(e => e.Type == SanguoCityTollPaid.EventType);
        var evt = bus.Published[0];
        evt.Source.Should().Be(nameof(SanguoEconomyManager));
        evt.Data.Should().BeOfType<JsonElementEventData>();
        var payload = ((JsonElementEventData)evt.Data!).Value;
        payload.GetProperty("GameId").GetString().Should().Be("game-1");
        payload.GetProperty("PayerId").GetString().Should().Be("payer");
        payload.GetProperty("OwnerId").GetString().Should().Be("owner");
        payload.GetProperty("CityId").GetString().Should().Be("c1");
        var amount = payload.GetProperty("Amount").GetDecimal();
        var ownerAmount = payload.GetProperty("OwnerAmount").GetDecimal();
        var overflow = payload.GetProperty("TreasuryOverflow").GetDecimal();
        amount.Should().Be(10m);
        ownerAmount.Should().Be(10m);
        overflow.Should().Be(0m);
        amount.Should().Be(ownerAmount + overflow);
        payload.GetProperty("OccurredAt").GetDateTimeOffset().Should().Be(occurredAt);
        payload.GetProperty("CorrelationId").GetString().Should().Be("corr-1");
        payload.GetProperty("CausationId").GetString().Should().Be("cmd-1");
    }
    [Fact]
    public async Task ShouldOverflowToTreasury_WhenOwnerHitsMoneyCap()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var tollCity = new City(
            id: "toll",
            name: "TollCity",
            regionId: "r1",
            basePrice: Money.Zero,
            baseToll: Money.FromDecimal(10m));
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal) { { tollCity.Id, tollCity } };
        var ownerStartMajor = Money.MaxMajorUnits - 5;
        var owner = new SanguoPlayer(playerId: "owner", money: ownerStartMajor, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        var payer = new SanguoPlayer(playerId: "payer", money: 50m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        var players = new[] { owner, payer };
        owner.TryBuyCity(tollCity, priceMultiplier: 1m).Should().BeTrue();
        var treasury = new SanguoTreasury();
        var occurredAt = new DateTimeOffset(2025, 1, 1, 0, 0, 0, TimeSpan.Zero);
        var paid = await economy.TryPayTollAndPublishEventAsync(
            gameId: "game-1",
            players: players,
            citiesById: citiesById,
            payerId: payer.PlayerId,
            cityId: tollCity.Id,
            tollMultiplier: 1m,
            treasury: treasury,
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: occurredAt);
        paid.Should().BeTrue();
        payer.Money.Should().Be(Money.FromDecimal(40m));
        owner.Money.Should().Be(Money.FromMajorUnits(Money.MaxMajorUnits));
        treasury.MinorUnits.Should().BeGreaterThan(0);
        bus.Published.Should().ContainSingle(e => e.Type == SanguoCityTollPaid.EventType);
        var payload = ((JsonElementEventData)bus.Published[0].Data!).Value;
        var amount = payload.GetProperty("Amount").GetDecimal();
        var ownerAmount = payload.GetProperty("OwnerAmount").GetDecimal();
        var overflow = payload.GetProperty("TreasuryOverflow").GetDecimal();
        amount.Should().Be(10m);
        overflow.Should().BeGreaterThan(0m);
        ownerAmount.Should().Be(amount - overflow);
        amount.Should().Be(ownerAmount + overflow);
    }
    [Fact]
    public async Task ShouldRollbackMoneyAndTreasuryAndThrow_WhenPublishTollPaidFails()
    {
        var bus = new ThrowingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var tollCity = new City(
            id: "toll",
            name: "TollCity",
            regionId: "r1",
            basePrice: Money.FromDecimal(100m),
            baseToll: Money.FromDecimal(10m));
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal) { { tollCity.Id, tollCity } };
        var owner = new SanguoPlayer(playerId: "owner", money: 200m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        var payer = new SanguoPlayer(playerId: "payer", money: 50m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        var players = new[] { owner, payer };
        owner.TryBuyCity(tollCity, priceMultiplier: 1m).Should().BeTrue();
        var treasury = new SanguoTreasury();
        var payerMoneyBefore = payer.Money;
        var ownerMoneyBefore = owner.Money;
        var payerOwnedBefore = payer.OwnedCityIds;
        var ownerOwnedBefore = owner.OwnedCityIds;
        var payerEliminatedBefore = payer.IsEliminated;
        var treasuryBefore = treasury.MinorUnits;
        Func<Task> act = async () => await economy.TryPayTollAndPublishEventAsync(
            gameId: "game-1",
            players: players,
            citiesById: citiesById,
            payerId: payer.PlayerId,
            cityId: tollCity.Id,
            tollMultiplier: 1m,
            treasury: treasury,
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);
        await act.Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("*Event publish failed after toll payment*");
        payer.Money.Should().Be(payerMoneyBefore);
        owner.Money.Should().Be(ownerMoneyBefore);
        payer.OwnedCityIds.Should().BeEquivalentTo(payerOwnedBefore);
        owner.OwnedCityIds.Should().BeEquivalentTo(ownerOwnedBefore);
        payer.IsEliminated.Should().Be(payerEliminatedBefore);
        treasury.MinorUnits.Should().Be(treasuryBefore);
    }
    [Fact]
    public async Task ShouldReturnFalseAndNotPublish_WhenCityIsUnowned()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var city = new City(
            id: "c1",
            name: "CityName",
            regionId: "r1",
            basePrice: Money.FromDecimal(100m),
            baseToll: Money.FromDecimal(10m));
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal) { { city.Id, city } };
        var payer = new SanguoPlayer(playerId: "payer", money: 50m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        var players = new[] { payer };
        var payerMoneyBefore = payer.Money;
        var treasury = new SanguoTreasury();
        var paid = await economy.TryPayTollAndPublishEventAsync(
            gameId: "game-1",
            players: players,
            citiesById: citiesById,
            payerId: payer.PlayerId,
            cityId: city.Id,
            tollMultiplier: 1m,
            treasury: treasury,
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);
        paid.Should().BeFalse();
        payer.Money.Should().Be(payerMoneyBefore);
        bus.Published.Should().BeEmpty();
    }
    // ACC:T13.2
    [Fact]
    public async Task ShouldEliminatePayerAndPublish_WhenPayerCannotCoverFullToll()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var tollCity = new City(
            id: "toll",
            name: "TollCity",
            regionId: "r1",
            basePrice: Money.FromDecimal(100m),
            baseToll: Money.FromDecimal(10m));
        var ownedCity = new City(
            id: "owned1",
            name: "OwnedCity",
            regionId: "r1",
            basePrice: Money.FromDecimal(10m),
            baseToll: Money.FromDecimal(1m));
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            { tollCity.Id, tollCity },
            { ownedCity.Id, ownedCity },
        };
        var owner = new SanguoPlayer(playerId: "owner", money: 200m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        var payer = new SanguoPlayer(playerId: "payer", money: 60m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        var players = new[] { owner, payer };
        owner.TryBuyCity(tollCity, priceMultiplier: 1m).Should().BeTrue();
        payer.TryBuyCity(ownedCity, priceMultiplier: 1m).Should().BeTrue();
        payer.OwnedCityIds.Should().Contain(ownedCity.Id);
        var treasury = new SanguoTreasury();
        var occurredAt = new DateTimeOffset(2025, 1, 2, 0, 0, 0, TimeSpan.Zero);
        var paid = await economy.TryPayTollAndPublishEventAsync(
            gameId: "game-1",
            players: players,
            citiesById: citiesById,
            payerId: payer.PlayerId,
            cityId: tollCity.Id,
            tollMultiplier: 10m,
            treasury: treasury,
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: occurredAt);
        paid.Should().BeTrue();
        payer.IsEliminated.Should().BeTrue();
        payer.Money.Should().Be(Money.Zero);
        payer.OwnedCityIds.Should().BeEmpty();
        owner.Money.Should().Be(Money.FromDecimal(150m));
        treasury.MinorUnits.Should().Be(0);
        bus.Published.Should().ContainSingle(e => e.Type == SanguoCityTollPaid.EventType);
        var payload = ((JsonElementEventData)bus.Published[0].Data!).Value;
        var amount = payload.GetProperty("Amount").GetDecimal();
        var ownerAmount = payload.GetProperty("OwnerAmount").GetDecimal();
        var overflow = payload.GetProperty("TreasuryOverflow").GetDecimal();
        amount.Should().Be(50m);
        ownerAmount.Should().Be(50m);
        overflow.Should().Be(0m);
        amount.Should().Be(ownerAmount + overflow);
        payload.GetProperty("OccurredAt").GetDateTimeOffset().Should().Be(occurredAt);
    }
    [Fact]
    public async Task ShouldNotPublishMonthSettled_WhenMonthUnchanged()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        await economy.PublishMonthSettlementIfBoundaryAsync(
            gameId: "game-1",
            previousDate: new DateTime(1, 1, 1),
            currentDate: new DateTime(1, 1, 2),
            settlements: Array.Empty<PlayerSettlement>(),
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);
        bus.Published.Should().BeEmpty();
    }
    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public async Task ShouldThrowArgumentException_WhenGameIdIsEmptyInMonthSettlementBoundary(string? gameId)
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);
        Func<Task> act = async () => await economy.PublishMonthSettlementIfBoundaryAsync(
            gameId: gameId!,
            previousDate: new DateTime(1, 1, 31),
            currentDate: new DateTime(1, 2, 1),
            settlements: Array.Empty<PlayerSettlement>(),
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);
        await act.Should().ThrowAsync<ArgumentException>().WithParameterName("gameId");
    }
    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public async Task ShouldThrowArgumentException_WhenCorrelationIdIsEmptyInMonthSettlementBoundary(string? correlationId)
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);
        Func<Task> act = async () => await economy.PublishMonthSettlementIfBoundaryAsync(
            gameId: "game-1",
            previousDate: new DateTime(1, 1, 31),
            currentDate: new DateTime(1, 2, 1),
            settlements: Array.Empty<PlayerSettlement>(),
            correlationId: correlationId!,
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);
        await act.Should().ThrowAsync<ArgumentException>().WithParameterName("correlationId");
    }
    [Fact]
    public async Task ShouldPublishMonthSettled_WhenMonthChanges()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        await economy.PublishMonthSettlementIfBoundaryAsync(
            gameId: "game-1",
            previousDate: new DateTime(1, 1, 31),
            currentDate: new DateTime(1, 2, 1),
            settlements: Array.Empty<PlayerSettlement>(),
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);
        bus.Published.Should().ContainSingle(e => e.Type == SanguoMonthSettled.EventType);
        var evt = bus.Published[0];
        evt.Source.Should().Be(nameof(SanguoEconomyManager));
        evt.Data.Should().BeOfType<JsonElementEventData>();
        var payload = ((JsonElementEventData)evt.Data!).Value;
        payload.GetProperty("GameId").GetString().Should().Be("game-1");
        payload.GetProperty("Year").GetInt32().Should().Be(1);
        payload.GetProperty("Month").GetInt32().Should().Be(1);
        payload.GetProperty("CorrelationId").GetString().Should().Be("corr-1");
        payload.GetProperty("CausationId").GetString().Should().Be("cmd-1");
        payload.GetProperty("PlayerSettlements").GetArrayLength().Should().Be(0);
    }
    [Fact]
    public async Task ShouldNotPublishSeasonEventApplied_WhenMonthUnchanged()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        await economy.PublishSeasonEventIfBoundaryAsync(
            gameId: "game-1",
            previousDate: new DateTime(1, 1, 1),
            currentDate: new DateTime(1, 1, 2),
            season: 1,
            affectedRegionIds: Array.Empty<string>(),
            yieldMultiplier: 1.0m,
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);
        bus.Published.Should().BeEmpty();
    }
    [Fact]
    public async Task ShouldNotPublishSeasonEventApplied_WhenSeasonUnchanged()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        await economy.PublishSeasonEventIfBoundaryAsync(
            gameId: "game-1",
            previousDate: new DateTime(1, 1, 31),
            currentDate: new DateTime(1, 2, 1),
            season: 1,
            affectedRegionIds: Array.Empty<string>(),
            yieldMultiplier: 1.0m,
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);
        bus.Published.Should().BeEmpty("season event should only be emitted on quarter boundary, not every month change");
    }
    [Fact]
    public async Task ShouldPublishSeasonEventApplied_WhenQuarterBoundaryReached()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        await economy.PublishSeasonEventIfBoundaryAsync(
            gameId: "game-1",
            previousDate: new DateTime(1, 3, 31),
            currentDate: new DateTime(1, 4, 1),
            season: 2,
            affectedRegionIds: new[] { "r1", "r2" },
            yieldMultiplier: 0.8m,
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);
        bus.Published.Should().ContainSingle(e => e.Type == SanguoSeasonEventApplied.EventType);
        var evt = bus.Published[0];
        evt.Source.Should().Be(nameof(SanguoEconomyManager));
        evt.Data.Should().BeOfType<JsonElementEventData>();
        var payload = ((JsonElementEventData)evt.Data!).Value;
        payload.GetProperty("GameId").GetString().Should().Be("game-1");
        payload.GetProperty("Year").GetInt32().Should().Be(1);
        payload.GetProperty("Season").GetInt32().Should().Be(2);
        payload.GetProperty("YieldMultiplier").GetDecimal().Should().Be(0.8m);
        payload.GetProperty("AffectedRegionIds").GetArrayLength().Should().Be(2);
    }
    [Fact]
    public async Task ShouldThrowArgumentOutOfRangeException_WhenSeasonOutOfRangeInSeasonBoundary()
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);
        Func<Task> act = async () => await economy.PublishSeasonEventIfBoundaryAsync(
            gameId: "game-1",
            previousDate: new DateTime(1, 1, 31),
            currentDate: new DateTime(1, 2, 1),
            season: 0,
            affectedRegionIds: Array.Empty<string>(),
            yieldMultiplier: 1.0m,
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);
        await act.Should().ThrowAsync<ArgumentOutOfRangeException>().WithParameterName("season");
    }
    [Fact]
    public async Task ShouldThrowArgumentOutOfRangeException_WhenYieldMultiplierIsNegativeInSeasonBoundary()
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);
        Func<Task> act = async () => await economy.PublishSeasonEventIfBoundaryAsync(
            gameId: "game-1",
            previousDate: new DateTime(1, 1, 31),
            currentDate: new DateTime(1, 2, 1),
            season: 1,
            affectedRegionIds: Array.Empty<string>(),
            yieldMultiplier: -0.1m,
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);
        await act.Should().ThrowAsync<ArgumentOutOfRangeException>().WithParameterName("yieldMultiplier");
    }
    [Fact]
    public async Task ShouldNotPublishYearlyPriceAdjusted_WhenYearUnchanged()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var cities = new[]
        {
            new City("c1", "City1", "r1", Money.FromMajorUnits(100), Money.FromMajorUnits(10)),
        };
        await economy.PublishYearlyPriceAdjustmentIfBoundaryAsync(
            gameId: "game-1",
            previousDate: new DateTime(1, 12, 31),
            currentDate: new DateTime(1, 1, 1),
            cities: cities,
            yearlyMultiplier: 1.10m,
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);
        bus.Published.Should().BeEmpty();
    }
    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public async Task ShouldThrowArgumentException_WhenGameIdIsEmptyInYearlyPriceBoundary(string? gameId)
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);
        Func<Task> act = async () => await economy.PublishYearlyPriceAdjustmentIfBoundaryAsync(
            gameId: gameId!,
            previousDate: new DateTime(1, 12, 31),
            currentDate: new DateTime(2, 1, 1),
            cities: Array.Empty<City>(),
            yearlyMultiplier: 1.10m,
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);
        await act.Should().ThrowAsync<ArgumentException>().WithParameterName("gameId");
    }
    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public async Task ShouldThrowArgumentException_WhenCorrelationIdIsEmptyInYearlyPriceBoundary(string? correlationId)
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);
        Func<Task> act = async () => await economy.PublishYearlyPriceAdjustmentIfBoundaryAsync(
            gameId: "game-1",
            previousDate: new DateTime(1, 12, 31),
            currentDate: new DateTime(2, 1, 1),
            cities: Array.Empty<City>(),
            yearlyMultiplier: 1.10m,
            correlationId: correlationId!,
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);
        await act.Should().ThrowAsync<ArgumentException>().WithParameterName("correlationId");
    }
    [Fact]
    public async Task ShouldPublishYearlyPriceAdjustedPerCity_WhenYearChanges()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var cities = new[]
        {
            new City("c1", "City1", "r1", Money.FromMajorUnits(100), Money.FromMajorUnits(10)),
            new City("c2", "City2", "r2", Money.FromMajorUnits(200), Money.FromMajorUnits(20)),
        };
        await economy.PublishYearlyPriceAdjustmentIfBoundaryAsync(
            gameId: "game-1",
            previousDate: new DateTime(1, 12, 31),
            currentDate: new DateTime(2, 1, 1),
            cities: cities,
            yearlyMultiplier: 1.10m,
            correlationId: "corr-1",
            causationId: "cmd-1",
            occurredAt: DateTimeOffset.UtcNow);
        bus.Published.Should().HaveCount(2);
        bus.Published.Should().OnlyContain(e => e.Type == SanguoYearPriceAdjusted.EventType);
        foreach (var evt in bus.Published)
        {
            evt.Source.Should().Be(nameof(SanguoEconomyManager));
            evt.Data.Should().BeOfType<JsonElementEventData>();
            var payload = ((JsonElementEventData)evt.Data!).Value;
            payload.GetProperty("GameId").GetString().Should().Be("game-1");
            payload.GetProperty("Year").GetInt32().Should().Be(1);
            payload.GetProperty("CorrelationId").GetString().Should().Be("corr-1");
            payload.GetProperty("CausationId").GetString().Should().Be("cmd-1");
        }
    }
    [Fact]
    public void ShouldSumBaseTollOfOwnedCities_WhenCalculatingMonthSettlements()
    {
        var bus = NullEventBus.Instance;
        var economy = new SanguoEconomyManager(bus);
        var cities = new Dictionary<string, City>
        {
            ["c1"] = new City("c1", "City1", "r1", Money.FromMajorUnits(100), Money.FromMajorUnits(10)),
            ["c2"] = new City("c2", "City2", "r1", Money.FromMajorUnits(200), Money.FromMajorUnits(15)),
        };
        var player = new PlayerView(
            playerId: "p1",
            ownedCityIds: new[] { "c1", "c2" });
        var settlements = economy.CalculateMonthSettlements(new[] { player }, cities);
        settlements.Should().ContainSingle();
        settlements[0].PlayerId.Should().Be("p1");
        settlements[0].AmountDelta.Should().Be(25m);
    }
    [Fact]
    public void ShouldThrowArgumentNullException_WhenPlayersIsNullInMonthSettlementCalculation()
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);
        Action act = () => _ = economy.CalculateMonthSettlements(
            players: null!,
            citiesById: new Dictionary<string, City>());
        act.Should().Throw<ArgumentNullException>().WithParameterName("players");
    }
    [Fact]
    public void ShouldThrowArgumentNullException_WhenCitiesByIdIsNullInMonthSettlementCalculation()
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);
        var player = new PlayerView(playerId: "p1", ownedCityIds: Array.Empty<string>());
        Action act = () => _ = economy.CalculateMonthSettlements(
            players: new[] { player },
            citiesById: null!);
        act.Should().Throw<ArgumentNullException>().WithParameterName("citiesById");
    }
    [Fact]
    public void ShouldSkipEliminatedPlayers_WhenCalculatingMonthSettlements()
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);
        var cities = new Dictionary<string, City>
        {
            ["c1"] = new City("c1", "City1", "r1", Money.FromMajorUnits(100), Money.FromMajorUnits(10)),
        };
        var eliminated = new PlayerView(
            playerId: "p1",
            ownedCityIds: new[] { "c1" },
            isEliminated: true);
        var settlements = economy.CalculateMonthSettlements(new[] { eliminated }, cities);
        settlements.Should().BeEmpty();
    }
    [Fact]
    public void ShouldThrowInvalidOperationException_WhenOwnedCityMissingInMonthSettlementCalculation()
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);
        var cities = new Dictionary<string, City>();
        var player = new PlayerView(
            playerId: "p1",
            ownedCityIds: new[] { "missing-city" });
        Action act = () => _ = economy.CalculateMonthSettlements(new[] { player }, cities);
        act.Should().Throw<InvalidOperationException>()
            .WithMessage("Owned city id not found:*");
    }
    [Fact]
    public void ShouldComputeNewPriceUsingMultiplier_WhenCalculatingYearlyPriceAdjustments()
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);
        var cities = new[]
        {
            new City("c1", "City1", "r1", Money.FromMajorUnits(100), Money.FromMajorUnits(10)),
        };
        var adjustments = economy.CalculateYearlyPriceAdjustments(cities, yearlyMultiplier: 1.10m);
        adjustments.Should().ContainSingle();
        adjustments[0].CityId.Should().Be("c1");
        adjustments[0].OldPrice.ToDecimal().Should().Be(100m);
        adjustments[0].NewPrice.ToDecimal().Should().Be(110m);
    }
    [Fact]
    public void ShouldThrowArgumentOutOfRangeException_WhenMultiplierIsNegativeInYearlyPriceAdjustmentCalculation()
    {
        var economy = new SanguoEconomyManager(NullEventBus.Instance);
        Action act = () => _ = economy.CalculateYearlyPriceAdjustments(
            cities: Array.Empty<City>(),
            yearlyMultiplier: -0.1m);
        act.Should().Throw<ArgumentOutOfRangeException>()
            .WithParameterName("yearlyMultiplier");
    }
    private sealed class PlayerView : ISanguoPlayerView
    {
        public PlayerView(string playerId, IReadOnlyCollection<string> ownedCityIds, bool isEliminated = false)
        {
            PlayerId = playerId;
            OwnedCityIds = ownedCityIds;
            IsEliminated = isEliminated;
        }
        public string PlayerId { get; }
        public Money Money => Money.Zero;
        public int PositionIndex => 0;
        public IReadOnlyCollection<string> OwnedCityIds { get; }
        public bool IsEliminated { get; }
    }
    private sealed class CapturingEventBus : IEventBus
    {
        public List<DomainEvent> Published { get; } = new();
        public Task PublishAsync(DomainEvent evt)
        {
            Published.Add(evt);
            return Task.CompletedTask;
        }
        public IDisposable Subscribe(Func<DomainEvent, Task> handler) => new DummySubscription();
        private sealed class DummySubscription : IDisposable
        {
            public void Dispose()
            {
            }
        }
    }
    private sealed class ThrowingEventBus : IEventBus
    {
        public Task PublishAsync(DomainEvent evt) => throw new InvalidOperationException("publish failed");
        public IDisposable Subscribe(Func<DomainEvent, Task> handler) => new DummySubscription();
        private sealed class DummySubscription : IDisposable
        {
            public void Dispose()
            {
            }
        }
    }
}
