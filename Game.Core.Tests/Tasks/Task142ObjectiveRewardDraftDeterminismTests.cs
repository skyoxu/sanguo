using System;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task142ObjectiveRewardDraftDeterminismTests
{
    // ACC:T142.1
    [Fact]
    [Trait("acceptance", "ACC:T142.1")]
    public void ShouldSelectSameReward_WhenObjectiveSettlementRunsTwiceWithSameInputs()
    {
        var firstCandidates = RewardDraftCandidateDeterminismEngine.GenerateDraftCandidates(
            seed: 142,
            source: "objective_reward",
            choiceCount: 3,
            actionCardsCatalog: null,
            relicsCatalog: null);
        var secondCandidates = RewardDraftCandidateDeterminismEngine.GenerateDraftCandidates(
            seed: 142,
            source: "objective_reward",
            choiceCount: 3,
            actionCardsCatalog: null,
            relicsCatalog: null);

        firstCandidates.Should().HaveCount(3);
        secondCandidates.Should().HaveCount(3);
        secondCandidates.Should().Equal(firstCandidates, "objective settlement reward draft must stay deterministic for identical inputs");

        var firstCommit = RewardDraftCandidateDeterminismEngine.CommitRewardDraft(
            firstCandidates,
            new[] { firstCandidates[0] },
            "objective_reward");
        var secondCommit = RewardDraftCandidateDeterminismEngine.CommitRewardDraft(
            secondCandidates,
            new[] { secondCandidates[0] },
            "objective_reward");

        firstCommit.WasRejected.Should().BeFalse();
        secondCommit.WasRejected.Should().BeFalse();
        secondCommit.SelectedCandidateIds.Should().Equal(firstCommit.SelectedCandidateIds);
        secondCommit.ExplainCodes.Should().Equal(firstCommit.ExplainCodes);
    }

    // ACC:T142.1
    [Fact]
    [Trait("acceptance", "ACC:T142.1")]
    public void ShouldEmitR8EvidenceSignatureInExplainEvent_WhenObjectiveSettlementCommitsDraftSelection()
    {
        var emissions = new[]
        {
            new ObjectiveRewardSourceEmission("event", "reward_evt_1", 10),
            new ObjectiveRewardSourceEmission("elite", "reward_elite_1", 20),
            new ObjectiveRewardSourceEmission("boss", "reward_boss_1", 30),
        };

        var sourceEvidence = ObjectiveRewardSourceIntegration.BuildDeterministicEvidence(emissions);
        var candidateIds = RewardDraftCandidateDeterminismEngine.GenerateDraftCandidates(
            seed: 142,
            source: "objective_reward",
            choiceCount: 3,
            actionCardsCatalog: null,
            relicsCatalog: null);

        var commit = RewardDraftCandidateDeterminismEngine.CommitRewardDraft(
            candidateIds,
            new[] { candidateIds[0] },
            "objective_reward");

        var explainEvent = commit.DomainEvents.Single(evt => string.Equals(evt.Type, EventTypes.SanguoActionExplain, StringComparison.Ordinal));
        explainEvent.Data.Should().BeOfType<JsonElementEventData>();

        var payload = ((JsonElementEventData)explainEvent.Data!).Value;
        payload.TryGetProperty("SourceTag", out var sourceTag).Should().BeTrue();
        sourceTag.GetString().Should().Be("objective_reward");

        payload.TryGetProperty("EvidenceSignature", out var evidenceSignature).Should().BeTrue("R8 deterministic evidence must be carried on the explain event payload");
        evidenceSignature.ValueKind.Should().Be(JsonValueKind.String);
        evidenceSignature.GetString().Should().Be(sourceEvidence.EvidenceSignature);
    }

    [Fact]
    public void ShouldRefuseCommit_WhenObjectiveSettlementSelectsMultipleRewards()
    {
        var candidateIds = RewardDraftCandidateDeterminismEngine.GenerateDraftCandidates(
            seed: 142,
            source: "objective_reward",
            choiceCount: 3,
            actionCardsCatalog: null,
            relicsCatalog: null);

        var commit = RewardDraftCandidateDeterminismEngine.CommitRewardDraft(
            candidateIds,
            new[] { candidateIds[0], candidateIds[1] },
            "objective_reward");

        commit.WasRejected.Should().BeTrue("objective settlement reward draft must refuse multi-selection commits");
        commit.SelectedCandidateIds.Should().BeEmpty();
        commit.DomainEvents.Should().NotContain(evt => string.Equals(evt.Type, EventTypes.RewardOfferSelected, StringComparison.Ordinal));
        commit.ExplainCodes.Should().Contain("reward_draft_commit_rejected_multi_select");
    }
}
