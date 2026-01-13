using System;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task60GameEndEventContractTests
{
    // ACC:T60.1
    [Fact]
    public void GameEnded_ShouldSupportWinnerReasonAndStatsSnapshot()
    {
        var evt = new SanguoGameEnded(
            "g1",
            "max_turns",
            DateTimeOffset.UtcNow,
            "corr-1",
            null,
            "p1",
            new SanguoGameEndStatsSnapshot(
                10,
                0,
                new[]
                {
                    new SanguoGameEndPlayerStats("p1", 10000m),
                    new SanguoGameEndPlayerStats("ai-1", 5000m),
                }));

        evt.WinnerPlayerId.Should().Be("p1");
        evt.StatsSnapshot.Should().NotBeNull();
    }
}
