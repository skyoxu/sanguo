using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task171SplitTests
{
    private const string VersioningRuleDocumentPath = "docs/architecture/overlays/PRD-SANGUO-V3/08/08-Contracts-Quality-Metrics.md";

    private static readonly SanguoCampaignContentFamily[] ExpectedFamilies =
    {
        SanguoCampaignContentFamily.Commander,
        SanguoCampaignContentFamily.Strategem,
        SanguoCampaignContentFamily.Building,
        SanguoCampaignContentFamily.Boss,
        SanguoCampaignContentFamily.Objective,
    };

    private static readonly string[] ExpectedDatasetTypes =
    {
        "commander",
        "strategem",
        "building",
        "boss",
        "objective",
    };

    // ACC:T171.1
    [Fact]
    [Trait("acceptance", "ACC:T171.1")]
    public void ShouldExposeAllExtendedFamilies_WhenReadingProductionSchemaCatalog()
    {
        var definitions = SanguoCampaignContentSchemaCatalog.Definitions;

        definitions.Keys.Should().BeEquivalentTo(ExpectedFamilies);
    }

    // ACC:T171.2
    [Fact]
    [Trait("acceptance", "ACC:T171.2")]
    public void ShouldDefineMachineCheckableContracts_WhenReadingProductionSchemaCatalog()
    {
        var definitions = SanguoCampaignContentSchemaCatalog.Definitions;

        foreach (var family in ExpectedFamilies)
        {
            var definition = definitions[family];
            definition.HasOnlyMachineCheckableConstraints.Should().BeTrue();
            definition.RequiredFields.Should().Contain(new[] { "id", "power", "schemaVersion" });
            definition.FieldTypes["id"].Should().Be("string");
            definition.FieldTypes["power"].Should().Be("int32");
            definition.FieldTypes["schemaVersion"].Should().Be("int32");
            definition.FieldTypes["refId"].Should().Be("string?");
            definition.MinPower.Should().BeLessThan(definition.MaxPower);
        }

        definitions[SanguoCampaignContentFamily.Commander].RequiresReference.Should().BeFalse();
        definitions[SanguoCampaignContentFamily.Strategem].RequiresReference.Should().BeTrue();
        definitions[SanguoCampaignContentFamily.Building].RequiresReference.Should().BeTrue();
        definitions[SanguoCampaignContentFamily.Boss].RequiresReference.Should().BeTrue();
        definitions[SanguoCampaignContentFamily.Objective].RequiresReference.Should().BeTrue();
    }

    // ACC:T171.3
    [Fact]
    [Trait("acceptance", "ACC:T171.3")]
    public void ShouldValidateMinimalFixtures_WhenFixtureIsValidOrInvalid()
    {
        foreach (var family in ExpectedFamilies)
        {
            var knownReferences = CreateKnownReferences();
            var validFixture = CreateMinimalValidFixture();

            var validResult = SanguoCampaignContentSchemaCatalog.ValidateFixture(
                family,
                validFixture,
                knownReferences,
                previousCatalogVersion: 1,
                currentCatalogVersion: 2,
                hasBreakingChange: false);

            validResult.IsValid.Should().BeTrue();

            var missingIdFixture = validFixture with { Id = string.Empty };
            var missingIdResult = SanguoCampaignContentSchemaCatalog.ValidateFixture(
                family,
                missingIdFixture,
                knownReferences,
                previousCatalogVersion: 1,
                currentCatalogVersion: 2,
                hasBreakingChange: false);

            missingIdResult.IsValid.Should().BeFalse();
            missingIdResult.ErrorCodes.Should().Contain(SanguoCampaignContentSchemaCatalog.MissingRequiredFieldIdError);

            var badRefFixture = validFixture with { RefId = "missing-ref" };
            var badRefResult = SanguoCampaignContentSchemaCatalog.ValidateFixture(
                family,
                badRefFixture,
                knownReferences,
                previousCatalogVersion: 1,
                currentCatalogVersion: 2,
                hasBreakingChange: false);

            if (SanguoCampaignContentSchemaCatalog.Definitions[family].RequiresReference)
            {
                badRefResult.IsValid.Should().BeFalse();
                badRefResult.ErrorCodes.Should().Contain(SanguoCampaignContentSchemaCatalog.BadReferenceError);
            }
            else
            {
                badRefResult.IsValid.Should().BeTrue();
            }
        }
    }

    // ACC:T171.4
    [Fact]
    [Trait("acceptance", "ACC:T171.4")]
    public void ShouldRejectFieldTypeMismatches_WhenValidatingRawFixtures()
    {
        foreach (var family in ExpectedFamilies)
        {
            var rawFixture = new Dictionary<string, object?>
            {
                ["id"] = 123,
                ["power"] = "10",
                ["schemaVersion"] = "1",
                ["refId"] = 99,
            };

            var result = SanguoCampaignContentSchemaCatalog.ValidateRawFixture(
                family,
                rawFixture,
                CreateKnownReferences(),
                previousCatalogVersion: 1,
                currentCatalogVersion: 2,
                hasBreakingChange: false);

            result.IsValid.Should().BeFalse();
            result.ErrorCodes.Should().Contain(SanguoCampaignContentSchemaCatalog.InvalidFieldTypeIdError);
            result.ErrorCodes.Should().Contain(SanguoCampaignContentSchemaCatalog.InvalidFieldTypePowerError);
            result.ErrorCodes.Should().Contain(SanguoCampaignContentSchemaCatalog.InvalidFieldTypeSchemaVersionError);
            result.ErrorCodes.Should().Contain(SanguoCampaignContentSchemaCatalog.InvalidFieldTypeRefIdError);
        }
    }

    // ACC:T171.5
    [Fact]
    [Trait("acceptance", "ACC:T171.5")]
    public void ShouldEnforceDatasetInventoryParity_WhenBuildingStrictLoaderCatalog()
    {
        var success = SanguoCampaignContentSchemaCatalog.TryBuildStrictLoaderCatalog(
            ExpectedDatasetTypes,
            out var strictCatalog,
            out var successError);

        success.Should().BeTrue(successError);
        strictCatalog.Keys.Should().BeEquivalentTo(ExpectedDatasetTypes);
        strictCatalog.Values.Should().BeEquivalentTo(ExpectedFamilies);
        strictCatalog.Values.Should().OnlyHaveUniqueItems();

        SanguoCampaignContentSchemaCatalog.Definitions.Keys.Should().BeEquivalentTo(strictCatalog.Values);
        SanguoCampaignContentSchemaCatalog.DatasetTypeMap.Values.Should().BeEquivalentTo(ExpectedFamilies);

        var missingOne = SanguoCampaignContentSchemaCatalog.TryBuildStrictLoaderCatalog(
            new[] { "commander", "strategem", "building", "boss" },
            out _,
            out var missingError);
        missingOne.Should().BeFalse();
        missingError.Should().Be(SanguoCampaignContentSchemaCatalog.DatasetInventoryMissingError);

        var extraOne = SanguoCampaignContentSchemaCatalog.TryBuildStrictLoaderCatalog(
            new[] { "commander", "strategem", "building", "boss", "objective", "unknown-type" },
            out _,
            out var extraError);
        extraOne.Should().BeFalse();
        extraError.Should().Be(SanguoCampaignContentSchemaCatalog.DatasetInventoryExtraError);

        var duplicateType = SanguoCampaignContentSchemaCatalog.TryBuildStrictLoaderCatalog(
            new[] { "commander", "strategem", "building", "boss", "objective", "boss" },
            out _,
            out var duplicateError);
        duplicateType.Should().BeFalse();
        duplicateError.Should().Be(SanguoCampaignContentSchemaCatalog.DatasetInventoryDuplicateError);
    }

    // ACC:T171.6
    [Fact]
    [Trait("acceptance", "ACC:T171.6")]
    public void ShouldFailValidationOnBadReferenceAndOutOfRange_WhenRunningDeterministicFixtures()
    {
        foreach (var family in ExpectedFamilies)
        {
            var knownReferences = CreateKnownReferences();
            var outOfRangeResult = SanguoCampaignContentSchemaCatalog.ValidateFixture(
                family,
                CreateMinimalValidFixture() with { Power = 101 },
                knownReferences,
                previousCatalogVersion: 1,
                currentCatalogVersion: 2,
                hasBreakingChange: false);

            outOfRangeResult.IsValid.Should().BeFalse();
            outOfRangeResult.ErrorCodes.Should().Contain(SanguoCampaignContentSchemaCatalog.OutOfRangePowerError);

            var badReferenceResult = SanguoCampaignContentSchemaCatalog.ValidateFixture(
                family,
                CreateMinimalValidFixture() with { RefId = "missing-ref" },
                knownReferences,
                previousCatalogVersion: 1,
                currentCatalogVersion: 2,
                hasBreakingChange: false);

            if (SanguoCampaignContentSchemaCatalog.Definitions[family].RequiresReference)
            {
                badReferenceResult.IsValid.Should().BeFalse();
                badReferenceResult.ErrorCodes.Should().Contain(SanguoCampaignContentSchemaCatalog.BadReferenceError);
            }
            else
            {
                badReferenceResult.IsValid.Should().BeTrue();
            }
        }
    }

    // ACC:T171.7
    [Fact]
    [Trait("acceptance", "ACC:T171.7")]
    public void ShouldKeepDefinitionsAndValidatorsConsistent_WhenCheckingReferencePolicyDeterministically()
    {
        foreach (var family in ExpectedFamilies)
        {
            var fixture = CreateMinimalValidFixture() with { RefId = "missing-ref" };
            var first = SanguoCampaignContentSchemaCatalog.ValidateFixture(
                family,
                fixture,
                CreateKnownReferences(),
                previousCatalogVersion: 1,
                currentCatalogVersion: 2,
                hasBreakingChange: false);
            var second = SanguoCampaignContentSchemaCatalog.ValidateFixture(
                family,
                fixture,
                CreateKnownReferences(),
                previousCatalogVersion: 1,
                currentCatalogVersion: 2,
                hasBreakingChange: false);

            first.IsValid.Should().Be(second.IsValid);
            first.ErrorCodes.Should().Equal(second.ErrorCodes);

            var requiresReference = SanguoCampaignContentSchemaCatalog.Definitions[family].RequiresReference;
            if (requiresReference)
            {
                first.ErrorCodes.Should().Contain(SanguoCampaignContentSchemaCatalog.BadReferenceError);
            }
            else
            {
                first.ErrorCodes.Should().NotContain(SanguoCampaignContentSchemaCatalog.BadReferenceError);
            }
        }
    }

    // ACC:T171.7
    [Fact]
    [Trait("acceptance", "ACC:T171.7")]
    public void ShouldDocumentAndEnforceSchemaEvolutionRule_WhenComparingDocsAndValidator()
    {
        var repoRoot = FindRepoRoot();
        var documentationPath = BuildDocumentationPath(repoRoot);
        File.Exists(documentationPath).Should().BeTrue();

        var markdown = File.ReadAllText(documentationPath);
        var parsed = SanguoCampaignContentSchemaCatalog.TryReadVersionRuleFromDocumentation(markdown, out var docsRule);

        parsed.Should().BeTrue();
        docsRule.Should().Be(SanguoCampaignContentSchemaCatalog.GetValidatorVersionRule());

        var missingVersionBump = SanguoCampaignContentSchemaCatalog.ValidateFixture(
            SanguoCampaignContentFamily.Boss,
            CreateMinimalValidFixture(),
            CreateKnownReferences(),
            previousCatalogVersion: 2,
            currentCatalogVersion: 2,
            hasBreakingChange: true);

        missingVersionBump.IsValid.Should().BeFalse();
        missingVersionBump.ErrorCodes.Should().Contain(SanguoCampaignContentSchemaCatalog.MissingVersionBumpError);
    }

    private static SanguoCampaignContentFixture CreateMinimalValidFixture()
    {
        return new SanguoCampaignContentFixture(Id: "entity-001", Power: 10, SchemaVersion: 1, RefId: "ref-alpha");
    }

    private static HashSet<string> CreateKnownReferences()
    {
        return new HashSet<string>(StringComparer.Ordinal) { "ref-alpha" };
    }

    private static string FindRepoRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            var markerPath = Path.Combine(directory.FullName, ".taskmaster", "tasks", "tasks.json");
            if (File.Exists(markerPath))
            {
                return directory.FullName;
            }

            directory = directory.Parent;
        }

        throw new DirectoryNotFoundException("Repo root not found (missing .taskmaster/tasks/tasks.json).");
    }

    private static string BuildDocumentationPath(string repoRoot)
    {
        var relativeParts = VersioningRuleDocumentPath.Split('/');
        return Path.Combine(new[] { repoRoot }.Concat(relativeParts).ToArray());
    }
}
