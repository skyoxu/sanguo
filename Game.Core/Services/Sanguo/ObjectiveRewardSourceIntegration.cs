using System;
using System.Collections.Generic;

namespace Game.Core.Services.Sanguo;

/// <summary>
/// Task 141 production entrypoint for deterministic objective reward-source evidence.
/// </summary>
public static class ObjectiveRewardSourceIntegration
{
    public static ObjectiveRewardSourceEvidence BuildDeterministicEvidence(IReadOnlyList<ObjectiveRewardSourceEmission> emissions)
    {
        ArgumentNullException.ThrowIfNull(emissions);

        var sourceTags = new List<string>(emissions.Count);
        foreach (var emission in emissions)
        {
            if (TryMapSourceTag(emission.OriginKind, out var tag))
            {
                sourceTags.Add(tag);
            }
        }

        var signature = "R8:" + string.Join("|", sourceTags);
        return new ObjectiveRewardSourceEvidence(sourceTags, signature);
    }

    private static bool TryMapSourceTag(string originKind, out string sourceTag)
    {
        var normalized = (originKind ?? string.Empty).Trim();
        if (string.Equals(normalized, "event", StringComparison.OrdinalIgnoreCase))
        {
            sourceTag = "event";
            return true;
        }

        if (string.Equals(normalized, "elite", StringComparison.OrdinalIgnoreCase))
        {
            sourceTag = "elite";
            return true;
        }

        if (string.Equals(normalized, "boss", StringComparison.OrdinalIgnoreCase))
        {
            sourceTag = "boss";
            return true;
        }

        sourceTag = string.Empty;
        return false;
    }
}

public sealed record ObjectiveRewardSourceEmission(string OriginKind, string RewardId, int Amount);

public sealed record ObjectiveRewardSourceEvidence(IReadOnlyList<string> SourceTags, string EvidenceSignature);
