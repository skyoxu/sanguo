using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Engine;
using Game.Core.Services;
using Xunit;

using static Game.Core.Contracts.CoreGameEvents;

namespace Game.Core.Tests.Engine;

public class GameEngineCoreEventTests
{
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

    private static GameEngineCore CreateEngineAndBus(out CapturingEventBus bus)
    {
        var config = new GameConfig(
            MaxLevel: 10,
            InitialHealth: 100,
            ScoreMultiplier: 1.0,
            AutoSave: false,
            Difficulty: Difficulty.Medium
        );
        var inventory = new Inventory();
        bus = new CapturingEventBus();
        return new GameEngineCore(config, inventory, bus);
    }

    [Fact]
    public void StartPublishesGameStartedEvent()
    {
        // Arrange
        var engine = CreateEngineAndBus(out var bus);

        // Act
        engine.Start();

        // Assert
        bus.Published.Should().ContainSingle();
        var evt = bus.Published[0];
        evt.Type.Should().Be(GameStarted);
        evt.Source.Should().Be(nameof(GameEngineCore));
        evt.Data.Should().NotBeNull();
    }

    [Fact]
    public void AddScorePublishesScoreChangedEvent()
    {
        // Arrange
        var engine = CreateEngineAndBus(out var bus);
        engine.Start();
        bus.Published.Clear();

        // Act
        engine.AddScore(10);

        // Assert
        bus.Published.Should().ContainSingle();
        var evt = bus.Published[0];
        evt.Type.Should().Be(ScoreChanged);
        evt.Source.Should().Be(nameof(GameEngineCore));
        evt.Data.Should().NotBeNull();
    }

    [Fact]
    public void ApplyDamagePublishesPlayerHealthChangedEvent()
    {
        // Arrange
        var engine = CreateEngineAndBus(out var bus);
        engine.Start();
        bus.Published.Clear();

        // Act
        engine.ApplyDamage(new Damage(Amount: 10, Type: DamageType.Physical, IsCritical: false));

        // Assert
        bus.Published.Should().ContainSingle();
        var evt = bus.Published[0];
        evt.Type.Should().Be(PlayerHealthChanged);
        evt.Source.Should().Be(nameof(GameEngineCore));
        evt.Data.Should().NotBeNull();
    }

    [Fact]
    public void MoveUpdatesPositionAndPublishesEvent()
    {
        // Arrange
        var engine = CreateEngineAndBus(out var bus);
        engine.Start();
        bus.Published.Clear();

        // Act
        var result = engine.Move(10, 20);

        // Assert
        result.Position.X.Should().Be(10);
        bus.Published.Should().ContainSingle();
        var evt = bus.Published[0];
        evt.Type.Should().Be(PlayerMoved);
        evt.Source.Should().Be(nameof(GameEngineCore));
    }

    [Fact]
    public void EndReturnsGameResultWithStatistics()
    {
        // Arrange
        var engine = CreateEngineAndBus(out var bus);
        engine.Start();
        engine.Move(5, 10);
        engine.AddScore(100);
        bus.Published.Clear();

        // Act
        var result = engine.End();

        // Assert
        result.FinalScore.Should().Be(100);
        result.LevelReached.Should().Be(1);
        result.PlayTimeSeconds.Should().BeGreaterThan(0);
        bus.Published.Should().ContainSingle();
        var evt = bus.Published[0];
        evt.Type.Should().Be(GameEnded);
    }

    [Fact]
    public void EngineWithNullBusDoesNotThrow()
    {
        // Arrange
        var config = new GameConfig(
            MaxLevel: 10,
            InitialHealth: 100,
            ScoreMultiplier: 1.0,
            AutoSave: false,
            Difficulty: Difficulty.Medium
        );
        var inventory = new Inventory();
        var engine = new GameEngineCore(config, inventory, bus: null);

        // Act & Assert - should not throw when bus is null
        engine.Start();
        engine.Move(1, 1);
        engine.AddScore(10);
        engine.ApplyDamage(new Damage(5, DamageType.Physical, false));
        var result = engine.End();

        result.Should().NotBeNull();
    }
}
