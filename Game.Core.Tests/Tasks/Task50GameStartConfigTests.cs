using System;
using System.Collections.Generic;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task50GameStartConfigTests
{
    // ACC:T50.1
    [Fact]
    public void GameStartConfig_ShouldBeConstructible_WithMinimalValidValues()
    {
        var cfg = new GameStartConfig(
            "map001",
            4,
            10000,
            10,
            12345,
            new Dictionary<string, string>(StringComparer.Ordinal)
            {
                ["p1"] = "c_liu_bei",
                ["ai-1"] = "c_cao_cao",
                ["ai-2"] = "c_sun_quan",
                ["ai-3"] = "c_yuan_shao",
            });

        cfg.MapId.Should().Be("map001");
        cfg.PlayersCount.Should().Be(4);
        cfg.StartingMoneyPreset.Should().Be(10000);
        cfg.GlobalEventIntervalTurns.Should().Be(10);
        cfg.RandomSeed.Should().Be(12345);
        cfg.CharacterAssignments.Should().ContainKey("p1");
    }

    // ACC:T50.2
    [Fact]
    public void GameStarted_EventType_ShouldMatchAdr0004Naming()
    {
        SanguoGameStarted.EventType.Should().Be("core.sanguo.game.started");
    }
}
