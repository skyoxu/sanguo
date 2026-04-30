using System;
using System.Collections.Generic;
using Game.Core.Campaign;
using Game.Core.Contracts;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task151SplitClosureTests
{
    [Fact]
    public void BuildSummaryUsesHighestExpectedPursuitScoreAsPrimaryCandidate()
    {
        var command = SplitForceCommand.Create(
            Guid.NewGuid(),
            Guid.NewGuid(),
            900,
            600,
            650,
            350,
            400,
            140,
            "task-151");

        var now = DateTimeOffset.UtcNow;
        var centerSnapshot = CreateCandidate(
            ArmyRole.Center,
            soldiers: 2200,
            morale: 1300,
            attack: 440,
            defense: 210,
            mobility: 86,
            counterPressure: 1.04,
            reinforcementCoverage: 1.25,
            supportWeight: 0.34,
            canCapture: true);
        var flankSnapshot = CreateCandidate(
            ArmyRole.LeftFlank,
            soldiers: 1750,
            morale: 1080,
            attack: 360,
            defense: 188,
            mobility: 74,
            counterPressure: 0.82,
            reinforcementCoverage: 1.02,
            supportWeight: 0.26,
            canCapture: true);

        var profile = new PursuitSelectionProfile(
            command,
            now,
            new[] { centerSnapshot, flankSnapshot });
        var summary = profile.BuildSummary();

        Assert.Equal(centerSnapshot.Army.Role, summary.PrimaryCandidateRole);
        Assert.Equal(centerSnapshot.ExpectedPursuitScore, summary.ExpectedPursuitScore);
        Assert.Equal(centerSnapshot.CanCaptureStronghold, summary.CanCaptureStronghold);
        Assert.Equal(now, summary.EvaluatedAt);
        Assert.Equal("task-151", summary.TaskScope);
    }

    [Fact]
    public void BuildSummaryFailsWhenCandidateListIsEmpty()
    {
        var command = SplitForceCommand.Create(
            Guid.NewGuid(),
            Guid.NewGuid(),
            760,
            540,
            520,
            320,
            320,
            110,
            "task-151");

        var profile = new PursuitSelectionProfile(
            command,
            DateTimeOffset.UtcNow,
            Array.Empty<PursuitCandidateSnapshot>());

        var exception = Assert.Throws<InvalidOperationException>(() => profile.BuildSummary());
        Assert.Equal("Pursuit selection summary requires at least one candidate.", exception.Message);
    }

    [Fact]
    public void BuildSummaryPreservesDeterministicScoresAcrossEquivalentInputs()
    {
        var command = SplitForceCommand.Create(
            Guid.NewGuid(),
            Guid.NewGuid(),
            810,
            500,
            470,
            300,
            310,
            95,
            "task-151");

        var first = CreateCandidate(
            ArmyRole.RightFlank,
            soldiers: 1620,
            morale: 960,
            attack: 325,
            defense: 168,
            mobility: 70,
            counterPressure: 0.77,
            reinforcementCoverage: 0.98,
            supportWeight: 0.24,
            canCapture: false);
        var second = CreateCandidate(
            ArmyRole.RightFlank,
            soldiers: 1620,
            morale: 960,
            attack: 325,
            defense: 168,
            mobility: 70,
            counterPressure: 0.77,
            reinforcementCoverage: 0.98,
            supportWeight: 0.24,
            canCapture: false);

        var profileA = new PursuitSelectionProfile(command, DateTimeOffset.UtcNow, new[] { first });
        var profileB = new PursuitSelectionProfile(command, DateTimeOffset.UtcNow, new[] { second });

        var summaryA = profileA.BuildSummary();
        var summaryB = profileB.BuildSummary();

        Assert.Equal(summaryA.ExpectedPursuitScore, summaryB.ExpectedPursuitScore);
        Assert.Equal(summaryA.PrimaryCandidateRole, summaryB.PrimaryCandidateRole);
        Assert.Equal(summaryA.CanCaptureStronghold, summaryB.CanCaptureStronghold);
        Assert.Equal("task-151", summaryA.TaskScope);
        Assert.Equal("task-151", summaryB.TaskScope);
    }

    private static PursuitCandidateSnapshot CreateCandidate(
        ArmyRole role,
        int soldiers,
        int morale,
        int attack,
        int defense,
        int mobility,
        double counterPressure,
        double reinforcementCoverage,
        double supportWeight,
        bool canCapture)
    {
        var score = Math.Round(counterPressure * 0.55 + reinforcementCoverage * 0.35 + supportWeight * 0.1, 4);
        return new PursuitCandidateSnapshot(
            new ArmySnapshot(role, soldiers, morale, attack, defense, mobility),
            new TacticResponseMetrics(counterPressure, reinforcementCoverage, supportWeight),
            score,
            canCapture,
            supportWeight);
    }
}
