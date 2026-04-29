using System;
using System.Collections.Generic;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task148CampaignContentCiEvidenceTests
{
    // ACC:T148.1
    [Fact]
    public void ShouldEmitPinpointedCiEvidence_WhenFixtureFailsCrossReferenceGate()
    {
        var rawFixture = new Dictionary<string, object?>
        {
            ["id"] = "strategem-001",
            ["power"] = 20,
            ["schemaVersion"] = 1,
            ["refId"] = "missing-ref",
            ["localeKey"] = "campaign.strategem.001.title",
        };

        var knownReferences = new HashSet<string>(StringComparer.Ordinal)
        {
            "existing-ref",
        };

        var result = SanguoCampaignContentSchemaCatalog.ValidateRawFixture(
            SanguoCampaignContentFamily.Strategem,
            rawFixture,
            knownReferences,
            previousCatalogVersion: 1,
            currentCatalogVersion: 1,
            hasBreakingChange: false);

        result.IsValid.Should().BeFalse();
        result.ErrorCodes.Should().Contain(code =>
            code.Contains("gate=CrossReference", StringComparison.Ordinal) &&
            code.Contains("field=refId", StringComparison.Ordinal) &&
            code.Contains("path=campaign/strategem/invalid_missing_ref.json", StringComparison.Ordinal));
    }

    [Fact]
    public void ShouldKeepFixtureValid_WhenAllMandatoryGatesPass()
    {
        var rawFixture = new Dictionary<string, object?>
        {
            ["id"] = "commander-001",
            ["power"] = 50,
            ["schemaVersion"] = 2,
        };

        var knownReferences = new HashSet<string>(StringComparer.Ordinal);

        var result = SanguoCampaignContentSchemaCatalog.ValidateRawFixture(
            SanguoCampaignContentFamily.Commander,
            rawFixture,
            knownReferences,
            previousCatalogVersion: 1,
            currentCatalogVersion: 2,
            hasBreakingChange: false);

        result.IsValid.Should().BeTrue();
        result.ErrorCodes.Should().BeEmpty();
    }

    [Fact]
    // ACC:T148.1
    public void ShouldReportVersionAndI18nGateNames_WhenBreakingChangeLacksVersionBumpAndLocalizationCoverage()
    {
        var rawFixture = new Dictionary<string, object?>
        {
            ["id"] = "objective-001",
            ["power"] = 40,
            ["schemaVersion"] = 3,
            ["refId"] = "objective-ref",
            ["localeKey"] = "",
        };

        var knownReferences = new HashSet<string>(StringComparer.Ordinal)
        {
            "objective-ref",
        };

        var result = SanguoCampaignContentSchemaCatalog.ValidateRawFixture(
            SanguoCampaignContentFamily.Objective,
            rawFixture,
            knownReferences,
            previousCatalogVersion: 3,
            currentCatalogVersion: 3,
            hasBreakingChange: true);

        result.IsValid.Should().BeFalse();
        result.ErrorCodes.Should().Contain(code =>
            code.Contains("gate=VersionBump", StringComparison.Ordinal) &&
            code.Contains("field=schemaVersion", StringComparison.Ordinal) &&
            code.Contains("path=campaign/objective/objective-001.json", StringComparison.Ordinal));
        result.ErrorCodes.Should().Contain(code =>
            code.Contains("gate=I18nCoverage", StringComparison.Ordinal) &&
            code.Contains("field=localeKey", StringComparison.Ordinal) &&
            code.Contains("path=campaign/objective/objective-001.json", StringComparison.Ordinal));
    }

    // ACC:T148.3
    [Fact]
    public void ShouldReuseSharedCatalogValidationInfrastructure_WhenRawFixtureMatchesTypedFixtureScenario()
    {
        var knownReferences = new HashSet<string>(StringComparer.Ordinal)
        {
            "existing-ref",
        };

        var rawFixture = new Dictionary<string, object?>
        {
            ["id"] = "strategem-001",
            ["power"] = 20,
            ["schemaVersion"] = 1,
            ["refId"] = "missing-ref",
            ["localeKey"] = "campaign.strategem.001.title",
        };

        var rawResult = SanguoCampaignContentSchemaCatalog.ValidateRawFixture(
            SanguoCampaignContentFamily.Strategem,
            rawFixture,
            knownReferences,
            previousCatalogVersion: 1,
            currentCatalogVersion: 1,
            hasBreakingChange: false);

        var typedResult = SanguoCampaignContentSchemaCatalog.ValidateFixture(
            SanguoCampaignContentFamily.Strategem,
            new SanguoCampaignContentFixture(
                Id: "strategem-001",
                Power: 20,
                SchemaVersion: 1,
                RefId: "missing-ref"),
            knownReferences,
            previousCatalogVersion: 1,
            currentCatalogVersion: 1,
            hasBreakingChange: false);

        rawResult.IsValid.Should().BeFalse();
        typedResult.IsValid.Should().BeFalse();
        rawResult.ErrorCodes.Should().Contain(SanguoCampaignContentSchemaCatalog.BadReferenceError);
        typedResult.ErrorCodes.Should().Contain(SanguoCampaignContentSchemaCatalog.BadReferenceError);
    }

    // ACC:T148.5
    [Fact]
    public void ShouldFailValidationToSupportCiHardGateBlocking_WhenMandatoryGateBreaks()
    {
        var rawFixture = new Dictionary<string, object?>
        {
            ["id"] = "strategem-001",
            ["power"] = 20,
            ["schemaVersion"] = 1,
            ["refId"] = "missing-ref",
            ["localeKey"] = "campaign.strategem.001.title",
        };

        var knownReferences = new HashSet<string>(StringComparer.Ordinal)
        {
            "existing-ref",
        };

        var result = SanguoCampaignContentSchemaCatalog.ValidateRawFixture(
            SanguoCampaignContentFamily.Strategem,
            rawFixture,
            knownReferences,
            previousCatalogVersion: 1,
            currentCatalogVersion: 1,
            hasBreakingChange: false);

        result.IsValid.Should().BeFalse();
        result.ErrorCodes.Should().Contain(code =>
            code.Contains("gate=CrossReference", StringComparison.Ordinal) &&
            code.Contains("field=refId", StringComparison.Ordinal) &&
            code.Contains("path=campaign/strategem/invalid_missing_ref.json", StringComparison.Ordinal));
    }

    // ACC:T148.2
    [Fact]
    public void ShouldNotReportI18nCoverage_WhenLocaleKeyIsPresentEvenIfVersionBumpFails()
    {
        var rawFixture = new Dictionary<string, object?>
        {
            ["id"] = "objective-001",
            ["power"] = 40,
            ["schemaVersion"] = 3,
            ["refId"] = "objective-ref",
            ["localeKey"] = "campaign.objective.001.title",
        };

        var knownReferences = new HashSet<string>(StringComparer.Ordinal)
        {
            "objective-ref",
        };

        var result = SanguoCampaignContentSchemaCatalog.ValidateRawFixture(
            SanguoCampaignContentFamily.Objective,
            rawFixture,
            knownReferences,
            previousCatalogVersion: 3,
            currentCatalogVersion: 3,
            hasBreakingChange: true);

        result.IsValid.Should().BeFalse();
        result.ErrorCodes.Should().Contain(code => code.Contains("gate=VersionBump", StringComparison.Ordinal));
        result.ErrorCodes.Should().NotContain(code => code.Contains("gate=I18nCoverage", StringComparison.Ordinal));
    }

    // ACC:T148.4
    [Fact]
    public void ShouldReportI18nCoverage_WhenLocaleKeyIsMissingEvenIfVersionBumpPasses()
    {
        var rawFixture = new Dictionary<string, object?>
        {
            ["id"] = "objective-001",
            ["power"] = 40,
            ["schemaVersion"] = 4,
            ["refId"] = "objective-ref",
            ["localeKey"] = "",
        };

        var knownReferences = new HashSet<string>(StringComparer.Ordinal)
        {
            "objective-ref",
        };

        var result = SanguoCampaignContentSchemaCatalog.ValidateRawFixture(
            SanguoCampaignContentFamily.Objective,
            rawFixture,
            knownReferences,
            previousCatalogVersion: 3,
            currentCatalogVersion: 4,
            hasBreakingChange: true);

        result.IsValid.Should().BeFalse();
        result.ErrorCodes.Should().Contain(code =>
            code.Contains("gate=I18nCoverage", StringComparison.Ordinal) &&
            code.Contains("field=localeKey", StringComparison.Ordinal) &&
            code.Contains("path=campaign/objective/objective-001.json", StringComparison.Ordinal));
        result.ErrorCodes.Should().NotContain(SanguoCampaignContentSchemaCatalog.MissingVersionBumpError);
    }
}
