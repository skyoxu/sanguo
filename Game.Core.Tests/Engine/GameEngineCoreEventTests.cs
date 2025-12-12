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
    public void Start_publishes_game_started_event()
    {
        // Arrange
        var engine = CreateEngineAndBus(out var bus);

        // Act
        engine.Start();

        // Assert
        bus.Published.Should().ContainSingle();
        var evt = bus.Published[0];
        evt.Type.Should().Be("game.started");
        evt.Source.Should().Be(nameof(GameEngineCore));
        evt.Data.Should().NotBeNull();
    }

    [Fact]
    public void AddScore_publishes_score_changed_event()
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
        evt.Type.Should().Be("score.changed");
        evt.Source.Should().Be(nameof(GameEngineCore));
        evt.Data.Should().NotBeNull();
    }

    [Fact]
    public void ApplyDamage_publishes_player_health_changed_event()
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
        evt.Type.Should().Be("player.health.changed");
        evt.Source.Should().Be(nameof(GameEngineCore));
        evt.Data.Should().NotBeNull();
    }

    [Fact]
    public void Move_updates_position_and_publishes_event()
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
        evt.Type.Should().Be("player.moved");
        evt.Source.Should().Be(nameof(GameEngineCore));
    }

    [Fact]
    public void End_returns_game_result_with_statistics()
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
        evt.Type.Should().Be("game.ended");
    }

    [Fact]
    public void Engine_with_null_bus_does_not_throw()
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
