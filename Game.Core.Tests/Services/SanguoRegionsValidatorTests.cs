using FluentAssertions;
using Game.Core.Services.Sanguo;
using System;
using System.Collections.Generic;
using Xunit;

namespace Game.Core.Tests.Services;

public class SanguoRegionsValidatorTests
{
    [Fact]
    public void ValidateCityRegionIdsOrThrow_ShouldThrow_WhenRegionIdMissing()
    {
        var cityRegionIds = new Dictionary<string, string?>(StringComparer.Ordinal) { ["c1"] = null };
        var known = new HashSet<string>(StringComparer.Ordinal) { "r1" };

        Action act = () => SanguoRegionsValidator.ValidateCityRegionIdsOrThrow(cityRegionIds, known);
        act.Should().Throw<InvalidOperationException>().WithMessage("invalid_city_region_ids:missing_region_id");
    }

    [Fact]
    public void ValidateCityRegionIdsOrThrow_ShouldThrow_WhenRegionIdUnknown()
    {
        var cityRegionIds = new Dictionary<string, string?>(StringComparer.Ordinal) { ["c1"] = "r2" };
        var known = new HashSet<string>(StringComparer.Ordinal) { "r1" };

        Action act = () => SanguoRegionsValidator.ValidateCityRegionIdsOrThrow(cityRegionIds, known);
        act.Should().Throw<InvalidOperationException>().WithMessage("invalid_city_region_ids:unknown_region_id");
    }

    [Fact]
    public void ValidateCityRegionIdsOrThrow_ShouldNotThrow_WhenAllRegionIdsKnown()
    {
        var cityRegionIds = new Dictionary<string, string?>(StringComparer.Ordinal) { ["c1"] = "r1" };
        var known = new HashSet<string>(StringComparer.Ordinal) { "r1" };

        Action act = () => SanguoRegionsValidator.ValidateCityRegionIdsOrThrow(cityRegionIds, known);
        act.Should().NotThrow();
    }
}

