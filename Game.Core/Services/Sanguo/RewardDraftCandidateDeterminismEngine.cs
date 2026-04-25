using System;
using System.Collections.Generic;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using Game.Core.Contracts.Sanguo;

namespace Game.Core.Services.Sanguo;

/// <summary>
/// Task 119 split scope entrypoint for deterministic reward draft candidate generation.
/// </summary>
public static class RewardDraftCandidateDeterminismEngine
{
    private static readonly string[] DefaultRewardPool =
    {
        "reward.alpha",
        "reward.beta",
        "reward.gamma",
        "reward.delta",
        "reward.epsilon",
    };

    public static IReadOnlyList<string> GenerateDraftCandidates()
    {
        return GenerateDraftCandidates(
            seed: 119,
            source: "objective_reward",
            choiceCount: 3,
            actionCardsCatalog: null,
            relicsCatalog: null);
    }

    public static IReadOnlyList<string> GenerateDraftCandidates(
        int seed,
        string source,
        int choiceCount,
        SanguoActionCardsCatalog? actionCardsCatalog,
        SanguoRelicsCatalog? relicsCatalog)
    {
        var normalizedChoiceCount = Math.Max(1, choiceCount);
        var normalizedSource = string.IsNullOrWhiteSpace(source) ? "objective_reward" : source.Trim();

        var pool = BuildCandidatePool(actionCardsCatalog, relicsCatalog);
        if (pool.Count == 0)
        {
            pool = DefaultRewardPool.ToList();
        }

        while (pool.Count < normalizedChoiceCount)
        {
            var fallbackId = $"reward.fallback.{pool.Count + 1}";
            if (!pool.Contains(fallbackId, StringComparer.Ordinal))
            {
                pool.Add(fallbackId);
            }
        }

        return pool
            .OrderBy(id => ComputeDeterministicRank(normalizedSource, seed, id))
            .ThenBy(id => id, StringComparer.Ordinal)
            .Take(normalizedChoiceCount)
            .ToArray();
    }

    private static List<string> BuildCandidatePool(
        SanguoActionCardsCatalog? actionCardsCatalog,
        SanguoRelicsCatalog? relicsCatalog)
    {
        var candidates = new List<string>();

        if (actionCardsCatalog is not null)
        {
            foreach (var card in actionCardsCatalog.Cards)
            {
                if (!string.IsNullOrWhiteSpace(card.CardId))
                {
                    candidates.Add($"card:{card.CardId.Trim()}");
                }
            }
        }

        if (relicsCatalog is not null)
        {
            foreach (var relic in relicsCatalog.Relics)
            {
                if (!string.IsNullOrWhiteSpace(relic.RelicId))
                {
                    candidates.Add($"relic:{relic.RelicId.Trim()}");
                }
            }
        }

        candidates.AddRange(DefaultRewardPool);

        return candidates
            .Where(id => !string.IsNullOrWhiteSpace(id))
            .Distinct(StringComparer.Ordinal)
            .ToList();
    }

    private static ulong ComputeDeterministicRank(string source, int seed, string candidateId)
    {
        var input = string.Concat(source, "|", seed.ToString(), "|", candidateId);
        var bytes = SHA256.HashData(Encoding.UTF8.GetBytes(input));
        return BitConverter.ToUInt64(bytes, 0);
    }
}
