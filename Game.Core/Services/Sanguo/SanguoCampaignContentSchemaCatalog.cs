using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;

namespace Game.Core.Services.Sanguo;

public enum SanguoCampaignContentFamily
{
    Commander,
    Strategem,
    Building,
    Boss,
    Objective,
}

public sealed record SanguoCampaignSchemaDefinition(
    IReadOnlyList<string> RequiredFields,
    IReadOnlyDictionary<string, string> FieldTypes,
    int MinPower,
    int MaxPower,
    bool RequiresReference,
    bool HasOnlyMachineCheckableConstraints);

public sealed record SanguoCampaignContentFixture(
    string Id,
    int Power,
    int SchemaVersion,
    string? RefId);

public sealed record SanguoCampaignContentValidationResult(
    bool IsValid,
    IReadOnlyList<string> ErrorCodes);

public static class SanguoCampaignContentSchemaCatalog
{
    public const string VersioningRuleToken = "BreakingChangesRequireVersionBump";
    public const string MissingRequiredFieldIdError = "MissingRequiredField:id";
    public const string OutOfRangePowerError = "OutOfRangePower";
    public const string BadReferenceError = "BadReference";
    public const string MissingVersionBumpError = "MissingVersionBump";
    public const string InvalidFieldTypeIdError = "InvalidFieldType:id";
    public const string InvalidFieldTypePowerError = "InvalidFieldType:power";
    public const string InvalidFieldTypeSchemaVersionError = "InvalidFieldType:schemaVersion";
    public const string InvalidFieldTypeRefIdError = "InvalidFieldType:refId";
    public const string DatasetInventoryMissingError = "DatasetInventoryMissing";
    public const string DatasetInventoryExtraError = "DatasetInventoryExtra";
    public const string DatasetInventoryDuplicateError = "DatasetInventoryDuplicate";

    private static readonly Regex VersioningRuleRegex =
        new(@"versioning-rule\s*:\s*(?<rule>[A-Za-z0-9_]+)", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);

    private static readonly IReadOnlyDictionary<SanguoCampaignContentFamily, SanguoCampaignSchemaDefinition> DefinitionsMap =
        new Dictionary<SanguoCampaignContentFamily, SanguoCampaignSchemaDefinition>
        {
            [SanguoCampaignContentFamily.Commander] = CreateDefinition(requiresReference: false),
            [SanguoCampaignContentFamily.Strategem] = CreateDefinition(requiresReference: true),
            [SanguoCampaignContentFamily.Building] = CreateDefinition(requiresReference: true),
            [SanguoCampaignContentFamily.Boss] = CreateDefinition(requiresReference: true),
            [SanguoCampaignContentFamily.Objective] = CreateDefinition(requiresReference: true),
        };

    private static readonly IReadOnlyDictionary<string, SanguoCampaignContentFamily> DatasetTypeMapInternal =
        new Dictionary<string, SanguoCampaignContentFamily>(StringComparer.OrdinalIgnoreCase)
        {
            ["commander"] = SanguoCampaignContentFamily.Commander,
            ["strategem"] = SanguoCampaignContentFamily.Strategem,
            ["building"] = SanguoCampaignContentFamily.Building,
            ["boss"] = SanguoCampaignContentFamily.Boss,
            ["objective"] = SanguoCampaignContentFamily.Objective,
        };

    public static IReadOnlyDictionary<SanguoCampaignContentFamily, SanguoCampaignSchemaDefinition> Definitions => DefinitionsMap;

    public static IReadOnlyDictionary<string, SanguoCampaignContentFamily> DatasetTypeMap => DatasetTypeMapInternal;

    public static string GetValidatorVersionRule() => VersioningRuleToken;

    public static bool TryResolveFamily(string datasetType, out SanguoCampaignContentFamily family)
    {
        family = default;
        var normalized = (datasetType ?? string.Empty).Trim();
        if (string.IsNullOrWhiteSpace(normalized))
        {
            return false;
        }

        return DatasetTypeMapInternal.TryGetValue(normalized, out family);
    }

    public static IReadOnlyDictionary<string, SanguoCampaignContentFamily> BuildLoaderCatalog(IEnumerable<string> datasetTypes)
    {
        ArgumentNullException.ThrowIfNull(datasetTypes);

        var catalog = new Dictionary<string, SanguoCampaignContentFamily>(StringComparer.OrdinalIgnoreCase);
        foreach (var datasetType in datasetTypes)
        {
            if (!TryResolveFamily(datasetType, out var family))
            {
                continue;
            }

            catalog[datasetType.Trim()] = family;
        }

        return catalog;
    }

    public static bool TryBuildStrictLoaderCatalog(
        IEnumerable<string> datasetTypes,
        out IReadOnlyDictionary<string, SanguoCampaignContentFamily> catalog,
        out string errorCode)
    {
        ArgumentNullException.ThrowIfNull(datasetTypes);

        var mutable = new Dictionary<string, SanguoCampaignContentFamily>(StringComparer.OrdinalIgnoreCase);
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var datasetType in datasetTypes)
        {
            var normalized = (datasetType ?? string.Empty).Trim();
            if (string.IsNullOrWhiteSpace(normalized))
            {
                continue;
            }

            if (!seen.Add(normalized))
            {
                catalog = mutable;
                errorCode = DatasetInventoryDuplicateError;
                return false;
            }

            if (!TryResolveFamily(normalized, out var family))
            {
                catalog = mutable;
                errorCode = DatasetInventoryExtraError;
                return false;
            }

            mutable[normalized] = family;
        }

        if (mutable.Count != DatasetTypeMapInternal.Count)
        {
            catalog = mutable;
            errorCode = DatasetInventoryMissingError;
            return false;
        }

        if (mutable.Values.Distinct().Count() != mutable.Count)
        {
            catalog = mutable;
            errorCode = DatasetInventoryDuplicateError;
            return false;
        }

        catalog = mutable;
        errorCode = string.Empty;
        return true;
    }

    public static bool TryReadVersionRuleFromDocumentation(string markdown, out string ruleToken)
    {
        ruleToken = string.Empty;
        if (string.IsNullOrWhiteSpace(markdown))
        {
            return false;
        }

        var match = VersioningRuleRegex.Match(markdown);
        if (!match.Success)
        {
            return false;
        }

        var value = match.Groups["rule"].Value.Trim();
        if (string.IsNullOrWhiteSpace(value))
        {
            return false;
        }

        ruleToken = value;
        return true;
    }

    public static bool CanAdvanceTaskWithVersioningMetadata(string markdown)
    {
        var hasVersioningHook = TryReadVersionRuleFromDocumentation(markdown, out _);
        var hasDeprecationMetadata = !string.IsNullOrWhiteSpace(markdown)
            && markdown.Contains("deprecation", StringComparison.OrdinalIgnoreCase);
        return hasVersioningHook && hasDeprecationMetadata;
    }

    public static SanguoCampaignContentValidationResult ValidateFixture(
        SanguoCampaignContentFamily family,
        SanguoCampaignContentFixture fixture,
        ISet<string> knownReferences,
        int previousCatalogVersion,
        int currentCatalogVersion,
        bool hasBreakingChange)
    {
        ArgumentNullException.ThrowIfNull(knownReferences);

        var definition = DefinitionsMap[family];
        var errorCodes = new List<string>();

        if (string.IsNullOrWhiteSpace(fixture.Id))
        {
            errorCodes.Add(MissingRequiredFieldIdError);
        }

        if (fixture.Power < definition.MinPower || fixture.Power > definition.MaxPower)
        {
            errorCodes.Add(OutOfRangePowerError);
        }

        if (definition.RequiresReference && (string.IsNullOrWhiteSpace(fixture.RefId) || !knownReferences.Contains(fixture.RefId)))
        {
            errorCodes.Add(BadReferenceError);
        }

        if (hasBreakingChange && currentCatalogVersion <= previousCatalogVersion)
        {
            errorCodes.Add(MissingVersionBumpError);
        }

        return new SanguoCampaignContentValidationResult(IsValid: errorCodes.Count == 0, ErrorCodes: errorCodes);
    }

    public static SanguoCampaignContentValidationResult ValidateRawFixture(
        SanguoCampaignContentFamily family,
        IReadOnlyDictionary<string, object?> rawFixture,
        ISet<string> knownReferences,
        int previousCatalogVersion,
        int currentCatalogVersion,
        bool hasBreakingChange)
    {
        ArgumentNullException.ThrowIfNull(rawFixture);

        var definition = DefinitionsMap[family];
        var errors = new List<string>();

        foreach (var fieldName in rawFixture.Keys.OrderBy(name => name, StringComparer.Ordinal))
        {
            if (!definition.FieldTypes.ContainsKey(fieldName))
            {
                errors.Add($"UnknownField:{fieldName}");
            }
        }

        string id = string.Empty;
        if (!rawFixture.TryGetValue("id", out var idValue))
        {
            errors.Add(MissingRequiredFieldIdError);
        }
        else if (idValue is string idText)
        {
            id = idText;
        }
        else
        {
            errors.Add(InvalidFieldTypeIdError);
        }

        int power = 0;
        if (!rawFixture.TryGetValue("power", out var powerValue) || powerValue is not int parsedPower)
        {
            errors.Add(InvalidFieldTypePowerError);
        }
        else
        {
            power = parsedPower;
        }

        int schemaVersion = 0;
        if (!rawFixture.TryGetValue("schemaVersion", out var schemaVersionValue) || schemaVersionValue is not int parsedSchemaVersion)
        {
            errors.Add(InvalidFieldTypeSchemaVersionError);
        }
        else
        {
            schemaVersion = parsedSchemaVersion;
        }

        string? refId = null;
        if (rawFixture.TryGetValue("refId", out var refIdValue))
        {
            if (refIdValue is null)
            {
                refId = null;
            }
            else if (refIdValue is string refIdText)
            {
                refId = refIdText;
            }
            else
            {
                errors.Add(InvalidFieldTypeRefIdError);
            }
        }

        if (errors.Count > 0)
        {
            return new SanguoCampaignContentValidationResult(IsValid: false, ErrorCodes: errors);
        }

        var fixture = new SanguoCampaignContentFixture(
            Id: id,
            Power: power,
            SchemaVersion: schemaVersion,
            RefId: refId);

        return ValidateFixture(
            family,
            fixture,
            knownReferences,
            previousCatalogVersion,
            currentCatalogVersion,
            hasBreakingChange);
    }

    private static SanguoCampaignSchemaDefinition CreateDefinition(bool requiresReference)
    {
        return new SanguoCampaignSchemaDefinition(
            RequiredFields: new[] { "id", "power", "schemaVersion" },
            FieldTypes: new Dictionary<string, string>(StringComparer.Ordinal)
            {
                ["id"] = "string",
                ["power"] = "int32",
                ["schemaVersion"] = "int32",
                ["refId"] = "string?",
            },
            MinPower: 1,
            MaxPower: 100,
            RequiresReference: requiresReference,
            HasOnlyMachineCheckableConstraints: true);
    }
}
