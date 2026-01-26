using System;
using System.Collections.Generic;

namespace Game.Core.Services.Sanguo;

public static class SanguoRegionsValidator
{
    public static void ValidateCityRegionIdsOrThrow(
        IReadOnlyDictionary<string, string?> cityRegionIds,
        IReadOnlySet<string> knownRegionIds)
    {
        ArgumentNullException.ThrowIfNull(cityRegionIds);
        ArgumentNullException.ThrowIfNull(knownRegionIds);

        foreach (var (cityId, regionId) in cityRegionIds)
        {
            if (string.IsNullOrWhiteSpace(cityId))
                throw new InvalidOperationException("invalid_city_region_ids:empty_city_id");

            if (string.IsNullOrWhiteSpace(regionId))
                throw new InvalidOperationException("invalid_city_region_ids:missing_region_id");

            if (!knownRegionIds.Contains(regionId))
                throw new InvalidOperationException("invalid_city_region_ids:unknown_region_id");
        }
    }
}

