using Game.Core.Contracts.Sanguo;
using System;
using System.Collections.Generic;
using System.Linq;

namespace Game.Core.Services.Sanguo;

public static class SanguoRegionBonusCalculator
{
    public static int ComputeRegionStepDeltaForCity(
        string cityId,
        string economyStepKey,
        IReadOnlyDictionary<string, string> cityRegionIds,
        IReadOnlyDictionary<string, string?> cityOwnerIds,
        IReadOnlyDictionary<string, SanguoEconomyStepDeltas> regionEconomyStepDeltasByRegionId)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(cityId);
        ArgumentException.ThrowIfNullOrWhiteSpace(economyStepKey);
        ArgumentNullException.ThrowIfNull(cityRegionIds);
        ArgumentNullException.ThrowIfNull(cityOwnerIds);
        ArgumentNullException.ThrowIfNull(regionEconomyStepDeltasByRegionId);

        if (!cityRegionIds.TryGetValue(cityId, out var regionId) || string.IsNullOrWhiteSpace(regionId))
            return 0;

        if (!cityOwnerIds.TryGetValue(cityId, out var ownerId) || string.IsNullOrWhiteSpace(ownerId))
            return 0;

        var isCaptured = cityRegionIds
            .Where(kvp => string.Equals(kvp.Value, regionId, StringComparison.Ordinal))
            .Select(kvp => kvp.Key)
            .All(cid =>
                cityOwnerIds.TryGetValue(cid, out var oid)
                && string.Equals(oid, ownerId, StringComparison.Ordinal));

        if (!isCaptured)
            return 0;

        if (!regionEconomyStepDeltasByRegionId.TryGetValue(regionId, out var deltas))
            return 0;

        var key = economyStepKey.Trim();
        if (key.Length == 0)
            return 0;

        return key.ToLowerInvariant() switch
        {
            "buyprice" => deltas.BuyPrice,
            "toll" => deltas.Toll,
            "incomesettlement" => deltas.IncomeSettlement,
            "buildcost" => deltas.BuildCost,
            "upgradecost" => deltas.UpgradeCost,
            _ => 0,
        };
    }
}
