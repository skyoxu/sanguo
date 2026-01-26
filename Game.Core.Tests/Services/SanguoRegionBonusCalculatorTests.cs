using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Game.Core.Services.Sanguo;
using System;
using System.Collections.Generic;
using Xunit;

namespace Game.Core.Tests.Services;

public class SanguoRegionBonusCalculatorTests
{
    [Fact]
    public void ShouldReturnZero_WhenCityNotInRegionMap()
    {
        var cityRegionIds = new Dictionary<string, string>(StringComparer.Ordinal);
        var cityOwnerIds = new Dictionary<string, string?>(StringComparer.Ordinal) { ["c1"] = "p1" };
        var regionDeltas = new Dictionary<string, SanguoEconomyStepDeltas>(StringComparer.Ordinal)
        {
            ["r1"] = new SanguoEconomyStepDeltas(0, 2, 0, 0, 0),
        };

        var delta = SanguoRegionBonusCalculator.ComputeRegionStepDeltaForCity(
            cityId: "c1",
            economyStepKey: "Toll",
            cityRegionIds: cityRegionIds,
            cityOwnerIds: cityOwnerIds,
            regionEconomyStepDeltasByRegionId: regionDeltas);

        delta.Should().Be(0);
    }

    [Fact]
    public void ShouldReturnZero_WhenCityUnowned()
    {
        var cityRegionIds = new Dictionary<string, string>(StringComparer.Ordinal) { ["c1"] = "r1" };
        var cityOwnerIds = new Dictionary<string, string?>(StringComparer.Ordinal) { ["c1"] = null };
        var regionDeltas = new Dictionary<string, SanguoEconomyStepDeltas>(StringComparer.Ordinal)
        {
            ["r1"] = new SanguoEconomyStepDeltas(0, 2, 0, 0, 0),
        };

        var delta = SanguoRegionBonusCalculator.ComputeRegionStepDeltaForCity(
            cityId: "c1",
            economyStepKey: "Toll",
            cityRegionIds: cityRegionIds,
            cityOwnerIds: cityOwnerIds,
            regionEconomyStepDeltasByRegionId: regionDeltas);

        delta.Should().Be(0);
    }

    [Fact]
    public void ShouldReturnZero_WhenCityOwnerNotInOwnerMap()
    {
        var cityRegionIds = new Dictionary<string, string>(StringComparer.Ordinal) { ["c1"] = "r1" };
        var cityOwnerIds = new Dictionary<string, string?>(StringComparer.Ordinal);
        var regionDeltas = new Dictionary<string, SanguoEconomyStepDeltas>(StringComparer.Ordinal)
        {
            ["r1"] = new SanguoEconomyStepDeltas(0, 2, 0, 0, 0),
        };

        var delta = SanguoRegionBonusCalculator.ComputeRegionStepDeltaForCity(
            cityId: "c1",
            economyStepKey: "Toll",
            cityRegionIds: cityRegionIds,
            cityOwnerIds: cityOwnerIds,
            regionEconomyStepDeltasByRegionId: regionDeltas);

        delta.Should().Be(0);
    }

    [Fact]
    public void ShouldReturnZero_WhenRegionNotFullyCaptured()
    {
        var cityRegionIds = new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["c1"] = "r1",
            ["c2"] = "r1",
        };

        var cityOwnerIds = new Dictionary<string, string?>(StringComparer.Ordinal)
        {
            ["c1"] = "p1",
            ["c2"] = "p2",
        };

        var regionDeltas = new Dictionary<string, SanguoEconomyStepDeltas>(StringComparer.Ordinal)
        {
            ["r1"] = new SanguoEconomyStepDeltas(0, 2, 0, 0, 0),
        };

        var delta = SanguoRegionBonusCalculator.ComputeRegionStepDeltaForCity(
            cityId: "c1",
            economyStepKey: "Toll",
            cityRegionIds: cityRegionIds,
            cityOwnerIds: cityOwnerIds,
            regionEconomyStepDeltasByRegionId: regionDeltas);

        delta.Should().Be(0);
    }

    [Fact]
    public void ShouldReturnZero_WhenRegionDeltasMissingEntry()
    {
        var cityRegionIds = new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["c1"] = "r1",
            ["c2"] = "r1",
        };

        var cityOwnerIds = new Dictionary<string, string?>(StringComparer.Ordinal)
        {
            ["c1"] = "p1",
            ["c2"] = "p1",
        };

        var regionDeltas = new Dictionary<string, SanguoEconomyStepDeltas>(StringComparer.Ordinal);

        var delta = SanguoRegionBonusCalculator.ComputeRegionStepDeltaForCity(
            cityId: "c1",
            economyStepKey: "Toll",
            cityRegionIds: cityRegionIds,
            cityOwnerIds: cityOwnerIds,
            regionEconomyStepDeltasByRegionId: regionDeltas);

        delta.Should().Be(0);
    }

    [Fact]
    public void ShouldReturnZero_WhenRegionDeltasMissing()
    {
        var cityRegionIds = new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["c1"] = "r1",
            ["c2"] = "r1",
        };

        var cityOwnerIds = new Dictionary<string, string?>(StringComparer.Ordinal)
        {
            ["c1"] = "p1",
            ["c2"] = "p1",
        };

        var regionDeltas = new Dictionary<string, SanguoEconomyStepDeltas>(StringComparer.Ordinal);

        var delta = SanguoRegionBonusCalculator.ComputeRegionStepDeltaForCity(
            cityId: "c1",
            economyStepKey: "Toll",
            cityRegionIds: cityRegionIds,
            cityOwnerIds: cityOwnerIds,
            regionEconomyStepDeltasByRegionId: regionDeltas);

        delta.Should().Be(0);
    }

    [Fact]
    public void ShouldReturnDelta_WhenRegionFullyCaptured()
    {
        var cityRegionIds = new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["c1"] = "r1",
            ["c2"] = "r1",
        };

        var cityOwnerIds = new Dictionary<string, string?>(StringComparer.Ordinal)
        {
            ["c1"] = "p1",
            ["c2"] = "p1",
        };

        var regionDeltas = new Dictionary<string, SanguoEconomyStepDeltas>(StringComparer.Ordinal)
        {
            ["r1"] = new SanguoEconomyStepDeltas(0, 2, 0, 0, 0),
        };

        var delta = SanguoRegionBonusCalculator.ComputeRegionStepDeltaForCity(
            cityId: "c1",
            economyStepKey: "Toll",
            cityRegionIds: cityRegionIds,
            cityOwnerIds: cityOwnerIds,
            regionEconomyStepDeltasByRegionId: regionDeltas);

        delta.Should().Be(2);
    }

    [Fact]
    public void ShouldReturnZero_WhenEconomyStepKeyUnknown()
    {
        var cityRegionIds = new Dictionary<string, string>(StringComparer.Ordinal) { ["c1"] = "r1" };
        var cityOwnerIds = new Dictionary<string, string?>(StringComparer.Ordinal) { ["c1"] = "p1" };
        var regionDeltas = new Dictionary<string, SanguoEconomyStepDeltas>(StringComparer.Ordinal)
        {
            ["r1"] = new SanguoEconomyStepDeltas(0, 2, 0, 0, 0),
        };

        var delta = SanguoRegionBonusCalculator.ComputeRegionStepDeltaForCity(
            cityId: "c1",
            economyStepKey: "UnknownKey",
            cityRegionIds: cityRegionIds,
            cityOwnerIds: cityOwnerIds,
            regionEconomyStepDeltasByRegionId: regionDeltas);

        delta.Should().Be(0);
    }
}
