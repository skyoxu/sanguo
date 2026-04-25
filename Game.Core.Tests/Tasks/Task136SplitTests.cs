using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task136SplitTests
{
    // ACC:T136.1
    [Fact]
    [Trait("acceptance", "ACC:T136.1")]
    public void ShouldTriggerForcedPreemptionAtLeaveCampBoundary_WhenHardCapReached()
    {
        var replay = CampPressureBoardTransitionSequencer.ReplayEventTypes(
            new[]
            {
                SanguoGameTurnAdvanced.EventType,
                SanguoBossChallengePrompted.EventType,
                SanguoTokenMoved.EventType,
                SanguoGameTurnEnded.EventType,
            },
            hardCapReachedAtLeaveCampEdge: true);

        replay.BoardEntryBranch.Should().Be("boss_preempted_board_entry");
        replay.Checkpoints.Should().Contain("pressure_preempted_by_boss");
        replay.Checkpoints.Should().NotContain("board_entered");
    }

    // ACC:T136.2
    [Fact]
    [Trait("acceptance", "ACC:T136.2")]
    public void ShouldBlockBoardEntry_WhenHardCapForcedChallengePreemptsLeaveCampFlow()
    {
        var replay = CampPressureBoardTransitionSequencer.ReplayEventTypes(
            new[]
            {
                SanguoGameTurnAdvanced.EventType,
                SanguoBossChallengePrompted.EventType,
                SanguoTokenMoved.EventType,
                SanguoGameTurnEnded.EventType,
            },
            hardCapReachedAtLeaveCampEdge: true);

        replay.BoardEntryBranch.Should().Be(
            "boss_preempted_board_entry",
            "hard-cap preemption should take the boss-preempted branch on leave-camp boundary.");
        replay.Checkpoints.Should().NotContain(
            "board_entered",
            "normal leave-camp board traversal must not continue after hard-cap forced challenge preemption.");
    }

    [Fact]
    public void ShouldKeepStandardLeaveCampPath_WhenHardCapPreemptionIsNotTriggered()
    {
        var replay = CampPressureBoardTransitionSequencer.ReplayEventTypes(
            new[]
            {
                SanguoGameTurnAdvanced.EventType,
                SanguoTokenMoved.EventType,
                SanguoGameTurnEnded.EventType,
            },
            hardCapReachedAtLeaveCampEdge: false);

        replay.BoardEntryBranch.Should().Be("standard_board_entry");
        replay.Checkpoints.Should().Contain("board_entered");
    }

    [Fact]
    public void ShouldNotPreemptWithoutHardCap_WhenPromptExistsButLeaveCampBoundaryNotAtCap()
    {
        var replay = CampPressureBoardTransitionSequencer.ReplayEventTypes(
            new[]
            {
                SanguoGameTurnAdvanced.EventType,
                SanguoBossChallengePrompted.EventType,
                SanguoTokenMoved.EventType,
                SanguoGameTurnEnded.EventType,
            },
            hardCapReachedAtLeaveCampEdge: false);

        replay.BoardEntryBranch.Should().Be("standard_board_entry");
        replay.Checkpoints.Should().Contain("board_entered");
    }

    // ACC:T136.3
    [Fact]
    [Trait("acceptance", "ACC:T136.3")]
    public void ShouldProduceDeterministicReplayEvidence_WhenSameHardCapLeaveCampSequenceIsReplayed()
    {
        var eventTypes = new[]
        {
            SanguoGameTurnAdvanced.EventType,
            SanguoBossChallengePrompted.EventType,
            SanguoTokenMoved.EventType,
            SanguoGameTurnEnded.EventType,
        };

        var firstReplay = CampPressureBoardTransitionSequencer.ReplayEventTypes(eventTypes, hardCapReachedAtLeaveCampEdge: true);
        var secondReplay = CampPressureBoardTransitionSequencer.ReplayEventTypes(eventTypes, hardCapReachedAtLeaveCampEdge: true);

        secondReplay.Should().BeEquivalentTo(firstReplay, options => options.WithStrictOrdering());
    }
}
