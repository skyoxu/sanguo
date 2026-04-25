using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task120SplitTests
{
    // ACC:T120.1
    [Fact]
    [Trait("acceptance", "ACC:T120.1")]
    public void ShouldCommitExactlyOneRewardAndEmitSourceTaggedExplainability_WhenDraftIsCommitted()
    {
        var candidateIds = RewardDraftCandidateDeterminismEngine.GenerateDraftCandidates(
            seed: 120,
            source: "objective_reward",
            choiceCount: 3,
            actionCardsCatalog: null,
            relicsCatalog: null);

        candidateIds.Should().HaveCount(3);
        var selectedCandidateId = candidateIds[1];

        var first = RewardDraftCandidateDeterminismEngine.CommitRewardDraft(
            candidateIds,
            new[] { selectedCandidateId },
            "objective_reward");
        var second = RewardDraftCandidateDeterminismEngine.CommitRewardDraft(
            candidateIds,
            new[] { selectedCandidateId },
            "objective_reward");

        first.WasRejected.Should().BeFalse("single-selection commit should be accepted");
        second.WasRejected.Should().BeFalse("repeated identical commit should stay accepted");

        first.SelectedCandidateIds.Should().Equal(
            new[] { selectedCandidateId },
            "a reward draft commit must materialize exactly one selected reward");
        second.SelectedCandidateIds.Should().Equal(
            first.SelectedCandidateIds,
            "repeating the same commit inputs must keep the selected reward deterministic");

        first.DomainEvents.Count(evt => string.Equals(evt.Type, EventTypes.RewardOfferSelected, StringComparison.Ordinal))
            .Should().Be(1, "a successful reward draft commit should emit one reward selected event");
        first.DomainEvents.Should().Contain(
            evt => string.Equals(evt.Type, EventTypes.SanguoActionExplain, StringComparison.Ordinal),
            "R8 requires explainability output for the committed reward source");
        AssertRewardSelectedEventPayload(first.DomainEvents, selectedCandidateId, "objective_reward");
        AssertExplainEventPayload(first.DomainEvents, "reward_draft_commit_selected", "objective_reward");
        AssertRewardSelectedEventPayload(second.DomainEvents, selectedCandidateId, "objective_reward");
        AssertExplainEventPayload(second.DomainEvents, "reward_draft_commit_selected", "objective_reward");

        first.SourceTags.Should().Contain("objective_reward", "the explainability output must preserve the reward source tag");
        second.SourceTags.Should().Contain("objective_reward", "repeated identical commits must preserve the same reward source tag");
        first.ExplainCodes.Should().Contain("reward_draft_commit_selected");

        BuildEvidenceSnapshot(first).Should().Be(
            BuildEvidenceSnapshot(second),
            "reward draft commit semantic evidence must stay deterministic for identical draft and selection inputs");
    }

    // ACC:T120.1
    [Fact]
    [Trait("acceptance", "ACC:T120.1")]
    public void ShouldRefuseCommit_WhenMultipleRewardsAreSelected()
    {
        var candidateIds = RewardDraftCandidateDeterminismEngine.GenerateDraftCandidates(
            seed: 120,
            source: "objective_reward",
            choiceCount: 3,
            actionCardsCatalog: null,
            relicsCatalog: null);

        candidateIds.Should().HaveCountGreaterThanOrEqualTo(2);

        var probe = RewardDraftCandidateDeterminismEngine.CommitRewardDraft(
            candidateIds,
            new[] { candidateIds[0], candidateIds[1] },
            "objective_reward");

        probe.WasRejected.Should().BeTrue("a single commit must not accept multiple reward selections");
        probe.SelectedCandidateIds.Should().BeEmpty("rejected multi-select commit must keep the committed reward set unchanged");
        probe.DomainEvents.Should().NotContain(
            evt => string.Equals(evt.Type, EventTypes.RewardOfferSelected, StringComparison.Ordinal),
            "a rejected multi-select commit must not emit a reward selected event");

        probe.DomainEvents.Should().Contain(
            evt => string.Equals(evt.Type, EventTypes.SanguoActionExplain, StringComparison.Ordinal),
            "rejected commit must still emit explainability evidence");
        probe.SourceTags.Should().Contain("objective_reward", "rejected commit explainability should preserve source tag");
        probe.ExplainCodes.Should().Contain("reward_draft_commit_rejected_multi_select");
        AssertExplainEventPayload(probe.DomainEvents, "reward_draft_commit_rejected_multi_select", "objective_reward");
    }

    private static string BuildEvidenceSnapshot(RewardDraftCommitResult probe)
    {
        var selectedIds = string.Join(",", probe.SelectedCandidateIds.OrderBy(id => id, StringComparer.Ordinal));
        var eventTypes = string.Join(",", probe.DomainEvents.Select(evt => evt.Type).OrderBy(type => type, StringComparer.Ordinal));
        var semanticEventPayloads = string.Join(
            ",",
            probe.DomainEvents
                .OrderBy(evt => evt.Type, StringComparer.Ordinal)
                .Select(BuildEventSemanticPayloadSnapshot));
        var sourceTags = string.Join(",", probe.SourceTags.OrderBy(tag => tag, StringComparer.Ordinal));
        var explainCodes = string.Join(",", probe.ExplainCodes.OrderBy(code => code, StringComparer.Ordinal));

        return string.Join(
            "|",
            selectedIds,
            eventTypes,
            semanticEventPayloads,
            sourceTags,
            explainCodes,
            probe.WasRejected ? "rejected" : "accepted");
    }

    private static void AssertRewardSelectedEventPayload(
        IReadOnlyList<DomainEvent> events,
        string expectedRewardId,
        string expectedSourceTag)
    {
        var rewardSelectedEvent = events.Single(
            evt => string.Equals(evt.Type, EventTypes.RewardOfferSelected, StringComparison.Ordinal));
        var payload = ExtractJsonPayload(rewardSelectedEvent);

        ReadRequiredString(payload, "SelectedCandidateId").Should().Be(expectedRewardId);
        ReadRequiredString(payload, "RewardId").Should().Be(expectedRewardId);
        ReadRequiredString(payload, "SourceTag").Should().Be(expectedSourceTag);
    }

    private static void AssertExplainEventPayload(
        IReadOnlyList<DomainEvent> events,
        string expectedExplainCode,
        string expectedSourceTag)
    {
        var explainEvent = events.Single(
            evt => string.Equals(evt.Type, EventTypes.SanguoActionExplain, StringComparison.Ordinal));
        var payload = ExtractJsonPayload(explainEvent);

        ReadRequiredString(payload, "ExplainCode").Should().Be(expectedExplainCode);
        ReadRequiredString(payload, "SourceTag").Should().Be(expectedSourceTag);
    }

    private static string BuildEventSemanticPayloadSnapshot(DomainEvent evt)
    {
        var payload = ExtractJsonPayload(evt);
        if (string.Equals(evt.Type, EventTypes.RewardOfferSelected, StringComparison.Ordinal))
        {
            var selectedCandidateId = ReadRequiredString(payload, "SelectedCandidateId");
            var rewardId = ReadRequiredString(payload, "RewardId");
            var sourceTag = ReadRequiredString(payload, "SourceTag");
            return $"reward-selected:{selectedCandidateId}:{rewardId}:{sourceTag}";
        }

        if (string.Equals(evt.Type, EventTypes.SanguoActionExplain, StringComparison.Ordinal))
        {
            var explainCode = ReadRequiredString(payload, "ExplainCode");
            var sourceTag = ReadRequiredString(payload, "SourceTag");
            return $"action-explain:{explainCode}:{sourceTag}";
        }

        return $"{evt.Type}:n/a";
    }

    private static JsonElement ExtractJsonPayload(DomainEvent evt)
    {
        evt.Data.Should().NotBeNull("Task 120 event payload must be present");
        evt.Data.Should().BeOfType<JsonElementEventData>("Task 120 payload contracts are JSON-backed");
        return ((JsonElementEventData)evt.Data!).Value;
    }

    private static string ReadRequiredString(JsonElement payload, string fieldName)
    {
        payload.TryGetProperty(fieldName, out var value).Should().BeTrue($"{fieldName} should exist in explainability payload");
        value.ValueKind.Should().Be(JsonValueKind.String, $"{fieldName} should be encoded as string");
        var text = value.GetString();
        text.Should().NotBeNullOrWhiteSpace($"{fieldName} should be non-empty");
        return text!;
    }
}
