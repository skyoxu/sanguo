using System.Collections.Generic;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task131BossDifficultyProfileSchemaTests
{
    // ACC:T131.1
    [Fact]
    [Trait("acceptance", "ACC:T131.1")]
    public void ShouldPassValidation_WhenBossDifficultyProfileFieldsAreWithinAllowedBounds()
    {
        var rawFixture = CreateValidBossDifficultyProfile();

        var result = SanguoCampaignContentSchemaCatalog.ValidateRawFixture(
            SanguoCampaignContentFamily.Boss,
            rawFixture,
            CreateKnownReferences(),
            previousCatalogVersion: 1,
            currentCatalogVersion: 2,
            hasBreakingChange: false);

        result.IsValid.Should().BeTrue();
        result.ErrorCodes.Should().BeEmpty();
    }

    // ACC:T131.1
    [Fact]
    [Trait("acceptance", "ACC:T131.1")]
    public void ShouldFailValidation_WhenBossDifficultyProfilePowerExceedsUpperBound()
    {
        var rawFixture = CreateValidBossDifficultyProfile();
        rawFixture["power"] = 101;

        var result = SanguoCampaignContentSchemaCatalog.ValidateRawFixture(
            SanguoCampaignContentFamily.Boss,
            rawFixture,
            CreateKnownReferences(),
            previousCatalogVersion: 1,
            currentCatalogVersion: 2,
            hasBreakingChange: false);

        result.IsValid.Should().BeFalse();
        result.ErrorCodes.Should().Contain(SanguoCampaignContentSchemaCatalog.OutOfRangePowerError);
    }

    // ACC:T131.1
    [Fact]
    [Trait("acceptance", "ACC:T131.1")]
    public void ShouldFailValidation_WhenBossDifficultyProfilePowerFallsBelowLowerBound()
    {
        var rawFixture = CreateValidBossDifficultyProfile();
        rawFixture["power"] = 0;

        var result = SanguoCampaignContentSchemaCatalog.ValidateRawFixture(
            SanguoCampaignContentFamily.Boss,
            rawFixture,
            CreateKnownReferences(),
            previousCatalogVersion: 1,
            currentCatalogVersion: 2,
            hasBreakingChange: false);

        result.IsValid.Should().BeFalse();
        result.ErrorCodes.Should().Contain(SanguoCampaignContentSchemaCatalog.OutOfRangePowerError);
    }

    // ACC:T131.1
    [Fact]
    [Trait("acceptance", "ACC:T131.1")]
    public void ShouldFailValidation_WhenBossDifficultyProfileContainsUnknownField()
    {
        var rawFixture = CreateValidBossDifficultyProfile();
        rawFixture["legacyDifficulty"] = "obsolete";

        var result = SanguoCampaignContentSchemaCatalog.ValidateRawFixture(
            SanguoCampaignContentFamily.Boss,
            rawFixture,
            CreateKnownReferences(),
            previousCatalogVersion: 1,
            currentCatalogVersion: 2,
            hasBreakingChange: false);

        result.IsValid.Should().BeFalse();
        result.ErrorCodes.Should().Contain("UnknownField:legacyDifficulty");
    }

    // ACC:T131.1
    [Fact]
    [Trait("acceptance", "ACC:T131.1")]
    public void ShouldFailValidation_WhenBossDifficultyProfileMissesRequiredIdField()
    {
        var rawFixture = CreateValidBossDifficultyProfile();
        rawFixture.Remove("id");

        var result = SanguoCampaignContentSchemaCatalog.ValidateRawFixture(
            SanguoCampaignContentFamily.Boss,
            rawFixture,
            CreateKnownReferences(),
            previousCatalogVersion: 1,
            currentCatalogVersion: 2,
            hasBreakingChange: false);

        result.IsValid.Should().BeFalse();
        result.ErrorCodes.Should().Contain(SanguoCampaignContentSchemaCatalog.MissingRequiredFieldIdError);
    }

    // ACC:T131.1
    [Fact]
    [Trait("acceptance", "ACC:T131.1")]
    public void ShouldFailValidation_WhenBossDifficultyProfilePowerTypeIsInvalid()
    {
        var rawFixture = CreateValidBossDifficultyProfile();
        rawFixture["power"] = "50";

        var result = SanguoCampaignContentSchemaCatalog.ValidateRawFixture(
            SanguoCampaignContentFamily.Boss,
            rawFixture,
            CreateKnownReferences(),
            previousCatalogVersion: 1,
            currentCatalogVersion: 2,
            hasBreakingChange: false);

        result.IsValid.Should().BeFalse();
        result.ErrorCodes.Should().Contain(SanguoCampaignContentSchemaCatalog.InvalidFieldTypePowerError);
    }

    // ACC:T131.1
    [Fact]
    [Trait("acceptance", "ACC:T131.1")]
    public void ShouldFailValidation_WhenBossDifficultyProfileSchemaVersionTypeIsInvalid()
    {
        var rawFixture = CreateValidBossDifficultyProfile();
        rawFixture["schemaVersion"] = "1";

        var result = SanguoCampaignContentSchemaCatalog.ValidateRawFixture(
            SanguoCampaignContentFamily.Boss,
            rawFixture,
            CreateKnownReferences(),
            previousCatalogVersion: 1,
            currentCatalogVersion: 2,
            hasBreakingChange: false);

        result.IsValid.Should().BeFalse();
        result.ErrorCodes.Should().Contain(SanguoCampaignContentSchemaCatalog.InvalidFieldTypeSchemaVersionError);
    }

    // ACC:T131.1
    [Fact]
    [Trait("acceptance", "ACC:T131.1")]
    public void ShouldFailValidation_WhenBossDifficultyProfileRefIdDoesNotResolve()
    {
        var rawFixture = CreateValidBossDifficultyProfile();
        rawFixture["refId"] = "boss-template-unknown";

        var result = SanguoCampaignContentSchemaCatalog.ValidateRawFixture(
            SanguoCampaignContentFamily.Boss,
            rawFixture,
            CreateKnownReferences(),
            previousCatalogVersion: 1,
            currentCatalogVersion: 2,
            hasBreakingChange: false);

        result.IsValid.Should().BeFalse();
        result.ErrorCodes.Should().Contain(SanguoCampaignContentSchemaCatalog.BadReferenceError);
    }

    private static HashSet<string> CreateKnownReferences()
    {
        return new HashSet<string>
        {
            "boss-template-001",
        };
    }

    private static Dictionary<string, object?> CreateValidBossDifficultyProfile()
    {
        return new Dictionary<string, object?>
        {
            ["id"] = "boss-hard-01",
            ["power"] = 50,
            ["schemaVersion"] = 1,
            ["refId"] = "boss-template-001",
        };
    }
}
