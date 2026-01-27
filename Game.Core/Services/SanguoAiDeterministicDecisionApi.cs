using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;

namespace Game.Core.Services;

public static class SanguoAiDeterministicDecisionApi
{
    public sealed record DecisionCandidatesContext(
        bool CanRoll = true,
        bool CanBuyLand = false,
        bool CanBuild = false,
        bool CanUseCard = false,
        int CardsToDiscard = 0
    );

    public static SanguoAiDecisionMade MakeDecision(string decisionPoint, string rngContextId, IReadOnlyList<string> candidateIds)
    {
        // Keep this 3-parameter overload deterministic.
        // If runtime needs wall-clock timestamps, use the overload that accepts occurredAt.
        return MakeDecision(decisionPoint, rngContextId, candidateIds, occurredAt: DateTimeOffset.UnixEpoch);
    }

    public static IReadOnlyList<string> GetCandidatesForActor(
        string actorKind,
        string decisionPoint,
        DecisionCandidatesContext context)
    {
        ArgumentNullException.ThrowIfNull(actorKind, nameof(actorKind));
        ArgumentNullException.ThrowIfNull(decisionPoint, nameof(decisionPoint));
        ArgumentNullException.ThrowIfNull(context, nameof(context));

        // Task 61 rule: AI uses the same legality checks as the player.
        // Keep this logic pure and deterministic.
        return GetCandidates(decisionPoint, context);
    }

    private static IReadOnlyList<string> GetCandidates(string decisionPoint, DecisionCandidatesContext context)
    {
        var candidates = new List<string>();

        switch (decisionPoint)
        {
            case "BeforeRoll":
                if (context.CanRoll) candidates.Add("roll");
                if (context.CanUseCard) candidates.Add("use_card");
                break;

            case "ResolveLanding":
                if (context.CanBuyLand) candidates.Add("buy_land");
                if (context.CanBuild) candidates.Add("build");
                if (context.CanUseCard) candidates.Add("use_card");
                break;

            case "Discard":
                for (var i = 1; i <= context.CardsToDiscard; i++)
                {
                    candidates.Add($"discard_card_{i}");
                }
                break;

            default:
                throw new ArgumentException($"Unknown decision point '{decisionPoint}'.", nameof(decisionPoint));
        }

        return candidates.OrderBy(x => x, StringComparer.Ordinal).ToArray();
    }

    public static Task PublishDecisionAsync(IEventBus bus, SanguoAiDecisionMade decision)
    {
        ArgumentNullException.ThrowIfNull(bus, nameof(bus));
        ArgumentNullException.ThrowIfNull(decision, nameof(decision));

        var id = $"ai_decision:{decision.RngContextId ?? "no_rng"}:{decision.DecisionType}:{decision.PickedId ?? "no_pick"}";

        var evt = new DomainEvent(
            Type: SanguoAiDecisionMade.EventType,
            Source: nameof(SanguoAiDeterministicDecisionApi),
            Data: JsonElementEventData.FromObject(decision),
            Timestamp: DateTime.UnixEpoch,
            Id: id);

        return bus.PublishAsync(evt);
    }

    public static SanguoAiDecisionMade MakeDecision(
        string decisionPoint,
        string rngContextId,
        IReadOnlyList<string> candidateIds,
        DateTimeOffset occurredAt,
        string gameId = "game-unknown",
        string aiPlayerId = "ai",
        string? correlationId = null,
        string? causationId = null)
    {
        ArgumentNullException.ThrowIfNull(decisionPoint, nameof(decisionPoint));
        ArgumentNullException.ThrowIfNull(rngContextId, nameof(rngContextId));
        ArgumentNullException.ThrowIfNull(candidateIds, nameof(candidateIds));
        if (candidateIds.Count == 0)
            throw new ArgumentException("At least one candidate id is required.", nameof(candidateIds));

        var orderedCandidates = candidateIds
            .Select(x => x ?? throw new ArgumentException("Candidate id must not be null.", nameof(candidateIds)))
            .OrderBy(x => x, StringComparer.Ordinal)
            .ToArray();

        var pickedIndex = 0;
        var pickedId = orderedCandidates[pickedIndex];
        var candidatesSortedIdsHash = SanguoDeterminism.ComputeCandidatesSortedIdsHash(orderedCandidates);

        return new SanguoAiDecisionMade(
            GameId: gameId,
            AiPlayerId: aiPlayerId,
            DecisionType: decisionPoint,
            DecisionNode: decisionPoint,
            FromState: "unknown",
            ToState: "unknown",
            Reason: "deterministic_first_candidate",
            TargetCityId: null,
            OccurredAt: occurredAt,
            CorrelationId: correlationId ?? rngContextId,
            CausationId: causationId,
            RngContextId: rngContextId,
            CandidatesSortedIdsHash: candidatesSortedIdsHash,
            PickedIndex: pickedIndex,
            PickedId: pickedId);
    }
}
