using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task78SplitIntegrationTests
{
    // ACC:T78.2
    [Fact]
    [Trait("acceptance", "ACC:T78.2")]
    public void ShouldReturnRepeatableDraftEvidence_WhenSeedAndInputsAreReused()
    {
        const int seed = 78;
        const string sourceTag = "objective_reward";

        var firstCandidates = GenerateCandidates(seed, sourceTag, 3);
        var secondCandidates = GenerateCandidates(seed, sourceTag, 3);

        firstCandidates.Should().HaveCount(3, "task 78 closes only when the draft exposes three choices");
        secondCandidates.Should().HaveCount(3, "task 78 closes only when the draft exposes three choices");
        firstCandidates.Should().OnlyHaveUniqueItems("each draft choice should be a distinct candidate");
        secondCandidates.Should().OnlyHaveUniqueItems("each draft choice should be a distinct candidate");
        secondCandidates.Should().Equal(firstCandidates, "the same seed and inputs must replay the same draft ordering");

        var selectedCandidateId = firstCandidates[1];
        var firstCommit = RewardDraftCandidateDeterminismEngine.CommitRewardDraft(firstCandidates, new[] { selectedCandidateId }, sourceTag);
        var secondCommit = RewardDraftCandidateDeterminismEngine.CommitRewardDraft(secondCandidates, new[] { selectedCandidateId }, sourceTag);

        firstCommit.WasRejected.Should().BeFalse("a single valid selection should commit successfully");
        secondCommit.WasRejected.Should().BeFalse("replaying the same valid selection should keep the same accepted outcome");
        firstCommit.DomainEvents.Select(evt => evt.Type).Should().Equal(new[] { EventTypes.RewardOfferSelected, EventTypes.SanguoActionExplain });
        secondCommit.DomainEvents.Select(evt => evt.Type).Should().Equal(new[] { EventTypes.RewardOfferSelected, EventTypes.SanguoActionExplain });

        BuildDraftEvidenceSnapshot(secondCandidates, secondCommit)
            .Should().Be(BuildDraftEvidenceSnapshot(firstCandidates, firstCommit), "task 78 needs repeatable semantic draft evidence from the split reward draft implementation");
    }

    // ACC:T78.2
    [Fact]
    [Trait("acceptance", "ACC:T78.2")]
    public void ShouldReturnRepeatableRejectedEvidence_WhenInvalidMultiSelectionIsReused()
    {
        const int seed = 78;
        const string sourceTag = "objective_reward";

        var candidateIds = GenerateCandidates(seed, sourceTag, 3);
        var invalidSelection = new[] { candidateIds[0], candidateIds[1] };

        var firstRejected = RewardDraftCandidateDeterminismEngine.CommitRewardDraft(candidateIds, invalidSelection, sourceTag);
        var secondRejected = RewardDraftCandidateDeterminismEngine.CommitRewardDraft(candidateIds, invalidSelection, sourceTag);

        firstRejected.WasRejected.Should().BeTrue("multi-select must stay rejected during integration closure");
        secondRejected.WasRejected.Should().BeTrue("the same invalid multi-select should replay the same rejected outcome");
        firstRejected.SelectedCandidateIds.Should().BeEmpty("rejected commits must keep the selected reward unchanged");
        secondRejected.SelectedCandidateIds.Should().BeEmpty("rejected commits must keep the selected reward unchanged");
        firstRejected.DomainEvents.Select(evt => evt.Type).Should().Equal(new[] { EventTypes.SanguoActionExplain });
        secondRejected.DomainEvents.Select(evt => evt.Type).Should().Equal(new[] { EventTypes.SanguoActionExplain });

        BuildDraftEvidenceSnapshot(candidateIds, secondRejected)
            .Should().Be(BuildDraftEvidenceSnapshot(candidateIds, firstRejected), "rejected reward draft evidence should also remain deterministic for repeated invalid inputs");
    }

    // ACC:T78.3
    [Fact]
    [Trait("acceptance", "ACC:T78.3")]
    public void ShouldExposeExactlyThreeCandidateOptions_WhenDraftIsGeneratedForIntegrationClosure()
    {
        var candidateIds = GenerateCandidates(seed: 78, sourceTag: "objective_reward", choiceCount: 3);

        candidateIds.Should().HaveCount(3, "task 78 closes only when each reward draft exposes exactly three candidate options");
        candidateIds.Should().OnlyHaveUniqueItems("the three-choice draft should not duplicate candidates");
    }

    // ACC:T78.3
    [Fact]
    [Trait("acceptance", "ACC:T78.3")]
    public void ShouldClampDraftToThreeCandidateOptions_WhenCallerRequestsMoreThanThreeChoices()
    {
        var candidateIds = GenerateCandidates(seed: 78, sourceTag: "objective_reward", choiceCount: 5);

        candidateIds.Should().HaveCount(3, "task 78 acceptance requires the integrated reward draft surface to stay fixed at exactly three choices");
    }

    private static IReadOnlyList<string> GenerateCandidates(int seed, string sourceTag, int choiceCount)
    {
        return RewardDraftCandidateDeterminismEngine.GenerateDraftCandidates(
            seed: seed,
            source: sourceTag,
            choiceCount: choiceCount,
            actionCardsCatalog: null,
            relicsCatalog: null);
    }

    private static string BuildDraftEvidenceSnapshot(IReadOnlyList<string> candidateIds, RewardDraftCommitResult commitResult)
    {
        var candidateSnapshot = string.Join(",", candidateIds);
        var selectedSnapshot = string.Join(",", commitResult.SelectedCandidateIds);
        var eventSnapshot = string.Join("|", commitResult.DomainEvents.Select(BuildEventSemanticSnapshot));
        var sourceSnapshot = string.Join(",", commitResult.SourceTags);
        var explainSnapshot = string.Join(",", commitResult.ExplainCodes);
        var outcomeSnapshot = commitResult.WasRejected ? "rejected" : "accepted";

        return string.Join("||", candidateSnapshot, selectedSnapshot, eventSnapshot, sourceSnapshot, explainSnapshot, outcomeSnapshot);
    }

    private static string BuildEventSemanticSnapshot(DomainEvent evt)
    {
        var payload = ExtractPayload(evt);

        if (string.Equals(evt.Type, EventTypes.RewardOfferSelected, StringComparison.Ordinal))
        {
            return string.Join(
                ":",
                "reward-selected",
                ReadRequiredString(payload, "SelectedCandidateId"),
                ReadRequiredString(payload, "RewardId"),
                ReadRequiredString(payload, "SourceTag"));
        }

        if (string.Equals(evt.Type, EventTypes.SanguoActionExplain, StringComparison.Ordinal))
        {
            return string.Join(
                ":",
                "explain",
                ReadRequiredString(payload, "ExplainCode"),
                ReadRequiredString(payload, "SourceTag"));
        }

        return evt.Type;
    }

    private static JsonElement ExtractPayload(DomainEvent evt)
    {
        if (evt.Data is not JsonElementEventData jsonData)
        {
            throw new InvalidOperationException($"Expected JsonElementEventData for '{evt.Type}'.");
        }

        return jsonData.Value;
    }

    private static string ReadRequiredString(JsonElement payload, string propertyName)
    {
        return payload.GetProperty(propertyName).GetString()
            ?? throw new InvalidOperationException($"Property '{propertyName}' must be a string.");
    }
}
