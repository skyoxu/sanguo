using FluentAssertions;
using Game.Core.Domain;
using System;
using System.Collections.Generic;
using System.Linq;
using Xunit;
using MoneyValue = Game.Core.Domain.ValueObjects.Money;

namespace Game.Core.Tests.Tasks;

// ADR-0004-event-bus-and-contracts (Accepted): Economic computations must be explicit and testable.
// ADR-0005-quality-gates (Accepted): Fail-fast behavior is enforced by deterministic unit tests.
// ADR-0011-windows-only-platform-and-ci (Accepted): Windows-only, but Core logic stays engine-agnostic.
// ADR-0019-godot-security-baseline (Accepted): Reject invalid inputs; never silently downgrade results.
public sealed class Task65RegionSynergyTollTests
{
    // ACC:T65.1
    [Fact]
    public void GivenOwnerOwnsMultipleCitiesInRegion_WhenComputingSynergyToll_ThenSumsPerCityFinalTollsAndReturnsBreakdown()
    {
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new City("c1", "City 1", "r1", MoneyValue.FromDecimal(10), MoneyValue.FromDecimal(5), positionIndex: 1),
            ["c2"] = new City("c2", "City 2", "r1", MoneyValue.FromDecimal(10), MoneyValue.FromDecimal(7), positionIndex: 2),
            ["c3"] = new City("c3", "City 3", "r2", MoneyValue.FromDecimal(10), MoneyValue.FromDecimal(9), positionIndex: 3),
        };

        var ownerOwnedCityIds = new[] { "c1", "c2", "c3" };
        var calls = new List<string>();
        var finalTollsByCityId = new Dictionary<string, decimal>(StringComparer.Ordinal)
        {
            ["c1"] = 10m,
            ["c2"] = 20m,
            ["c3"] = 30m,
        };

        decimal ComputeFinalToll(string cityId)
        {
            calls.Add(cityId);
            return finalTollsByCityId[cityId];
        }

        var result = SanguoRegionSynergyTollCalculator.Compute(
            payerId: "payer",
            ownerId: "owner",
            landingCityId: "c1",
            citiesById: citiesById,
            ownerOwnedCityIds: ownerOwnedCityIds,
            computeCityFinalToll: ComputeFinalToll,
            bypassPolicy: new DefaultSanguoRegionSynergyTollBypassPolicy());

        result.Total.Should().Be(30m);
        result.Breakdown.Should().HaveCount(2);
        result.Breakdown.Select(x => x.CityId).Should().Equal(new[] { "c1", "c2" });
        result.Breakdown.Select(x => x.Amount).Sum().Should().Be(result.Total);
        var breakdownByCityId = result.Breakdown.ToDictionary(x => x.CityId, x => x.Amount, StringComparer.Ordinal);
        breakdownByCityId["c1"].Should().Be(10m);
        breakdownByCityId["c2"].Should().Be(20m);

        calls.Should().Equal(new[] { "c1", "c2" });
    }

    // ACC:T65.2
    [Fact]
    public void GivenUnownedOrSelfOrNoOwnedCities_WhenComputingSynergyToll_ThenReturnsZeroAndEmptyBreakdown()
    {
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new City("c1", "City 1", "r1", MoneyValue.FromDecimal(10), MoneyValue.FromDecimal(5), positionIndex: 1),
        };

        var resultUnowned = SanguoRegionSynergyTollCalculator.Compute(
            payerId: "p1",
            ownerId: null,
            landingCityId: "c1",
            citiesById: citiesById,
            ownerOwnedCityIds: Array.Empty<string>(),
            computeCityFinalToll: _ => throw new InvalidOperationException("should_not_call"),
            bypassPolicy: new DefaultSanguoRegionSynergyTollBypassPolicy());
        resultUnowned.Total.Should().Be(0m);
        resultUnowned.Breakdown.Should().BeEmpty();

        var resultSelf = SanguoRegionSynergyTollCalculator.Compute(
            payerId: "p1",
            ownerId: "p1",
            landingCityId: "c1",
            citiesById: citiesById,
            ownerOwnedCityIds: new[] { "c1" },
            computeCityFinalToll: _ => throw new InvalidOperationException("should_not_call"),
            bypassPolicy: new DefaultSanguoRegionSynergyTollBypassPolicy());
        resultSelf.Total.Should().Be(0m);
        resultSelf.Breakdown.Should().BeEmpty();

        var resultNoOwnedCities = SanguoRegionSynergyTollCalculator.Compute(
            payerId: "p1",
            ownerId: "p2",
            landingCityId: "c1",
            citiesById: citiesById,
            ownerOwnedCityIds: Array.Empty<string>(),
            computeCityFinalToll: _ => throw new InvalidOperationException("should_not_call"),
            bypassPolicy: new DefaultSanguoRegionSynergyTollBypassPolicy());
        resultNoOwnedCities.Total.Should().Be(0m);
        resultNoOwnedCities.Breakdown.Should().BeEmpty();

        var otherRegionCitiesById = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new City("c1", "City 1", "r1", MoneyValue.FromDecimal(10), MoneyValue.FromDecimal(5), positionIndex: 1),
            ["c2"] = new City("c2", "City 2", "r2", MoneyValue.FromDecimal(10), MoneyValue.FromDecimal(7), positionIndex: 2),
        };
        var resultOwnedOutsideRegion = SanguoRegionSynergyTollCalculator.Compute(
            payerId: "p1",
            ownerId: "p2",
            landingCityId: "c1",
            citiesById: otherRegionCitiesById,
            ownerOwnedCityIds: new[] { "c2" },
            computeCityFinalToll: _ => throw new InvalidOperationException("should_not_call"),
            bypassPolicy: new DefaultSanguoRegionSynergyTollBypassPolicy());
        resultOwnedOutsideRegion.Total.Should().Be(0m);
        resultOwnedOutsideRegion.Breakdown.Should().BeEmpty();
    }

    // ACC:T65.2
    [Fact]
    public void GivenDuplicateOwnedCityIds_WhenComputingSynergyToll_ThenDeduplicatesCitiesAndDoesNotDoubleCharge()
    {
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new City("c1", "City 1", "r1", MoneyValue.FromDecimal(10), MoneyValue.FromDecimal(5), positionIndex: 1),
            ["c2"] = new City("c2", "City 2", "r1", MoneyValue.FromDecimal(10), MoneyValue.FromDecimal(7), positionIndex: 2),
        };

        var calls = new List<string>();
        decimal ComputeFinalToll(string cityId)
        {
            calls.Add(cityId);
            return cityId == "c1" ? 10m : 20m;
        }

        var result = SanguoRegionSynergyTollCalculator.Compute(
            payerId: "payer",
            ownerId: "owner",
            landingCityId: "c1",
            citiesById: citiesById,
            ownerOwnedCityIds: new[] { "c1", "c1", "c2" },
            computeCityFinalToll: ComputeFinalToll,
            bypassPolicy: new DefaultSanguoRegionSynergyTollBypassPolicy());

        result.Breakdown.Select(x => x.CityId).Should().Equal(new[] { "c1", "c2" });
        result.Breakdown.Select(x => x.Amount).Should().Equal(new[] { 10m, 20m });
        result.Total.Should().Be(30m);
        calls.Should().Equal(new[] { "c1", "c2" });
    }

    // ACC:T65.4
    [Fact]
    public void GivenMissingCityOrCorruptedOwnership_WhenComputingSynergyToll_ThenFailFast()
    {
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new City("c1", "City 1", "r1", MoneyValue.FromDecimal(10), MoneyValue.FromDecimal(5), positionIndex: 1),
        };

        Action missingLandingCity = () =>
            _ = SanguoRegionSynergyTollCalculator.Compute(
                payerId: "p1",
                ownerId: "p2",
                landingCityId: "missing",
                citiesById: citiesById,
                ownerOwnedCityIds: new[] { "c1" },
                computeCityFinalToll: _ => 10m,
                bypassPolicy: new DefaultSanguoRegionSynergyTollBypassPolicy());
        missingLandingCity.Should().Throw<InvalidOperationException>();

        Action corruptedOwnerSet = () =>
            _ = SanguoRegionSynergyTollCalculator.Compute(
                payerId: "p1",
                ownerId: "p2",
                landingCityId: "c1",
                citiesById: citiesById,
                ownerOwnedCityIds: new[] { "missing" },
                computeCityFinalToll: _ => 10m,
                bypassPolicy: new DefaultSanguoRegionSynergyTollBypassPolicy());
        corruptedOwnerSet.Should().Throw<InvalidOperationException>();

        Action missingRegionId = () =>
        {
            var missingRegionCitiesById = new Dictionary<string, City>(StringComparer.Ordinal)
            {
                ["c1"] = new City("c1", "City 1", regionId: "", basePrice: MoneyValue.FromDecimal(10), baseToll: MoneyValue.FromDecimal(5), positionIndex: 1),
            };

            _ = SanguoRegionSynergyTollCalculator.Compute(
                payerId: "p1",
                ownerId: "p2",
                landingCityId: "c1",
                citiesById: missingRegionCitiesById,
                ownerOwnedCityIds: new[] { "c1" },
                computeCityFinalToll: _ => 10m,
                bypassPolicy: new DefaultSanguoRegionSynergyTollBypassPolicy());
        };
        missingRegionId.Should().Throw<ArgumentException>();

        var ownershipMismatchCitiesById = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new City("c1", "City 1", "r1", MoneyValue.FromDecimal(10), MoneyValue.FromDecimal(5), positionIndex: 1),
            ["c2"] = new City("c2", "City 2", "r1", MoneyValue.FromDecimal(10), MoneyValue.FromDecimal(7), positionIndex: 2),
        };
        Action ownershipMismatch = () =>
            _ = SanguoRegionSynergyTollCalculator.Compute(
                payerId: "p1",
                ownerId: "p2",
                landingCityId: "c1",
                citiesById: ownershipMismatchCitiesById,
                ownerOwnedCityIds: new[] { "c2" },
                computeCityFinalToll: _ => 10m,
                bypassPolicy: new DefaultSanguoRegionSynergyTollBypassPolicy());
        ownershipMismatch.Should().Throw<InvalidOperationException>();

        var outOfRangeCitiesById = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new City("c1", "City 1", "r1", MoneyValue.FromDecimal(10), MoneyValue.FromDecimal(5), positionIndex: 1),
            ["c2"] = new City("c2", "City 2", "r1", MoneyValue.FromDecimal(10), MoneyValue.FromDecimal(7), positionIndex: 2),
        };
        Action outOfRangeFinalToll = () =>
            _ = SanguoRegionSynergyTollCalculator.Compute(
                payerId: "p1",
                ownerId: "p2",
                landingCityId: "c1",
                citiesById: outOfRangeCitiesById,
                ownerOwnedCityIds: new[] { "c1", "c2" },
                computeCityFinalToll: cityId => cityId == "c1" ? -1m : 10m,
                bypassPolicy: new DefaultSanguoRegionSynergyTollBypassPolicy());
        outOfRangeFinalToll.Should().Throw<ArgumentOutOfRangeException>();
    }

    // ACC:T65.3
    [Fact]
    public void GivenBypassPolicyReturnsTrue_WhenComputingSynergyToll_ThenReturnsZeroAndDoesNotComputePerCity()
    {
        var citiesById = new Dictionary<string, City>(StringComparer.Ordinal)
        {
            ["c1"] = new City("c1", "City 1", "r1", MoneyValue.FromDecimal(10), MoneyValue.FromDecimal(5), positionIndex: 1),
            ["c2"] = new City("c2", "City 2", "r1", MoneyValue.FromDecimal(10), MoneyValue.FromDecimal(7), positionIndex: 2),
        };

        var result = SanguoRegionSynergyTollCalculator.Compute(
            payerId: "p1",
            ownerId: "p2",
            landingCityId: "c1",
            citiesById: citiesById,
            ownerOwnedCityIds: new[] { "c1", "c2" },
            computeCityFinalToll: _ => throw new InvalidOperationException("should_not_call"),
            bypassPolicy: new AlwaysBypassSynergyTollPolicy());

        result.Total.Should().Be(0m);
        result.Breakdown.Should().BeEmpty();
    }

    private sealed class AlwaysBypassSynergyTollPolicy : ISanguoRegionSynergyTollBypassPolicy
    {
        public bool ShouldBypass(SanguoRegionSynergyTollContext context) => true;
    }
}
