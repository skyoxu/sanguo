// Acceptance anchors:
// ACC:T5.1
// ACC:T5.2

using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Services;

public class SanguoDiceServiceTests
{
    [Fact]
    public void ShouldThrowArgumentNullException_WhenBusIsNull()
    {
        Action act = () => new SanguoDiceService(null!);

        act.Should().Throw<ArgumentNullException>()
            .WithParameterName("bus");
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void ShouldThrowArgumentException_WhenGameIdIsNullOrWhitespace(string? gameId)
    {
        var bus = new CapturingEventBus();
        var svc = new SanguoDiceService(bus);

        Action act = () => svc.RollD6(gameId!, "p1", "corr-1", causationId: null);

        act.Should().Throw<ArgumentException>()
            .WithParameterName("gameId");
        bus.Published.Should().BeEmpty();
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void ShouldThrowArgumentException_WhenPlayerIdIsNullOrWhitespace(string? playerId)
    {
        var bus = new CapturingEventBus();
        var svc = new SanguoDiceService(bus);

        Action act = () => svc.RollD6("game-1", playerId!, "corr-1", causationId: null);

        act.Should().Throw<ArgumentException>()
            .WithParameterName("playerId");
        bus.Published.Should().BeEmpty();
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void ShouldThrowArgumentException_WhenCorrelationIdIsNullOrWhitespace(string? correlationId)
    {
        var bus = new CapturingEventBus();
        var svc = new SanguoDiceService(bus);

        Action act = () => svc.RollD6("game-1", "p1", correlationId!, causationId: null);

        act.Should().Throw<ArgumentException>()
            .WithParameterName("correlationId");
        bus.Published.Should().BeEmpty();
    }

    [Fact]
    public void ShouldPublishSanguoDiceRolledDomainEvent_WhenRollingD6()
    {
        var bus = new CapturingEventBus();
        var svc = new SanguoDiceService(bus);

        var gameId = "game-1";
        var playerId = "p1";
        var correlationId = "corr-1";
        var causationId = "cause-1";

        var value = svc.RollD6(gameId, playerId, correlationId, causationId);

        value.Should().BeInRange(1, 6);
        bus.Published.Should().ContainSingle();

        var evt = bus.Published[0];
        evt.Type.Should().Be(SanguoDiceRolled.EventType);
        evt.Source.Should().Be("SanguoDiceService");
        evt.Data.Should().BeOfType<JsonElementEventData>();

        var payload = ((JsonElementEventData)evt.Data!).Value;
        payload.GetProperty("GameId").GetString().Should().Be(gameId);
        payload.GetProperty("PlayerId").GetString().Should().Be(playerId);
        payload.GetProperty("Value").GetInt32().Should().Be(value);
        payload.GetProperty("CorrelationId").GetString().Should().Be(correlationId);
        payload.GetProperty("CausationId").GetString().Should().Be(causationId);
        payload.TryGetProperty("OccurredAt", out _).Should().BeTrue();
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
