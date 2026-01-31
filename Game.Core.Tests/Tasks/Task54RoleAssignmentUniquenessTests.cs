using System;
using System.Collections.Generic;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task54RoleAssignmentUniquenessTests
{
    private static readonly string[] AvailableIds =
    {
        "c1",
        "c2",
        "c3",
        "c4",
        "c5",
        "c6",
        "c7",
        "c8",
    };

    // ACC:T54.2
    [Fact]
    public void GivenPlayersCountAndSeed_WhenBuildingAssignments_ThenFillsAiSlotsWithUniqueRoles()
    {
        var ok = SanguoCharacterAssignmentsGenerator.TryBuildAssignments(
            availableCharacterIds: AvailableIds,
            playersCount: 8,
            playerCharacterId: "c3",
            seed: 123,
            assignments: out var assigns,
            error: out var error);

        ok.Should().BeTrue(error);
        assigns.Should().NotBeNull();
        assigns.Should().HaveCount(8);
        assigns.Should().ContainKey("p1");
        assigns["p1"].Should().Be("c3");
        assigns.Keys.Should().Contain(new[] { "ai-1", "ai-2", "ai-3", "ai-4", "ai-5", "ai-6", "ai-7" });
        assigns.Values.Should().OnlyHaveUniqueItems();
        assigns.Values.Should().NotContainNulls();
        assigns.Values.Should().NotContain(x => string.IsNullOrWhiteSpace(x));
    }

    // ACC:T54.3
    [Fact]
    public void GivenSameInput_WhenBuildingAssignmentsTwice_ThenResultsAreDeterministicAndUnique()
    {
        var ok1 = SanguoCharacterAssignmentsGenerator.TryBuildAssignments(
            availableCharacterIds: AvailableIds,
            playersCount: 8,
            playerCharacterId: "c3",
            seed: 999,
            assignments: out var a,
            error: out var e1);
        ok1.Should().BeTrue(e1);

        var ok2 = SanguoCharacterAssignmentsGenerator.TryBuildAssignments(
            availableCharacterIds: AvailableIds,
            playersCount: 8,
            playerCharacterId: "c3",
            seed: 999,
            assignments: out var b,
            error: out var e2);
        ok2.Should().BeTrue(e2);

        a.Should().Equal(b);
        a.Values.Should().OnlyHaveUniqueItems();
    }

    [Fact]
    public void GivenInsufficientCharacters_WhenBuildingAssignments_ThenFailsWithExpectedError()
    {
        var ok = SanguoCharacterAssignmentsGenerator.TryBuildAssignments(
            availableCharacterIds: new[] { "c1", "c2", "c3" },
            playersCount: 4,
            playerCharacterId: "c1",
            seed: 1,
            assignments: out _,
            error: out var error);

        ok.Should().BeFalse();
        error.Should().Be("insufficient_characters");
    }

    [Fact]
    public void GivenZeroPlayers_WhenBuildingAssignments_ThenFailsWithExpectedError()
    {
        var ok = SanguoCharacterAssignmentsGenerator.TryBuildAssignments(
            availableCharacterIds: AvailableIds,
            playersCount: 0,
            playerCharacterId: "c1",
            seed: 1,
            assignments: out _,
            error: out var error);

        ok.Should().BeFalse();
        error.Should().Be("players_count_invalid");
    }

    [Fact]
    public void GivenEmptyPlayerCharacter_WhenBuildingAssignments_ThenFailsWithExpectedError()
    {
        var ok = SanguoCharacterAssignmentsGenerator.TryBuildAssignments(
            availableCharacterIds: AvailableIds,
            playersCount: 4,
            playerCharacterId: "",
            seed: 1,
            assignments: out _,
            error: out var error);

        ok.Should().BeFalse();
        error.Should().Be("player_character_empty");
    }

    [Fact]
    public void GivenEmptyAvailableCharacters_WhenBuildingAssignments_ThenFailsWithExpectedError()
    {
        var ok = SanguoCharacterAssignmentsGenerator.TryBuildAssignments(
            availableCharacterIds: Array.Empty<string>(),
            playersCount: 2,
            playerCharacterId: "c1",
            seed: 1,
            assignments: out _,
            error: out var error);

        ok.Should().BeFalse();
        error.Should().Be("insufficient_characters");
    }

    [Fact]
    public void GivenMissingPlayerCharacter_WhenBuildingAssignments_ThenFailsWithExpectedError()
    {
        var ok = SanguoCharacterAssignmentsGenerator.TryBuildAssignments(
            availableCharacterIds: AvailableIds,
            playersCount: 4,
            playerCharacterId: "c99",
            seed: 1,
            assignments: out _,
            error: out var error);

        ok.Should().BeFalse();
        error.Should().Be("player_character_not_found");
    }
}
