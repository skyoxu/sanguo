using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Services;

public sealed class SanguoEconomyManagerFailureTests
{
    [Fact]
    public async Task TryBuyCityAndPublishEventAsync_ShouldReturnFalse_WhenBuyerHasInsufficientFunds()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var rules = SanguoEconomyRules.Default;
        var buyer = new SanguoPlayer(playerId: "p1", money: 0m, positionIndex: 0, economyRules: rules);
        var players = new List<SanguoPlayer> { buyer };

        var city = new City(id: "c1", name: "City1", regionId: "r1", basePrice: Money.FromMajorUnits(100), baseToll: Money.FromMajorUnits(1), positionIndex: 0);
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city };

        var ok = await economy.TryBuyCityAndPublishEventAsync(
            gameId: "game-1",
            players: players,
            citiesById: citiesById,
            buyerId: buyer.PlayerId,
            cityId: city.Id,
            priceMultiplier: 1.0m,
            correlationId: "corr-1",
            causationId: null,
            occurredAt: DateTimeOffset.UtcNow);

        ok.Should().BeFalse();
        bus.Published.Should().NotContain(e => e.Type == SanguoCityBought.EventType);
        buyer.OwnsCityId(city.Id).Should().BeFalse();
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
}

