using System;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Text;

namespace Game.Core.Services.Sanguo;

/// <summary>
/// Task 117 split scope entrypoint for deterministic objective-generation evidence.
/// </summary>
public static class SanguoObjectiveGenerationDeterminismEngine
{
    private static readonly string[] CampaignObjectivePool =
    {
        "SecureSupplyRoute",
        "HoldRiverCrossing",
        "StabilizeCampOrder",
        "CounterEnemyRaid",
        "FortifyRelayNode",
        "ProtectForwardScouts",
    };

    private static readonly string[] DefaultObjectivePool =
    {
        "PatrolAssignedSector",
        "ConserveTacticalSupplies",
        "MaintainIntelCoverage",
        "ReinforceOuterPerimeter",
    };

    public static string GenerateObjectiveSnapshot(int seed, string modeName, int roundIndex)
    {
        var normalizedMode = NormalizeMode(modeName);
        var normalizedRound = Math.Max(1, roundIndex);
        var objectivePool = SelectObjectivePool(normalizedMode);

        var key = $"{normalizedMode}|{seed}|{normalizedRound}";
        var objectiveIndex = GetDeterministicIndex(key, objectivePool.Count);
        var objectiveCode = objectivePool[objectiveIndex];

        return string.Concat(
            "OBJECTIVE_SNAPSHOT_",
            normalizedMode,
            "_SEED_",
            seed.ToString(),
            "_ROUND_",
            normalizedRound.ToString(),
            "_OBJ_",
            objectiveCode);
    }

    private static string NormalizeMode(string? modeName)
    {
        var normalized = (modeName ?? string.Empty).Trim();
        if (string.IsNullOrWhiteSpace(normalized))
        {
            return "DEFAULT";
        }

        return normalized.ToUpperInvariant();
    }

    private static IReadOnlyList<string> SelectObjectivePool(string normalizedMode) =>
        string.Equals(normalizedMode, "CAMPAIGN", StringComparison.Ordinal)
            ? CampaignObjectivePool
            : DefaultObjectivePool;

    private static int GetDeterministicIndex(string key, int upperBoundExclusive)
    {
        var bytes = SHA256.HashData(Encoding.UTF8.GetBytes(key));
        var value = BitConverter.ToInt32(bytes, startIndex: 0) & int.MaxValue;
        return value % upperBoundExclusive;
    }
}
