using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Game.Core.Ports;
using Game.Core.Services.Sanguo;
using System;
using System.Collections.Generic;
using System.Text.Json;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task57ActionCardPolicyTests
{
    // ACC:T57.1
    // ACC:T57.2
    [Fact]
    public void ShouldFilterCards_WhenEffectKindIsInvalid()
    {
        var loader = new TestResourceLoader
        {
            OnLoadText = path => path == SanguoActionCardsCatalogLoader.ActionCardsResPath
                ? BuildCatalogJson(includeInvalidEffectKind: true)
                : null,
        };

        var ok = SanguoActionCardsCatalogLoader.TryLoadActionCardsCatalog(loader, out var catalog, out var error);

        ok.Should().BeTrue(error);
        loader.LoadTextCalls.Should().Equal(SanguoActionCardsCatalogLoader.ActionCardsResPath);
        catalog.SchemaVersion.Should().Be(1);
        catalog.Version.Should().Be(1);
        catalog.Cards.Should().ContainSingle(c => c.CardId == "ac_valid");
        catalog.Cards.Should().NotContain(c => c.CardId == "ac_invalid_kind");
    }

    // ACC:T57.1
    [Theory]
    [InlineData("cardId")]
    [InlineData("nameKey")]
    [InlineData("descriptionKey")]
    [InlineData("effectKind")]
    [InlineData("stepDelta")]
    [InlineData("durationRounds")]
    public void ShouldFilterCard_WhenRequiredFieldMissing(string missingKey)
    {
        var loader = new TestResourceLoader
        {
            OnLoadText = path => path == SanguoActionCardsCatalogLoader.ActionCardsResPath
                ? BuildCatalogJsonWithSingleCard(missingKey: missingKey)
                : null,
        };

        var ok = SanguoActionCardsCatalogLoader.TryLoadActionCardsCatalog(loader, out var catalog, out var error);

        ok.Should().BeTrue(error);
        catalog.Cards.Should().BeEmpty("cards with missing required fields must not be loaded");
    }

    // ACC:T57.1
    [Fact]
    public void ShouldRejectCatalog_WhenCardFieldHasWrongType()
    {
        var loader = new TestResourceLoader
        {
            OnLoadText = path => path == SanguoActionCardsCatalogLoader.ActionCardsResPath
                ? "{\"schemaVersion\":1,\"version\":1,\"cards\":[{\"cardId\":\"ac_bad\",\"nameKey\":\"k\",\"descriptionKey\":\"d\",\"effectKind\":\"economyStepDelta\",\"stepDelta\":1,\"durationRounds\":\"oops\"}]}"
                : null,
        };

        var ok = SanguoActionCardsCatalogLoader.TryLoadActionCardsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_action_cards_catalog:card_field_type:durationRounds");
    }

    [Fact]
    public void ShouldRejectCatalog_WhenRootIsNotObject()
    {
        var loader = new TestResourceLoader
        {
            OnLoadText = path => path == SanguoActionCardsCatalogLoader.ActionCardsResPath
                ? "[]"
                : null,
        };

        var ok = SanguoActionCardsCatalogLoader.TryLoadActionCardsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_action_cards_catalog:root_not_object");
    }

    [Fact]
    public void ShouldRejectCatalog_WhenCardsIsNotArray()
    {
        var loader = new TestResourceLoader
        {
            OnLoadText = path => path == SanguoActionCardsCatalogLoader.ActionCardsResPath
                ? "{\"schemaVersion\":1,\"version\":1,\"cards\":{}}"
                : null,
        };

        var ok = SanguoActionCardsCatalogLoader.TryLoadActionCardsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_action_cards_catalog:cards_not_array");
    }

    [Fact]
    public void ShouldRejectCatalog_WhenCardIsNotObject()
    {
        var loader = new TestResourceLoader
        {
            OnLoadText = path => path == SanguoActionCardsCatalogLoader.ActionCardsResPath
                ? "{\"schemaVersion\":1,\"version\":1,\"cards\":[1]}"
                : null,
        };

        var ok = SanguoActionCardsCatalogLoader.TryLoadActionCardsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_action_cards_catalog:card_not_object");
    }

    [Fact]
    public void ShouldLoadEmptyCatalog_WhenCardsPropertyIsMissing()
    {
        var loader = new TestResourceLoader
        {
            OnLoadText = path => path == SanguoActionCardsCatalogLoader.ActionCardsResPath
                ? "{\"schemaVersion\":1,\"version\":1}"
                : null,
        };

        var ok = SanguoActionCardsCatalogLoader.TryLoadActionCardsCatalog(loader, out var catalog, out var error);

        ok.Should().BeTrue(error);
        catalog.SchemaVersion.Should().Be(1);
        catalog.Version.Should().Be(1);
        catalog.Cards.Should().BeEmpty();
    }

    [Fact]
    public void ShouldRejectCatalog_WhenSchemaVersionHasWrongType()
    {
        var loader = new TestResourceLoader
        {
            OnLoadText = path => path == SanguoActionCardsCatalogLoader.ActionCardsResPath
                ? "{\"schemaVersion\":\"1\",\"version\":1,\"cards\":[]}"
                : null,
        };

        var ok = SanguoActionCardsCatalogLoader.TryLoadActionCardsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_action_cards_catalog:bad_versions");
    }

    [Fact]
    public void ShouldRejectCatalog_WhenStepDeltaIsNonIntegral()
    {
        var loader = new TestResourceLoader
        {
            OnLoadText = path => path == SanguoActionCardsCatalogLoader.ActionCardsResPath
                ? "{\"schemaVersion\":1,\"version\":1,\"cards\":[{\"cardId\":\"ac_bad\",\"nameKey\":\"k\",\"descriptionKey\":\"d\",\"effectKind\":\"economyStepDelta\",\"stepDelta\":1.25,\"durationRounds\":3}]}"
                : null,
        };

        var ok = SanguoActionCardsCatalogLoader.TryLoadActionCardsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_action_cards_catalog:card_field_type:stepDelta");
    }

    [Theory]
    [InlineData(7)]
    [InlineData(-7)]
    public void ShouldFilterCard_WhenStepDeltaIsOutOfBounds(int stepDelta)
    {
        var loader = new TestResourceLoader
        {
            OnLoadText = path => path == SanguoActionCardsCatalogLoader.ActionCardsResPath
                ? BuildCatalogJsonWithSingleCardOverrides(stepDelta: stepDelta, durationRounds: 3)
                : null,
        };

        var ok = SanguoActionCardsCatalogLoader.TryLoadActionCardsCatalog(loader, out var catalog, out var error);

        ok.Should().BeTrue(error);
        catalog.Cards.Should().BeEmpty("stepDelta outside the allow-list range must be filtered out");
    }

    [Fact]
    public void ShouldFilterCard_WhenDurationRoundsIsTooLarge()
    {
        var loader = new TestResourceLoader
        {
            OnLoadText = path => path == SanguoActionCardsCatalogLoader.ActionCardsResPath
                ? BuildCatalogJsonWithSingleCardOverrides(stepDelta: 1, durationRounds: 1001)
                : null,
        };

        var ok = SanguoActionCardsCatalogLoader.TryLoadActionCardsCatalog(loader, out var catalog, out var error);

        ok.Should().BeTrue(error);
        catalog.Cards.Should().BeEmpty("durationRounds above the hard cap must be filtered out");
    }

    [Fact]
    public void ShouldRejectCatalog_WhenSchemaOrContentVersionIsInvalid()
    {
        var loader = new TestResourceLoader
        {
            OnLoadText = path => path == SanguoActionCardsCatalogLoader.ActionCardsResPath
                ? "{\"schemaVersion\":0,\"version\":1,\"cards\":[]}"
                : null,
        };

        var ok = SanguoActionCardsCatalogLoader.TryLoadActionCardsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_action_cards_catalog:bad_versions");
    }

    private static string BuildCatalogJson(bool includeInvalidEffectKind)
    {
        var cards = new List<Dictionary<string, object?>>
        {
            new()
            {
                ["cardId"] = "ac_valid",
                ["nameKey"] = "card.ac_valid.name",
                ["descriptionKey"] = "card.ac_valid.desc",
                ["effectKind"] = "economyStepDelta",
                ["stepDelta"] = -1,
                ["durationRounds"] = 3,
            },
        };

        if (includeInvalidEffectKind)
        {
            cards.Add(new Dictionary<string, object?>
            {
                ["cardId"] = "ac_invalid_kind",
                ["nameKey"] = "card.ac_invalid_kind.name",
                ["descriptionKey"] = "card.ac_invalid_kind.desc",
                ["effectKind"] = "moneyDelta",
                ["stepDelta"] = 1,
                ["durationRounds"] = 3,
            });
        }

        var root = new Dictionary<string, object?>
        {
            ["schemaVersion"] = 1,
            ["version"] = 1,
            ["cards"] = cards,
        };

        return JsonSerializer.Serialize(root);
    }

    private static string BuildCatalogJsonWithSingleCard(string missingKey)
    {
        var card = new Dictionary<string, object?>
        {
            ["cardId"] = "ac_valid",
            ["nameKey"] = "card.ac_valid.name",
            ["descriptionKey"] = "card.ac_valid.desc",
            ["effectKind"] = "economyStepDelta",
            ["stepDelta"] = -1,
            ["durationRounds"] = 3,
        };

        card.Remove(missingKey);

        var root = new Dictionary<string, object?>
        {
            ["schemaVersion"] = 1,
            ["version"] = 1,
            ["cards"] = new List<Dictionary<string, object?>> { card },
        };

        return JsonSerializer.Serialize(root);
    }

    private static string BuildCatalogJsonWithSingleCardOverrides(int stepDelta, int durationRounds)
    {
        var card = new Dictionary<string, object?>
        {
            ["cardId"] = "ac_valid",
            ["nameKey"] = "card.ac_valid.name",
            ["descriptionKey"] = "card.ac_valid.desc",
            ["effectKind"] = "economyStepDelta",
            ["stepDelta"] = stepDelta,
            ["durationRounds"] = durationRounds,
        };

        var root = new Dictionary<string, object?>
        {
            ["schemaVersion"] = 1,
            ["version"] = 1,
            ["cards"] = new List<Dictionary<string, object?>> { card },
        };

        return JsonSerializer.Serialize(root);
    }

    private sealed class TestResourceLoader : IResourceLoader
    {
        public Func<string, string?>? OnLoadText { get; init; }
        public List<string> LoadTextCalls { get; } = new();

        public string? LoadText(string path)
        {
            LoadTextCalls.Add(path);
            return OnLoadText?.Invoke(path);
        }

        public byte[]? LoadBytes(string path) => null;
    }
}
