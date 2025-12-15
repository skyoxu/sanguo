using System;
using FluentAssertions;
using Game.Core.Domain;
using Game.Core.Engine;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Engine;

public class GameEngineCoreConstructorTests
{
    private static GameConfig DefaultConfig() =>
        new(
            MaxLevel: 10,
            InitialHealth: 100,
            ScoreMultiplier: 1.0,
            AutoSave: false,
            Difficulty: Difficulty.Medium
        );

    [Fact]
    public void Constructor_WhenEventBusIsNull_ShouldThrowArgumentNullException()
    {
        var config = DefaultConfig();
        var inventory = new Inventory();

        Action act = () => new GameEngineCore(config, inventory, bus: null!, scoreService: new ScoreService());

        act.Should().Throw<ArgumentNullException>()
            .WithParameterName("bus");
    }

    [Fact]
    public void Constructor_WhenScoreServiceIsNull_ShouldThrowArgumentNullException()
    {
        var config = DefaultConfig();
        var inventory = new Inventory();

        Action act = () => new GameEngineCore(config, inventory, bus: NullEventBus.Instance, scoreService: null!);

        act.Should().Throw<ArgumentNullException>()
            .WithParameterName("scoreService");
    }
}

