using System;
using Game.Core.Services.Sanguo;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task153R4IntegrationTests
{
    // ACC:T153.2
    [Fact]
    public void ShouldLockCampaignExplainabilityAndReplayEvidence_WhenScenarioIsDeterministicAndComplete()
    {
        var gate = new Task153R4IntegrationGate();
        var evidence = new Task153R4ScenarioEvidence(
            ScenarioKind: "campaign",
            FixedSeed: 153,
            ExplainabilityEntries: new[]
            {
                new Task153ExplainabilityEntry("tile_random_event", "round=7/tick=42", "money:+120"),
                new Task153ExplainabilityEntry("boss_pressure", "round=7/tick=43", "durability:-1"),
            },
            LocalizedHudSummaries: new[]
            {
                "Random event summary. Source=Tile. Round=7. Money +120.",
                "Boss pressure summary. Source=Camp. Round=7. Durability -1.",
            },
            BaselineReplay: new Task153ReplaySnapshot(153, "digest-campaign-r4"),
            RerunReplay: new Task153ReplaySnapshot(153, "digest-campaign-r4"));

        var result = gate.Evaluate(evidence);

        result.IsLocked.Should().BeTrue("campaign CI evidence should lock explainability, HUD summaries, and replay output together");
        result.FailureCode.Should().BeNull();
        result.LockedScenario.Should().Be("campaign");
        result.LockedEvidenceKeys.Should().Equal("explainability", "hud_summary", "replay_digest");
        result.MissingRequirements.Should().BeEmpty();
    }

    [Fact]
    public void ShouldRejectEvidence_WhenScenarioIsNotCampaign()
    {
        var gate = new Task153R4IntegrationGate();
        var evidence = new Task153R4ScenarioEvidence(
            ScenarioKind: "sandbox",
            FixedSeed: 153,
            ExplainabilityEntries: new[]
            {
                new Task153ExplainabilityEntry("tile_random_event", "round=7/tick=42", "money:+120"),
            },
            LocalizedHudSummaries: new[]
            {
                "Random event summary. Source=Tile. Round=7. Money +120.",
            },
            BaselineReplay: new Task153ReplaySnapshot(153, "digest-shared"),
            RerunReplay: new Task153ReplaySnapshot(153, "digest-shared"));

        var result = gate.Evaluate(evidence);

        result.IsLocked.Should().BeFalse();
        result.FailureCode.Should().Be("NON_CAMPAIGN_SCENARIO");
        result.LockedScenario.Should().Be("sandbox");
        result.LockedEvidenceKeys.Should().BeEmpty();
        result.MissingRequirements.Should().BeEmpty();
    }

    [Fact]
    public void ShouldRejectEvidence_WhenReplayOutputDiffersUnderFixedSeed()
    {
        var gate = new Task153R4IntegrationGate();
        var evidence = new Task153R4ScenarioEvidence(
            ScenarioKind: "campaign",
            FixedSeed: 153,
            ExplainabilityEntries: new[]
            {
                new Task153ExplainabilityEntry("tile_random_event", "round=7/tick=42", "money:+120"),
            },
            LocalizedHudSummaries: new[]
            {
                "Random event summary. Source=Tile. Round=7. Money +120.",
            },
            BaselineReplay: new Task153ReplaySnapshot(153, "digest-a"),
            RerunReplay: new Task153ReplaySnapshot(153, "digest-b"));

        var result = gate.Evaluate(evidence);

        result.IsLocked.Should().BeFalse();
        result.FailureCode.Should().Be("REPLAY_DIGEST_MISMATCH");
        result.LockedEvidenceKeys.Should().BeEmpty();
        result.MissingRequirements.Should().ContainSingle().Which.Should().Be("replay_digest");
    }

    [Fact]
    public void ShouldRejectEvidence_WhenExplainabilityEntriesAreMissing()
    {
        var gate = new Task153R4IntegrationGate();
        var evidence = new Task153R4ScenarioEvidence(
            ScenarioKind: "campaign",
            FixedSeed: 153,
            ExplainabilityEntries: Array.Empty<Task153ExplainabilityEntry>(),
            LocalizedHudSummaries: new[] { "Random event summary. Source=Tile. Round=7. Money +120." },
            BaselineReplay: new Task153ReplaySnapshot(153, "digest-campaign-r4"),
            RerunReplay: new Task153ReplaySnapshot(153, "digest-campaign-r4"));

        var result = gate.Evaluate(evidence);

        result.IsLocked.Should().BeFalse();
        result.FailureCode.Should().Be("MISSING_EVIDENCE_LOCK");
        result.MissingRequirements.Should().ContainSingle().Which.Should().Be("explainability");
    }

    [Fact]
    public void ShouldRejectEvidence_WhenLocalizedHudSummariesAreMissing()
    {
        var gate = new Task153R4IntegrationGate();
        var evidence = new Task153R4ScenarioEvidence(
            ScenarioKind: "campaign",
            FixedSeed: 153,
            ExplainabilityEntries: new[]
            {
                new Task153ExplainabilityEntry("tile_random_event", "round=7/tick=42", "money:+120"),
            },
            LocalizedHudSummaries: Array.Empty<string>(),
            BaselineReplay: new Task153ReplaySnapshot(153, "digest-campaign-r4"),
            RerunReplay: new Task153ReplaySnapshot(153, "digest-campaign-r4"));

        var result = gate.Evaluate(evidence);

        result.IsLocked.Should().BeFalse();
        result.FailureCode.Should().Be("MISSING_EVIDENCE_LOCK");
        result.MissingRequirements.Should().ContainSingle().Which.Should().Be("hud_summary");
    }
}
