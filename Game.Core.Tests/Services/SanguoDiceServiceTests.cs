using System;
using System.Collections.Generic;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Services;
using Game.Core.Utilities;
using Xunit;
namespace Game.Core.Tests.Services;
public class SanguoDiceServiceTests
{
    // ACC:T5.1
    [Fact]
    public void ShouldNotReferenceGodotAssemblies_WhenUsingDiceServiceInGameCore()
    {
        var referenced = typeof(SanguoDiceService).Assembly.GetReferencedAssemblies();
        referenced.Should().NotContain(a => a.Name != null && a.Name.StartsWith("Godot", StringComparison.OrdinalIgnoreCase));
    }

    // ACC:T5.2
    [Fact]
    public void ShouldThrowArgumentNullException_WhenBusIsNull()
    {
        Action act = () => new SanguoDiceService(null!);
        act.Should().Throw<ArgumentNullException>()
            .WithParameterName("bus");
    }
    // ACC:T5.3
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
    // ACC:T5.4
    [Fact]
    public void ShouldPublishSanguoDiceRolledDomainEvent_WhenRollingD6()
    {
        var bus = new CapturingEventBus();
        var svc = new SanguoDiceService(bus);
        var gameId = "game-1";
        var playerId = "p1";
        var correlationId = "corr-1";
        var causationId = "cause-1";

        SanguoDiceRolled.EventType.Should().Be("core.sanguo.dice.rolled");

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

    // ACC:T5.5
    [Fact]
    public void ShouldUseInjectedRandomNumberGenerator_WhenRollingD6()
    {
        var bus = new CapturingEventBus();
        var rng = new FixedRng(nextIntValue: 3);
        var svc = new SanguoDiceService(bus, rng);

        var value = svc.RollD6(gameId: "game-1", playerId: "p1", correlationId: "corr-1", causationId: null);

        value.Should().Be(3);
        rng.NextIntCalls.Should().BeGreaterOrEqualTo(1);
        rng.LastNextIntMinInclusive.Should().Be(1);
        rng.LastNextIntMaxExclusive.Should().Be(7);

        bus.Published.Should().ContainSingle();
        var payload = ((JsonElementEventData)bus.Published[0].Data!).Value;
        payload.GetProperty("Value").GetInt32().Should().Be(3);
    }

    // ACC:T5.6
    [Fact]
    public void ShouldUseDefaultSystemRandomSource_WhenNoRngIsInjected()
    {
        var rngField = typeof(RandomHelper).GetField("_rng", BindingFlags.NonPublic | BindingFlags.Static);
        rngField.Should().NotBeNull();

        var threadLocalRng = rngField!.GetValue(null).Should().BeAssignableTo<ThreadLocal<Random>>().Subject;

        var originalRandom = threadLocalRng.Value;
        try
        {
            var fixedRandom = new FixedRandom(nextValueInclusive: 6);
            threadLocalRng.Value = fixedRandom;

            var bus = new CapturingEventBus();
            var svc = new SanguoDiceService(bus, rng: null);

            var value = svc.RollD6(gameId: "game-1", playerId: "p1", correlationId: "corr-1", causationId: null);

            value.Should().Be(6);
            fixedRandom.NextCalls.Should().BeGreaterOrEqualTo(1);
            bus.Published.Should().ContainSingle();
            var payload = ((JsonElementEventData)bus.Published[0].Data!).Value;
            payload.GetProperty("Value").GetInt32().Should().Be(6);
        }
        finally
        {
            threadLocalRng.Value = originalRandom;
        }
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

    private sealed class FixedRng : IRandomNumberGenerator
    {
        private readonly int _nextIntValue;

        public int NextIntCalls { get; private set; }

        public int? LastNextIntMinInclusive { get; private set; }

        public int? LastNextIntMaxExclusive { get; private set; }

        public FixedRng(int nextIntValue)
        {
            _nextIntValue = nextIntValue;
        }

        public int NextInt(int minInclusive, int maxExclusive)
        {
            NextIntCalls++;
            LastNextIntMinInclusive = minInclusive;
            LastNextIntMaxExclusive = maxExclusive;
            return _nextIntValue;
        }

        public double NextDouble() => 0.5;
    }

    private sealed class FixedRandom : Random
    {
        private readonly int _nextValueInclusive;

        public FixedRandom(int nextValueInclusive)
        {
            _nextValueInclusive = nextValueInclusive;
        }

        public int NextCalls { get; private set; }

        public override int Next(int minValue, int maxValue)
        {
            NextCalls++;
            _nextValueInclusive.Should().BeInRange(minValue, maxValue - 1);
            return _nextValueInclusive;
        }
    }
}
