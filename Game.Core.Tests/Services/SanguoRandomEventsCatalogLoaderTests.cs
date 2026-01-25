using FluentAssertions;
using Game.Core.Services.Sanguo;
using Game.Core.Ports;
using System;
using System.Linq;
using Xunit;

namespace Game.Core.Tests.Services;

public sealed class SanguoRandomEventsCatalogLoaderTests
{
    [Fact]
    public void TryLoadRandomEventsCatalog_ShouldLoad_WhenJsonIsValid()
    {
        var loader = new FakeResourceLoader(SanguoRandomEventsCatalogLoader.RandomEventsResPath, ValidJson);

        var ok = SanguoRandomEventsCatalogLoader.TryLoadRandomEventsCatalog(loader, out var catalog, out var error);

        ok.Should().BeTrue();
        error.Should().BeEmpty();
        catalog.SchemaVersion.Should().Be(1);
        catalog.Version.Should().Be(1);
        catalog.Events.Should().HaveCount(2);
        catalog.EventPools.Should().HaveCount(2);
        catalog.EventPools.Select(p => p.PoolId).Should().Contain(new[] { "default", "global" });
    }

    [Fact]
    public void TryLoadRandomEventsCatalog_ShouldLoadStartCombat_WhenEncounterFieldsPresent()
    {
        var loader = new FakeResourceLoader(SanguoRandomEventsCatalogLoader.RandomEventsResPath, StartCombatJson);

        var ok = SanguoRandomEventsCatalogLoader.TryLoadRandomEventsCatalog(loader, out var catalog, out var error);

        ok.Should().BeTrue();
        error.Should().BeEmpty();

        var combat = catalog.Events.Single(e => e.EventId == "event_combat_small");
        combat.EffectKind.Should().Be("startCombat");
        combat.EncounterId.Should().Be("enc_event_combat_small");
        combat.EncounterTarget.Should().Be(10);
        combat.MoneyDelta.Should().BeNull();
        combat.StepDelta.Should().BeNull();
    }

    [Fact]
    public void TryLoadRandomEventsCatalog_ShouldFail_WhenStartCombatMissingEncounterId()
    {
        var json = "{\"schemaVersion\":1,\"version\":1,"
                   + "\"eventPools\":[{\"poolId\":\"default\",\"eventIds\":[\"event_combat_small\"]},{\"poolId\":\"global\",\"eventIds\":[]}],"
                   + "\"events\":[{\"eventId\":\"event_combat_small\",\"nameKey\":\"n\",\"descriptionKey\":\"d\",\"uniqueOnce\":false,\"cooldownRounds\":0,\"effectKind\":\"startCombat\",\"encounterTarget\":10}]}";
        var loader = new FakeResourceLoader(SanguoRandomEventsCatalogLoader.RandomEventsResPath, json);

        var ok = SanguoRandomEventsCatalogLoader.TryLoadRandomEventsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_random_events_catalog:event_missing_encounterId");
    }

    [Fact]
    public void TryLoadRandomEventsCatalog_ShouldFail_WhenStartCombatEncounterTargetInvalid()
    {
        var json = "{\"schemaVersion\":1,\"version\":1,"
                   + "\"eventPools\":[{\"poolId\":\"default\",\"eventIds\":[\"event_combat_small\"]},{\"poolId\":\"global\",\"eventIds\":[]}],"
                   + "\"events\":[{\"eventId\":\"event_combat_small\",\"nameKey\":\"n\",\"descriptionKey\":\"d\",\"uniqueOnce\":false,\"cooldownRounds\":0,\"effectKind\":\"startCombat\",\"encounterId\":\"enc_event_combat_small\",\"encounterTarget\":-1}]}";
        var loader = new FakeResourceLoader(SanguoRandomEventsCatalogLoader.RandomEventsResPath, json);

        var ok = SanguoRandomEventsCatalogLoader.TryLoadRandomEventsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_random_events_catalog:event_invalid_encounterTarget");
    }

    [Fact]
    public void TryLoadRandomEventsCatalog_ShouldFail_WhenJsonMissing()
    {
        var loader = new FakeResourceLoader(SanguoRandomEventsCatalogLoader.RandomEventsResPath, null);

        var ok = SanguoRandomEventsCatalogLoader.TryLoadRandomEventsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("random_events_catalog_missing");
    }

    [Fact]
    public void TryLoadRandomEventsCatalog_ShouldFail_WhenRootNotObject()
    {
        var loader = new FakeResourceLoader(SanguoRandomEventsCatalogLoader.RandomEventsResPath, "[]");

        var ok = SanguoRandomEventsCatalogLoader.TryLoadRandomEventsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_random_events_catalog:root_not_object");
    }

    [Fact]
    public void TryLoadRandomEventsCatalog_ShouldFail_WhenVersionsMissing()
    {
        var loader = new FakeResourceLoader(SanguoRandomEventsCatalogLoader.RandomEventsResPath, "{\"eventPools\":[],\"events\":[]}");

        var ok = SanguoRandomEventsCatalogLoader.TryLoadRandomEventsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_random_events_catalog:bad_versions");
    }

    [Fact]
    public void TryLoadRandomEventsCatalog_ShouldFail_WhenEventPoolsMissing()
    {
        var loader = new FakeResourceLoader(SanguoRandomEventsCatalogLoader.RandomEventsResPath, "{\"schemaVersion\":1,\"version\":1,\"events\":[]}");

        var ok = SanguoRandomEventsCatalogLoader.TryLoadRandomEventsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_random_events_catalog:eventPools_missing");
    }

    [Fact]
    public void TryLoadRandomEventsCatalog_ShouldFail_WhenEventPoolsNotArray()
    {
        var loader = new FakeResourceLoader(SanguoRandomEventsCatalogLoader.RandomEventsResPath, "{\"schemaVersion\":1,\"version\":1,\"eventPools\":{},\"events\":[]}");

        var ok = SanguoRandomEventsCatalogLoader.TryLoadRandomEventsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_random_events_catalog:eventPools_not_array");
    }

    [Fact]
    public void TryLoadRandomEventsCatalog_ShouldFail_WhenEventPoolsEmpty()
    {
        var loader = new FakeResourceLoader(SanguoRandomEventsCatalogLoader.RandomEventsResPath, "{\"schemaVersion\":1,\"version\":1,\"eventPools\":[],\"events\":[]}");

        var ok = SanguoRandomEventsCatalogLoader.TryLoadRandomEventsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_random_events_catalog:eventPools_empty");
    }

    [Fact]
    public void TryLoadRandomEventsCatalog_ShouldFail_WhenRequiredPoolsMissing()
    {
        var json = "{\"schemaVersion\":1,\"version\":1,\"eventPools\":[{\"poolId\":\"default\",\"eventIds\":[\"a\"]}],\"events\":[{\"eventId\":\"a\",\"nameKey\":\"n\",\"descriptionKey\":\"d\",\"uniqueOnce\":false,\"cooldownRounds\":0,\"effectKind\":\"moneyDelta\",\"moneyDelta\":1}]}";
        var loader = new FakeResourceLoader(SanguoRandomEventsCatalogLoader.RandomEventsResPath, json);

        var ok = SanguoRandomEventsCatalogLoader.TryLoadRandomEventsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_random_events_catalog:missing_required_pools");
    }

    [Fact]
    public void TryLoadRandomEventsCatalog_ShouldFail_WhenPoolNotObject()
    {
        var loader = new FakeResourceLoader(SanguoRandomEventsCatalogLoader.RandomEventsResPath, "{\"schemaVersion\":1,\"version\":1,\"eventPools\":[1],\"events\":[]}");

        var ok = SanguoRandomEventsCatalogLoader.TryLoadRandomEventsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_random_events_catalog:pool_not_object");
    }

    [Fact]
    public void TryLoadRandomEventsCatalog_ShouldFail_WhenPoolMissingPoolId()
    {
        var loader = new FakeResourceLoader(SanguoRandomEventsCatalogLoader.RandomEventsResPath, "{\"schemaVersion\":1,\"version\":1,\"eventPools\":[{\"eventIds\":[]}],\"events\":[]}");

        var ok = SanguoRandomEventsCatalogLoader.TryLoadRandomEventsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_random_events_catalog:pool_missing_poolId");
    }

    [Fact]
    public void TryLoadRandomEventsCatalog_ShouldFail_WhenPoolMissingEventIds()
    {
        var loader = new FakeResourceLoader(SanguoRandomEventsCatalogLoader.RandomEventsResPath, "{\"schemaVersion\":1,\"version\":1,\"eventPools\":[{\"poolId\":\"default\"}],\"events\":[]}");

        var ok = SanguoRandomEventsCatalogLoader.TryLoadRandomEventsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_random_events_catalog:pool_missing_eventIds");
    }

    [Fact]
    public void TryLoadRandomEventsCatalog_ShouldFail_WhenPoolEventIdsNotStrings()
    {
        var loader = new FakeResourceLoader(SanguoRandomEventsCatalogLoader.RandomEventsResPath, "{\"schemaVersion\":1,\"version\":1,\"eventPools\":[{\"poolId\":\"default\",\"eventIds\":[1]}],\"events\":[]}");

        var ok = SanguoRandomEventsCatalogLoader.TryLoadRandomEventsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_random_events_catalog:pool_eventIds_not_strings");
    }

    [Fact]
    public void TryLoadRandomEventsCatalog_ShouldFail_WhenEventNotObject()
    {
        var loader = new FakeResourceLoader(SanguoRandomEventsCatalogLoader.RandomEventsResPath, "{\"schemaVersion\":1,\"version\":1,\"eventPools\":[{\"poolId\":\"default\",\"eventIds\":[]},{\"poolId\":\"global\",\"eventIds\":[]}],\"events\":[1]}");

        var ok = SanguoRandomEventsCatalogLoader.TryLoadRandomEventsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_random_events_catalog:event_not_object");
    }

    [Fact]
    public void TryLoadRandomEventsCatalog_ShouldFail_WhenEventsMissing()
    {
        var loader = new FakeResourceLoader(SanguoRandomEventsCatalogLoader.RandomEventsResPath, "{\"schemaVersion\":1,\"version\":1,\"eventPools\":[{\"poolId\":\"default\",\"eventIds\":[]},{\"poolId\":\"global\",\"eventIds\":[]}]}");

        var ok = SanguoRandomEventsCatalogLoader.TryLoadRandomEventsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_random_events_catalog:events_missing");
    }

    [Fact]
    public void TryLoadRandomEventsCatalog_ShouldFail_WhenEventsNotArray()
    {
        var loader = new FakeResourceLoader(SanguoRandomEventsCatalogLoader.RandomEventsResPath, "{\"schemaVersion\":1,\"version\":1,\"eventPools\":[{\"poolId\":\"default\",\"eventIds\":[]},{\"poolId\":\"global\",\"eventIds\":[]}],\"events\":{}}");

        var ok = SanguoRandomEventsCatalogLoader.TryLoadRandomEventsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_random_events_catalog:events_not_array");
    }

    [Fact]
    public void TryLoadRandomEventsCatalog_ShouldFail_WhenUniqueOnceMissing()
    {
        var json = "{\"schemaVersion\":1,\"version\":1,\"eventPools\":[{\"poolId\":\"default\",\"eventIds\":[\"a\"]},{\"poolId\":\"global\",\"eventIds\":[\"a\"]}],\"events\":[{\"eventId\":\"a\",\"nameKey\":\"n\",\"descriptionKey\":\"d\",\"cooldownRounds\":0,\"effectKind\":\"moneyDelta\",\"moneyDelta\":1}]}";
        var loader = new FakeResourceLoader(SanguoRandomEventsCatalogLoader.RandomEventsResPath, json);

        var ok = SanguoRandomEventsCatalogLoader.TryLoadRandomEventsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_random_events_catalog:event_missing_uniqueOnce");
    }

    [Fact]
    public void TryLoadRandomEventsCatalog_ShouldFail_WhenEffectKindNotAllowed()
    {
        var json = "{\"schemaVersion\":1,\"version\":1,\"eventPools\":[{\"poolId\":\"default\",\"eventIds\":[\"a\"]},{\"poolId\":\"global\",\"eventIds\":[\"a\"]}],\"events\":[{\"eventId\":\"a\",\"nameKey\":\"n\",\"descriptionKey\":\"d\",\"uniqueOnce\":false,\"cooldownRounds\":0,\"effectKind\":\"teleport\",\"moneyDelta\":1}]}";
        var loader = new FakeResourceLoader(SanguoRandomEventsCatalogLoader.RandomEventsResPath, json);

        var ok = SanguoRandomEventsCatalogLoader.TryLoadRandomEventsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_random_events_catalog:event_invalid_effectKind");
    }

    [Fact]
    public void TryLoadRandomEventsCatalog_ShouldFail_WhenMoneyDeltaMissingForMoneyDeltaKind()
    {
        var json = "{\"schemaVersion\":1,\"version\":1,\"eventPools\":[{\"poolId\":\"default\",\"eventIds\":[\"a\"]},{\"poolId\":\"global\",\"eventIds\":[\"a\"]}],\"events\":[{\"eventId\":\"a\",\"nameKey\":\"n\",\"descriptionKey\":\"d\",\"uniqueOnce\":false,\"cooldownRounds\":0,\"effectKind\":\"moneyDelta\"}]}";
        var loader = new FakeResourceLoader(SanguoRandomEventsCatalogLoader.RandomEventsResPath, json);

        var ok = SanguoRandomEventsCatalogLoader.TryLoadRandomEventsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_random_events_catalog:event_missing_moneyDelta");
    }

    [Fact]
    public void TryLoadRandomEventsCatalog_ShouldFail_WhenStepDeltaOutOfRange()
    {
        var json = "{\"schemaVersion\":1,\"version\":1,\"eventPools\":[{\"poolId\":\"default\",\"eventIds\":[\"a\"]},{\"poolId\":\"global\",\"eventIds\":[\"a\"]}],\"events\":[{\"eventId\":\"a\",\"nameKey\":\"n\",\"descriptionKey\":\"d\",\"uniqueOnce\":false,\"cooldownRounds\":0,\"effectKind\":\"economyStepDelta\",\"stepDelta\":7}]}";
        var loader = new FakeResourceLoader(SanguoRandomEventsCatalogLoader.RandomEventsResPath, json);

        var ok = SanguoRandomEventsCatalogLoader.TryLoadRandomEventsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_random_events_catalog:event_invalid_stepDelta");
    }

    [Fact]
    public void TryLoadRandomEventsCatalog_ShouldFail_WhenCooldownInvalid()
    {
        var json = "{\"schemaVersion\":1,\"version\":1,\"eventPools\":[{\"poolId\":\"default\",\"eventIds\":[\"a\"]},{\"poolId\":\"global\",\"eventIds\":[\"a\"]}],\"events\":[{\"eventId\":\"a\",\"nameKey\":\"n\",\"descriptionKey\":\"d\",\"uniqueOnce\":false,\"cooldownRounds\":-1,\"effectKind\":\"moneyDelta\",\"moneyDelta\":1}]}";
        var loader = new FakeResourceLoader(SanguoRandomEventsCatalogLoader.RandomEventsResPath, json);

        var ok = SanguoRandomEventsCatalogLoader.TryLoadRandomEventsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_random_events_catalog:event_invalid_cooldownRounds");
    }

    [Fact]
    public void TryLoadRandomEventsCatalog_ShouldDeDuplicatePoolsAndEvents_ById()
    {
        var json = "{\"schemaVersion\":1,\"version\":1,\"eventPools\":[{\"poolId\":\"default\",\"eventIds\":[\"a\",\"a\"]},{\"poolId\":\"default\",\"eventIds\":[\"b\"]},{\"poolId\":\"global\",\"eventIds\":[\"a\",\"b\"]}],\"events\":[{\"eventId\":\"a\",\"nameKey\":\"n\",\"descriptionKey\":\"d\",\"uniqueOnce\":false,\"cooldownRounds\":0,\"effectKind\":\"moneyDelta\",\"moneyDelta\":1},{\"eventId\":\"a\",\"nameKey\":\"n2\",\"descriptionKey\":\"d2\",\"uniqueOnce\":false,\"cooldownRounds\":0,\"effectKind\":\"moneyDelta\",\"moneyDelta\":2},{\"eventId\":\"b\",\"nameKey\":\"n3\",\"descriptionKey\":\"d3\",\"uniqueOnce\":false,\"cooldownRounds\":0,\"effectKind\":\"economyStepDelta\",\"stepDelta\":1}]}";
        var loader = new FakeResourceLoader(SanguoRandomEventsCatalogLoader.RandomEventsResPath, json);

        var ok = SanguoRandomEventsCatalogLoader.TryLoadRandomEventsCatalog(loader, out var catalog, out var error);

        ok.Should().BeTrue();
        error.Should().BeEmpty();
        catalog.EventPools.Should().HaveCount(2);
        catalog.Events.Should().HaveCount(2);
    }

    private const string ValidJson = @"{
  ""schemaVersion"": 1,
  ""version"": 1,
  ""eventPools"": [
    { ""poolId"": ""default"", ""eventIds"": [ ""event_money_small"", ""event_economy_boost"" ] },
    { ""poolId"": ""global"", ""eventIds"": [ ""event_money_small"" ] }
  ],
  ""events"": [
    {
      ""eventId"": ""event_money_small"",
      ""nameKey"": ""event.event_money_small.name"",
      ""descriptionKey"": ""event.event_money_small.desc"",
      ""uniqueOnce"": false,
      ""cooldownRounds"": 0,
      ""effectKind"": ""moneyDelta"",
      ""moneyDelta"": 200
    },
    {
      ""eventId"": ""event_economy_boost"",
      ""nameKey"": ""event.event_economy_boost.name"",
      ""descriptionKey"": ""event.event_economy_boost.desc"",
      ""uniqueOnce"": false,
      ""cooldownRounds"": 2,
      ""effectKind"": ""economyStepDelta"",
      ""stepDelta"": 1
    }
  ]
}";

    private const string StartCombatJson = @"{
  ""schemaVersion"": 1,
  ""version"": 1,
  ""eventPools"": [
    { ""poolId"": ""default"", ""eventIds"": [ ""event_combat_small"" ] },
    { ""poolId"": ""global"", ""eventIds"": [ ""event_money_small"" ] }
  ],
  ""events"": [
    {
      ""eventId"": ""event_combat_small"",
      ""nameKey"": ""event.event_combat_small.name"",
      ""descriptionKey"": ""event.event_combat_small.desc"",
      ""uniqueOnce"": false,
      ""cooldownRounds"": 0,
      ""effectKind"": ""startCombat"",
      ""encounterId"": ""enc_event_combat_small"",
      ""encounterTarget"": 10
    },
    {
      ""eventId"": ""event_money_small"",
      ""nameKey"": ""event.event_money_small.name"",
      ""descriptionKey"": ""event.event_money_small.desc"",
      ""uniqueOnce"": false,
      ""cooldownRounds"": 0,
      ""effectKind"": ""moneyDelta"",
      ""moneyDelta"": 200
    }
  ]
}";

    private sealed class FakeResourceLoader : IResourceLoader
    {
        private readonly string _path;
        private readonly string? _content;

        public FakeResourceLoader(string path, string? content)
        {
            _path = path;
            _content = content;
        }

        public string? LoadText(string path) => string.Equals(path, _path, StringComparison.Ordinal) ? _content : null;

        public byte[]? LoadBytes(string path) => null;
    }
}
