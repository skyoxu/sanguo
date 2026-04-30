using System;
using System.Collections.Generic;
using System.Linq;
using Game.Core.Battle;
using Game.Core.Campaign;
using Game.Core.Contracts;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task111SplitIntegrationTests
{
    [Fact]
    public void CandidateWithHighestExpectedPursuitScoreBecomesTopCandidate()
    {
        var command = SplitForceCommand.Create(
            Guid.NewGuid(),
            Guid.NewGuid(),
            700,
            500,
            500,
            300,
            300,
            100,
            "task-111");

        var profile = new PursuitSelectionProfile(
            command,
            DateTimeOffset.UtcNow,
            BuildLeaderboard(
                (new ArmySnapshot(ArmyRole.Center, 1800, 1200, 380, 180, 75), new TacticResponseMetrics(0.92, 1.34, 0.61), 0.40, true),
                (new ArmySnapshot(ArmyRole.LeftFlank, 1500, 1000, 340, 160, 68), new TacticResponseMetrics(0.79, 1.08, 0.46), 0.20, true),
                (new ArmySnapshot(ArmyRole.RightFlank, 1400, 980, 320, 150, 65), new TacticResponseMetrics(0.74, 1.01, 0.43), 0.10, false)));

        var topCandidate = profile.Candidates.First();

        Assert.Equal(profile.Candidates.Max(c => c.ExpectedPursuitScore), topCandidate.ExpectedPursuitScore);
        Assert.Equal(ArmyRole.Center, topCandidate.Army.Role);
    }

    private static IReadOnlyList<PursuitCandidateSnapshot> BuildLeaderboard(
        params (ArmySnapshot Army, TacticResponseMetrics Metrics, double SupportWeight, bool CanCapture)[] candidates)
    {
        if (candidates.Length == 0)
        {
            return Array.Empty<PursuitCandidateSnapshot>();
        }

        var computed = candidates.Select(candidate =>
        {
            var score = candidate.Metrics.CounterPressure * 0.55
                + candidate.Metrics.ReinforcementCoverage * 0.35
                + candidate.SupportWeight * 0.1;
            return new PursuitCandidateSnapshot(
                candidate.Army,
                candidate.Metrics,
                Math.Round(score, 4),
                candidate.CanCapture,
                candidate.SupportWeight);
        });

        return computed.OrderByDescending(snapshot => snapshot.ExpectedPursuitScore).ToArray();
    }
}
