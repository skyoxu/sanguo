using System;
using System.Collections.Generic;
using System.Linq;
using Game.Core.Battle;
using Game.Core.Campaign;
using Game.Core.Contracts;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task151SplitIntegrationTests
{
    [Fact]
    public void HighestExpectedScoreCandidateShouldBeSortedFirstForTask151()
    {
        var command = SplitForceCommand.Create(
            Guid.NewGuid(),
            Guid.NewGuid(),
            780,
            520,
            530,
            320,
            320,
            120,
            "task-151");

        var candidates = BuildCandidates(
            (ArmyRole.Center, 2100, 1280, 430, 215, 82, 0.95, 1.21, 0.33, true),
            (ArmyRole.RightFlank, 1700, 1030, 355, 175, 73, 0.81, 1.03, 0.21, true),
            (ArmyRole.LeftFlank, 1650, 980, 342, 168, 71, 0.74, 0.97, 0.18, false));

        var profile = new PursuitSelectionProfile(command, DateTimeOffset.UtcNow, candidates);

        Assert.Equal(ArmyRole.Center, profile.Candidates[0].Army.Role);
        Assert.Equal(profile.Candidates.Max(c => c.ExpectedPursuitScore), profile.Candidates[0].ExpectedPursuitScore);
        Assert.All(profile.Candidates.Zip(profile.Candidates.Skip(1), (current, next) => current.ExpectedPursuitScore >= next.ExpectedPursuitScore), Assert.True);
    }

    [Fact]
    public void SummaryShouldIncludeTask151ScopeAndTopCandidateFields()
    {
        var command = SplitForceCommand.Create(
            Guid.NewGuid(),
            Guid.NewGuid(),
            830,
            560,
            570,
            340,
            350,
            130,
            "task-151");

        var candidates = BuildCandidates(
            (ArmyRole.RightFlank, 1820, 1120, 372, 181, 75, 0.88, 1.09, 0.28, true),
            (ArmyRole.Center, 1980, 1200, 405, 200, 79, 0.93, 1.16, 0.31, true));

        var profile = new PursuitSelectionProfile(command, DateTimeOffset.UtcNow, candidates);
        var summary = profile.BuildSummary();

        Assert.Equal("task-151", summary.TaskScope);
        Assert.Equal(profile.Candidates[0].Army.Role, summary.PrimaryCandidateRole);
        Assert.Equal(profile.Candidates[0].ExpectedPursuitScore, summary.ExpectedPursuitScore);
        Assert.Equal(profile.Candidates[0].CanCaptureStronghold, summary.CanCaptureStronghold);
    }

    [Fact]
    public void CandidateSnapshotWeightShouldAlignWithScoreComputation()
    {
        var command = SplitForceCommand.Create(
            Guid.NewGuid(),
            Guid.NewGuid(),
            790,
            540,
            540,
            310,
            330,
            115,
            "task-151");

        var candidates = BuildCandidates(
            (ArmyRole.Center, 1880, 1160, 390, 192, 77, 0.9, 1.14, 0.29, true));

        var profile = new PursuitSelectionProfile(command, DateTimeOffset.UtcNow, candidates);
        var candidate = profile.Candidates[0];

        var expected = Math.Round(candidate.Metrics.CounterPressure * 0.55 + candidate.Metrics.ReinforcementCoverage * 0.35 + candidate.SupportWeight * 0.1, 4);
        Assert.Equal(expected, candidate.ExpectedPursuitScore);
    }

    private static IReadOnlyList<PursuitCandidateSnapshot> BuildCandidates(
        params (ArmyRole Role, int Soldiers, int Morale, int Attack, int Defense, int Mobility, double CounterPressure, double ReinforcementCoverage, double SupportWeight, bool CanCapture)[] data)
    {
        if (data.Length == 0)
        {
            return Array.Empty<PursuitCandidateSnapshot>();
        }

        var snapshots = data.Select(item =>
        {
            var score = Math.Round(item.CounterPressure * 0.55 + item.ReinforcementCoverage * 0.35 + item.SupportWeight * 0.1, 4);
            return new PursuitCandidateSnapshot(
                new ArmySnapshot(item.Role, item.Soldiers, item.Morale, item.Attack, item.Defense, item.Mobility),
                new TacticResponseMetrics(item.CounterPressure, item.ReinforcementCoverage, item.SupportWeight),
                score,
                item.CanCapture,
                item.SupportWeight);
        });

        return snapshots.OrderByDescending(snapshot => snapshot.ExpectedPursuitScore).ToArray();
    }
}
