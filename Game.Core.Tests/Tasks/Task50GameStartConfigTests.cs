using System;
using System.Collections.Generic;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task50GameStartConfigTests
{
    // ACC:T50.1
    [Fact]
    public void ShouldBeConstructible_WhenUsingMinimalValidValues()
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
    public void ShouldMatchAdr0004Naming_WhenCheckingGameStartedEventType()
    {
        SanguoGameStarted.EventType.Should().Be("core.sanguo.game.started");
    }

    // ACC:T50.1
    [Theory]
    [InlineData(3)]
    [InlineData(9)]
    public void ShouldRejectConfig_WhenPlayersCountIsInvalid(int invalidPlayersCount)
    {
        var cfg = new GameStartConfig(
            "map001",
            invalidPlayersCount,
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

        GameStartConfigValidator.TryValidate(cfg, out var errors).Should().BeFalse();
        errors.Should().NotBeEmpty();
    }

    // ACC:T50.1
    [Theory]
    [InlineData(0)]
    [InlineData(123)]
    public void ShouldRejectConfig_WhenStartingMoneyPresetIsInvalid(int invalidPreset)
    {
        var cfg = new GameStartConfig(
            "map001",
            4,
            invalidPreset,
            10,
            12345,
            new Dictionary<string, string>(StringComparer.Ordinal)
            {
                ["p1"] = "c_liu_bei",
                ["ai-1"] = "c_cao_cao",
                ["ai-2"] = "c_sun_quan",
                ["ai-3"] = "c_yuan_shao",
            });

        GameStartConfigValidator.TryValidate(cfg, out var errors).Should().BeFalse();
        errors.Should().Contain(e => e.StartsWith("starting_money_preset_invalid:", StringComparison.Ordinal));
    }

    // ACC:T50.1
    [Theory]
    [InlineData(0)]
    [InlineData(99)]
    public void ShouldRejectConfig_WhenGlobalEventIntervalTurnsIsInvalid(int invalidInterval)
    {
        var cfg = new GameStartConfig(
            "map001",
            4,
            10000,
            invalidInterval,
            12345,
            new Dictionary<string, string>(StringComparer.Ordinal)
            {
                ["p1"] = "c_liu_bei",
                ["ai-1"] = "c_cao_cao",
                ["ai-2"] = "c_sun_quan",
                ["ai-3"] = "c_yuan_shao",
            });

        GameStartConfigValidator.TryValidate(cfg, out var errors).Should().BeFalse();
        errors.Should().Contain(e => e.StartsWith("global_event_interval_turns_invalid:", StringComparison.Ordinal));
    }

    // ACC:T50.1
    [Fact]
    public void ShouldRejectConfig_WhenCharacterAssignmentsContainDuplicates()
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
                ["ai-1"] = "c_liu_bei",
                ["ai-2"] = "c_sun_quan",
                ["ai-3"] = "c_yuan_shao",
            });

        GameStartConfigValidator.TryValidate(cfg, out var errors).Should().BeFalse();
        errors.Should().Contain("character_assignments_has_duplicates");
    }

    // ACC:T50.1
    [Fact]
    public void ShouldAcceptConfig_WhenValuesAreValid()
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

        GameStartConfigValidator.TryValidate(cfg, out var errors).Should().BeTrue();
        errors.Should().BeEmpty();
    }

    // ACC:T50.1
    [Fact]
    public void ShouldRejectConfig_WhenConfigIsNull()
    {
        GameStartConfigValidator.TryValidate(cfg: null!, out var errors).Should().BeFalse();
        errors.Should().Contain("cfg_null");
    }

    // ACC:T50.1
    [Fact]
    public void ShouldCollectMultipleErrors_WhenConfigIsInvalid()
    {
        var cfg = new GameStartConfig(
            MapId: "",
            PlayersCount: 3,
            StartingMoneyPreset: 0,
            GlobalEventIntervalTurns: 0,
            RandomSeed: 12345,
            CharacterAssignments: new Dictionary<string, string>(StringComparer.Ordinal)
            {
                [""] = "",
                ["p1"] = "c_liu_bei",
            });

        GameStartConfigValidator.TryValidate(cfg, out var errors).Should().BeFalse();
        errors.Should().Contain("map_id_empty");
        errors.Should().Contain(e => e.StartsWith("players_count_invalid:", StringComparison.Ordinal));
        errors.Should().Contain(e => e.StartsWith("starting_money_preset_invalid:", StringComparison.Ordinal));
        errors.Should().Contain(e => e.StartsWith("global_event_interval_turns_invalid:", StringComparison.Ordinal));
        errors.Should().Contain("character_assignments_has_empty_player_id");
        errors.Should().Contain("character_assignments_has_empty_character_id");
    }

    // ACC:T50.1
    [Fact]
    public void ShouldRejectConfig_WhenCharacterAssignmentsIsNull()
    {
        var cfg = new GameStartConfig(
            MapId: "map001",
            PlayersCount: 4,
            StartingMoneyPreset: 10000,
            GlobalEventIntervalTurns: 10,
            RandomSeed: 12345,
            CharacterAssignments: null!);

        GameStartConfigValidator.TryValidate(cfg, out var errors).Should().BeFalse();
        errors.Should().Contain("character_assignments_null");
    }

    // ACC:T50.4
    [Fact]
    public void ShouldRoundTripThroughJsonAuditSnapshot_WhenSerializingAndDeserializing()
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

        var json = JsonSerializer.Serialize(cfg);
        var roundTripped = JsonSerializer.Deserialize<GameStartConfig>(json);

        roundTripped.Should().NotBeNull();
        roundTripped.Should().BeEquivalentTo(cfg);
    }
}
