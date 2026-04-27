using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task169SplitTests
{
    private static readonly string[] ExpectedCampaignDatasetTypes =
    {
        "boss",
        "building",
        "commander",
        "objective",
        "strategem",
    };

    // ACC:T169.1
    [Fact]
    [Trait("acceptance", "ACC:T169.1")]
    public void ShouldInventoryCampaignContractSurface_WhenDiscoveringDomainEventsAndDtos()
    {
        var campaignEventTypes = GetCampaignEventTypes();
        var dtoTypeNames = typeof(EventTypes).Assembly
            .GetTypes()
            .Where(type =>
                typeof(IEventData).IsAssignableFrom(type) &&
                type.IsClass &&
                !type.IsAbstract &&
                type.Namespace is not null &&
                type.Namespace.StartsWith("Game.Core.Contracts", StringComparison.Ordinal))
            .Select(type => type.Name)
            .ToHashSet(StringComparer.Ordinal);

        campaignEventTypes.Should().NotBeEmpty("campaign contract surface must expose domain events");

        var expectedDtoTypeNames = campaignEventTypes
            .Select(ToDtoTypeNameFromEventType)
            .ToArray();

        var missingDtoTypes = expectedDtoTypeNames
            .Where(dtoTypeName => !dtoTypeNames.Contains(dtoTypeName))
            .ToArray();

        missingDtoTypes.Should().BeEmpty("campaign contract surface must be fully inventoried by domain events and DTOs");
    }

    // ACC:T169.2
    [Fact]
    [Trait("acceptance", "ACC:T169.2")]
    public void ShouldDeclareAndResolveCampaignContractRegistry_WhenUsingKnownDatasetTypes()
    {
        var registryDatasetTypes = SanguoCampaignContentSchemaCatalog.DatasetTypeMap.Keys
            .OrderBy(datasetType => datasetType, StringComparer.Ordinal)
            .ToArray();

        registryDatasetTypes.Should().BeEquivalentTo(ExpectedCampaignDatasetTypes);

        foreach (var datasetType in ExpectedCampaignDatasetTypes)
        {
            var isResolved = SanguoCampaignContentSchemaCatalog.TryResolveFamily(datasetType, out _);
            isResolved.Should().BeTrue($"dataset type '{datasetType}' must be discoverable in the registry");
        }
    }

    // ACC:T169.3
    [Fact]
    [Trait("acceptance", "ACC:T169.3")]
    public void ShouldFollowContractTemplate_WhenInspectingEventDataDtos()
    {
        var dtoTypes = typeof(EventTypes).Assembly
            .GetTypes()
            .Where(type =>
                typeof(IEventData).IsAssignableFrom(type) &&
                type.IsClass &&
                !type.IsAbstract &&
                type.Namespace is not null &&
                type.Namespace.StartsWith("Game.Core.Contracts", StringComparison.Ordinal))
            .ToArray();

        dtoTypes.Should().NotBeEmpty("contract template checks require at least one DTO");
        dtoTypes.Should().OnlyContain(type => type.IsSealed, "event DTO contracts must be sealed");
        dtoTypes.Should().OnlyContain(
            type => type.GetFields(BindingFlags.Public | BindingFlags.Instance).Length == 0,
            "event DTO contracts should not expose mutable public fields");
        dtoTypes.Should().OnlyContain(
            type => type.GetConstructors(BindingFlags.Public | BindingFlags.Instance).Length == 1,
            "event DTO contracts should keep a single public construction path");
    }

    // ACC:T169.4
    [Fact]
    [Trait("acceptance", "ACC:T169.4")]
    public void ShouldBlockTaskAdvance_WhenExplicitVersioningHookIsAbsent()
    {
        var markdownWithoutVersioningHook =
            "# Campaign Contract Set\n"
            + "\n"
            + "deprecation: active\n"
            + "note: versioning hook intentionally absent\n";
        var canAdvanceTask = SanguoCampaignContentSchemaCatalog.CanAdvanceTaskWithVersioningMetadata(
            markdownWithoutVersioningHook);

        canAdvanceTask.Should().BeFalse("task must not advance when explicit versioning hooks are absent");
    }

    // ACC:T169.5
    [Fact]
    [Trait("acceptance", "ACC:T169.5")]
    public void ShouldPreserveAdditiveCompatibility_WhenReadingActionExplainPayloadAcrossVersions()
    {
        const string v1Payload = """
                                 {"ExplainCode":"second_action_refused","SourceTag":"objective_reward"}
                                 """;
        const string v2Payload = """
                                 {
                                   "ExplainCode":"reward_draft_commit_selected",
                                   "SourceTag":"objective_reward",
                                   "ReasonCode":"already_played_this_turn",
                                   "GameId":"g-001",
                                   "TurnNumber":12,
                                   "RoundNumber":3,
                                   "PlayerId":"p1",
                                   "UnknownFutureField":"ignored"
                                 }
                                 """;

        var parsedV1 = JsonSerializer.Deserialize<SanguoActionExplainEventData>(v1Payload);
        var parsedV2 = JsonSerializer.Deserialize<SanguoActionExplainEventData>(v2Payload);

        parsedV1.Should().NotBeNull();
        parsedV1!.ExplainCode.Should().Be("second_action_refused");
        parsedV1.SourceTag.Should().Be("objective_reward");
        parsedV1.ReasonCode.Should().BeNull();

        parsedV2.Should().NotBeNull();
        parsedV2!.ExplainCode.Should().Be("reward_draft_commit_selected");
        parsedV2.SourceTag.Should().Be("objective_reward");
        parsedV2.ReasonCode.Should().Be("already_played_this_turn");
        parsedV2.GameId.Should().Be("g-001");
        parsedV2.TurnNumber.Should().Be(12);
        parsedV2.RoundNumber.Should().Be(3);
        parsedV2.PlayerId.Should().Be("p1");
    }

    // ACC:T169.6
    [Fact]
    [Trait("acceptance", "ACC:T169.6")]
    public void ShouldProduceDeterministicVersioningDecisions_WhenBreakingChangeMetadataChanges()
    {
        var knownReferences = new HashSet<string>(StringComparer.Ordinal)
        {
            "ref-alpha",
        };
        var fixture = new SanguoCampaignContentFixture(
            Id: "boss-001",
            Power: 50,
            SchemaVersion: 1,
            RefId: "ref-alpha");

        var rejectedResult = SanguoCampaignContentSchemaCatalog.ValidateFixture(
            SanguoCampaignContentFamily.Boss,
            fixture,
            knownReferences,
            previousCatalogVersion: 2,
            currentCatalogVersion: 2,
            hasBreakingChange: true);

        var acceptedResult = SanguoCampaignContentSchemaCatalog.ValidateFixture(
            SanguoCampaignContentFamily.Boss,
            fixture,
            knownReferences,
            previousCatalogVersion: 2,
            currentCatalogVersion: 3,
            hasBreakingChange: true);

        rejectedResult.IsValid.Should().BeFalse();
        rejectedResult.ErrorCodes.Should().Contain(SanguoCampaignContentSchemaCatalog.MissingVersionBumpError);

        acceptedResult.IsValid.Should().BeTrue();
        acceptedResult.ErrorCodes.Should().BeEmpty();
    }

    private static string[] GetCampaignEventTypes()
    {
        return typeof(EventTypes)
            .GetFields(BindingFlags.Public | BindingFlags.Static)
            .Where(field => field is { IsLiteral: true, IsInitOnly: false } && field.FieldType == typeof(string))
            .Select(field => field.GetRawConstantValue() as string ?? string.Empty)
            .Where(eventType =>
                eventType.Contains(".campaign.", StringComparison.OrdinalIgnoreCase) ||
                eventType.Contains(".sanguo.", StringComparison.OrdinalIgnoreCase))
            .OrderBy(eventType => eventType, StringComparer.Ordinal)
            .ToArray();
    }

    private static string ToDtoTypeNameFromEventType(string eventType)
    {
        var normalizedSegments = eventType
            .Split('.', StringSplitOptions.RemoveEmptyEntries)
            .Where(segment => !segment.Equals("core", StringComparison.OrdinalIgnoreCase))
            .Select(ToPascalCaseSegment);

        return string.Concat(normalizedSegments) + "EventData";
    }

    private static string ToPascalCaseSegment(string segment)
    {
        if (segment.Length == 0)
        {
            return string.Empty;
        }

        if (segment.Length == 1)
        {
            return char.ToUpperInvariant(segment[0]).ToString();
        }

        return char.ToUpperInvariant(segment[0]) + segment[1..];
    }
}
