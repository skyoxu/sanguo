using System;
using System.Collections.Generic;
using System.Linq;

namespace Game.Core.Domain;

public sealed record SanguoRegionSynergyTollContext(
    string PayerId,
    string OwnerId,
    string LandingCityId,
    string RegionId);

public interface ISanguoRegionSynergyTollBypassPolicy
{
    bool ShouldBypass(SanguoRegionSynergyTollContext context);
}

public sealed class DefaultSanguoRegionSynergyTollBypassPolicy : ISanguoRegionSynergyTollBypassPolicy
{
    public bool ShouldBypass(SanguoRegionSynergyTollContext context) => false;
}

public sealed record SanguoRegionSynergyTollBreakdownItem(string CityId, decimal Amount);

public sealed record SanguoRegionSynergyTollResult(decimal Total, IReadOnlyList<SanguoRegionSynergyTollBreakdownItem> Breakdown);

public static class SanguoRegionSynergyTollCalculator
{
    public static SanguoRegionSynergyTollResult Compute(
        string payerId,
        string? ownerId,
        string landingCityId,
        IReadOnlyDictionary<string, City> citiesById,
        IReadOnlyCollection<string> ownerOwnedCityIds,
        Func<string, decimal> computeCityFinalToll,
        ISanguoRegionSynergyTollBypassPolicy bypassPolicy)
    {
        if (string.IsNullOrWhiteSpace(payerId))
            throw new ArgumentException("PayerId must be non-empty.", nameof(payerId));

        if (string.IsNullOrWhiteSpace(landingCityId))
            throw new ArgumentException("LandingCityId must be non-empty.", nameof(landingCityId));

        ArgumentNullException.ThrowIfNull(citiesById, nameof(citiesById));
        ArgumentNullException.ThrowIfNull(ownerOwnedCityIds, nameof(ownerOwnedCityIds));
        ArgumentNullException.ThrowIfNull(computeCityFinalToll, nameof(computeCityFinalToll));
        ArgumentNullException.ThrowIfNull(bypassPolicy, nameof(bypassPolicy));

        if (string.IsNullOrWhiteSpace(ownerId))
            return new SanguoRegionSynergyTollResult(0m, Array.Empty<SanguoRegionSynergyTollBreakdownItem>());

        if (string.Equals(ownerId, payerId, StringComparison.Ordinal))
            return new SanguoRegionSynergyTollResult(0m, Array.Empty<SanguoRegionSynergyTollBreakdownItem>());

        if (ownerOwnedCityIds.Count == 0)
            return new SanguoRegionSynergyTollResult(0m, Array.Empty<SanguoRegionSynergyTollBreakdownItem>());

        if (!citiesById.TryGetValue(landingCityId, out var landingCity))
            throw new InvalidOperationException($"Landing city not found (landingCityId={landingCityId}).");

        var regionId = landingCity.RegionId;
        if (string.IsNullOrWhiteSpace(regionId))
            throw new InvalidOperationException($"Landing city has missing RegionId (landingCityId={landingCityId}).");

        var cityIdsInRegionSet = new HashSet<string>(StringComparer.Ordinal);
        foreach (var cityId in ownerOwnedCityIds)
        {
            if (!citiesById.TryGetValue(cityId, out var city))
                throw new InvalidOperationException($"Owner city set references missing city (cityId={cityId}).");

            if (string.Equals(city.RegionId, regionId, StringComparison.Ordinal))
                cityIdsInRegionSet.Add(cityId);
        }

        if (cityIdsInRegionSet.Count == 0)
            return new SanguoRegionSynergyTollResult(0m, Array.Empty<SanguoRegionSynergyTollBreakdownItem>());

        if (!cityIdsInRegionSet.Contains(landingCityId))
            throw new InvalidOperationException(
                $"Owner city set does not include the landing city within the same region (landingCityId={landingCityId}, regionId={regionId}).");

        var cityIdsInRegion = cityIdsInRegionSet.ToList();
        cityIdsInRegion.Sort(StringComparer.Ordinal);

        var context = new SanguoRegionSynergyTollContext(
            PayerId: payerId,
            OwnerId: ownerId,
            LandingCityId: landingCityId,
            RegionId: regionId);
        if (bypassPolicy.ShouldBypass(context))
            return new SanguoRegionSynergyTollResult(0m, Array.Empty<SanguoRegionSynergyTollBreakdownItem>());

        var breakdown = new List<SanguoRegionSynergyTollBreakdownItem>(capacity: cityIdsInRegion.Count);
        decimal total = 0m;
        foreach (var cityId in cityIdsInRegion)
        {
            var amount = computeCityFinalToll(cityId);
            if (amount < 0m)
                throw new ArgumentOutOfRangeException(nameof(computeCityFinalToll), "Final toll amount must be non-negative.");

            breakdown.Add(new SanguoRegionSynergyTollBreakdownItem(cityId, amount));
            total += amount;
        }

        return new SanguoRegionSynergyTollResult(total, breakdown);
    }
}
