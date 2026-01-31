using System.Collections.Generic;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Game.Core.Ports;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Services;

public sealed class SanguoCatalogPackPathTests
{
    private const string PortraitResPath = "res://Assets/portraits/portrait_placeholder.svg";

    [Fact]
    public void TryLoadMapsCatalog_ShouldUsePackPath()
    {
        var mapsPath = "res://Data/packs/test_pack/maps/_index.json";
        var loader = new FakeResourceLoader(new Dictionary<string, string?>
        {
            [mapsPath] = BuildMapsJson()
        });
        var pack = BuildPack(mapsIndexPath: mapsPath);

        var ok = SanguoMapsCatalogLoader.TryLoadMapsCatalog(loader, pack, out _, out var error);

        ok.Should().BeTrue(error);
        loader.LoadTextCalls.Should().ContainSingle().Which.Should().Be(mapsPath);
    }

    [Fact]
    public void TryLoadCharactersCatalog_ShouldUsePackPath()
    {
        var charactersPath = "res://Data/packs/test_pack/characters.json";
        var loader = new FakeResourceLoader(new Dictionary<string, string?>
        {
            [charactersPath] = BuildCharactersJson(count: 8)
        });
        var pack = BuildPack(charactersPath: charactersPath);

        var ok = SanguoCharactersCatalogLoader.TryLoadCharactersCatalog(loader, pack, out _, out var error);

        ok.Should().BeTrue(error);
        loader.LoadTextCalls.Should().ContainSingle().Which.Should().Be(charactersPath);
        loader.LoadBytesCalls.Should().Contain(PortraitResPath);
    }

    [Fact]
    public void TryLoadRandomEventsCatalog_ShouldUsePackPath()
    {
        var eventsPath = "res://Data/packs/test_pack/random_events.json";
        var loader = new FakeResourceLoader(new Dictionary<string, string?>
        {
            [eventsPath] = BuildRandomEventsJson()
        });
        var pack = BuildPack(randomEventsPath: eventsPath);

        var ok = SanguoRandomEventsCatalogLoader.TryLoadRandomEventsCatalog(loader, pack, out _, out var error);

        ok.Should().BeTrue(error);
        loader.LoadTextCalls.Should().ContainSingle().Which.Should().Be(eventsPath);
    }

    [Fact]
    public void TryLoadActionCardsCatalog_ShouldUsePackPath()
    {
        var cardsPath = "res://Data/packs/test_pack/action_cards.json";
        var loader = new FakeResourceLoader(new Dictionary<string, string?>
        {
            [cardsPath] = BuildActionCardsJson()
        });
        var pack = BuildPack(actionCardsPath: cardsPath);

        var ok = SanguoActionCardsCatalogLoader.TryLoadActionCardsCatalog(loader, pack, out _, out var error);

        ok.Should().BeTrue(error);
        loader.LoadTextCalls.Should().ContainSingle().Which.Should().Be(cardsPath);
    }

    [Fact]
    public void TryLoadBuildingsCatalog_ShouldUsePackPath()
    {
        var buildingsPath = "res://Data/packs/test_pack/buildings.json";
        var loader = new FakeResourceLoader(new Dictionary<string, string?>
        {
            [buildingsPath] = BuildBuildingsJson()
        });
        var pack = BuildPack(buildingsPath: buildingsPath);

        var ok = SanguoBuildingsCatalogLoader.TryLoadBuildingsCatalog(loader, pack, out _, out var error);

        ok.Should().BeTrue(error);
        loader.LoadTextCalls.Should().ContainSingle().Which.Should().Be(buildingsPath);
    }

    [Fact]
    public void TryLoadRelicsCatalog_ShouldUsePackPath()
    {
        var relicsPath = "res://Data/packs/test_pack/relics.json";
        var loader = new FakeResourceLoader(new Dictionary<string, string?>
        {
            [relicsPath] = BuildRelicsJson()
        });
        var pack = BuildPack(relicsPath: relicsPath);

        var ok = SanguoRelicsCatalogLoader.TryLoadRelicsCatalog(loader, pack, out _, out var error);

        ok.Should().BeTrue(error);
        loader.LoadTextCalls.Should().ContainSingle().Which.Should().Be(relicsPath);
    }

    [Fact]
    public void TryLoadRegionsCatalog_ShouldUsePackPath()
    {
        var regionsPath = "res://Data/packs/test_pack/regions.json";
        var loader = new FakeResourceLoader(new Dictionary<string, string?>
        {
            [regionsPath] = BuildRegionsJson()
        });
        var pack = BuildPack(regionsPath: regionsPath);

        var ok = SanguoRegionsCatalogLoader.TryLoadRegionsCatalog(loader, pack, out _, out var error);

        ok.Should().BeTrue(error);
        loader.LoadTextCalls.Should().ContainSingle().Which.Should().Be(regionsPath);
    }

    private static SanguoContentPackPaths BuildPack(
        string mapsIndexPath = "res://Data/packs/test_pack/maps/_index.json",
        string charactersPath = "res://Data/packs/test_pack/characters.json",
        string randomEventsPath = "res://Data/packs/test_pack/random_events.json",
        string actionCardsPath = "res://Data/packs/test_pack/action_cards.json",
        string buildingsPath = "res://Data/packs/test_pack/buildings.json",
        string relicsPath = "res://Data/packs/test_pack/relics.json",
        string regionsPath = "res://Data/packs/test_pack/regions.json")
        => new(
            PackId: "test_pack",
            PackVersion: 1,
            MapsIndexPath: mapsIndexPath,
            CharactersPath: charactersPath,
            RandomEventsPath: randomEventsPath,
            ActionCardsPath: actionCardsPath,
            BuildingsPath: buildingsPath,
            RelicsPath: relicsPath,
            RegionsPath: regionsPath,
            FacilitiesPath: "res://Data/packs/test_pack/facilities.json",
            I18nZhPath: "res://Data/packs/test_pack/i18n/zh_cn.json",
            I18nEnPath: "res://Data/packs/test_pack/i18n/en_us.json");

    private static string BuildMapsJson()
    {
        var payload = new Dictionary<string, object?>
        {
            ["schemaVersion"] = 1,
            ["version"] = 1,
            ["maps"] = new[]
            {
                new Dictionary<string, object?>
                {
                    ["mapId"] = "map001",
                    ["nameKey"] = "map.map001.name",
                    ["descriptionKey"] = "map.map001.desc",
                    ["path"] = "res://Data/maps/map001.json",
                    ["recommendedPlayersMin"] = 2,
                    ["recommendedPlayersMax"] = 4,
                    ["contentVersion"] = 1,
                    ["previewImagePath"] = "res://Assets/maps/map001_preview.svg"
                }
            }
        };
        return JsonSerializer.Serialize(payload);
    }

    private static string BuildCharactersJson(int count)
    {
        var characters = new List<Dictionary<string, object?>>();
        for (var index = 0; index < count; index++)
        {
            var characterId = $"c{index + 1}";
            characters.Add(new Dictionary<string, object?>
            {
                ["characterId"] = characterId,
                ["nameKey"] = $"character.{characterId}.name",
                ["descriptionKey"] = $"character.{characterId}.desc",
                ["combatRating"] = 10,
                ["portraitPath"] = PortraitResPath,
                ["startingMoneyStepDelta"] = 0,
                ["economyStepDeltas"] = new Dictionary<string, int>
                {
                    ["buyPrice"] = 0,
                    ["toll"] = 0,
                    ["incomeSettlement"] = 0,
                    ["buildCost"] = 0,
                    ["upgradeCost"] = 0
                }
            });
        }

        var payload = new Dictionary<string, object?>
        {
            ["schemaVersion"] = 1,
            ["version"] = 1,
            ["characters"] = characters
        };
        return JsonSerializer.Serialize(payload);
    }

    private static string BuildRandomEventsJson()
    {
        var payload = new Dictionary<string, object?>
        {
            ["schemaVersion"] = 1,
            ["version"] = 1,
            ["eventPools"] = new[]
            {
                new Dictionary<string, object?>
                {
                    ["poolId"] = "default",
                    ["eventIds"] = new[] { "event_1" }
                },
                new Dictionary<string, object?>
                {
                    ["poolId"] = "global",
                    ["eventIds"] = new[] { "event_1" }
                }
            },
            ["events"] = new[]
            {
                new Dictionary<string, object?>
                {
                    ["eventId"] = "event_1",
                    ["nameKey"] = "event.event_1.name",
                    ["descriptionKey"] = "event.event_1.desc",
                    ["uniqueOnce"] = false,
                    ["cooldownRounds"] = 0,
                    ["effectKind"] = "economyStepDelta",
                    ["stepDelta"] = 1
                }
            }
        };
        return JsonSerializer.Serialize(payload);
    }

    private static string BuildActionCardsJson()
    {
        var payload = new Dictionary<string, object?>
        {
            ["schemaVersion"] = 1,
            ["version"] = 1,
            ["cards"] = new[]
            {
                new Dictionary<string, object?>
                {
                    ["cardId"] = "card_1",
                    ["nameKey"] = "card.card_1.name",
                    ["descriptionKey"] = "card.card_1.desc",
                    ["effectKind"] = "economyStepDelta",
                    ["stepDelta"] = 1,
                    ["durationRounds"] = 1
                }
            }
        };
        return JsonSerializer.Serialize(payload);
    }

    private static string BuildBuildingsJson()
    {
        var payload = new Dictionary<string, object?>
        {
            ["schemaVersion"] = 1,
            ["version"] = 1,
            ["buildings"] = new[]
            {
                new Dictionary<string, object?>
                {
                    ["buildingId"] = "building_1",
                    ["nameKey"] = "building.building_1.name",
                    ["descriptionKey"] = "building.building_1.desc",
                    ["maxLevel"] = 1,
                    ["buildCostBase"] = 100,
                    ["upgradeCostBase"] = 50,
                    ["settlementIncomeBase"] = 10,
                    ["economyStepDeltas"] = new Dictionary<string, int>
                    {
                        ["buyPrice"] = 0,
                        ["toll"] = 1,
                        ["incomeSettlement"] = 0,
                        ["buildCost"] = 0,
                        ["upgradeCost"] = 0
                    }
                }
            }
        };
        return JsonSerializer.Serialize(payload);
    }

    private static string BuildRelicsJson()
    {
        var payload = new Dictionary<string, object?>
        {
            ["schemaVersion"] = 1,
            ["version"] = 1,
            ["relics"] = new[]
            {
                new Dictionary<string, object?>
                {
                    ["relicId"] = "relic_1",
                    ["nameKey"] = "relic.relic_1.name",
                    ["descriptionKey"] = "relic.relic_1.desc",
                    ["effectKind"] = "moneyDelta",
                    ["moneyDelta"] = 100
                }
            }
        };
        return JsonSerializer.Serialize(payload);
    }

    private static string BuildRegionsJson()
    {
        var payload = new Dictionary<string, object?>
        {
            ["schemaVersion"] = 1,
            ["version"] = 1,
            ["regions"] = new[]
            {
                new Dictionary<string, object?>
                {
                    ["regionId"] = "region_1",
                    ["nameKey"] = "region.region_1.name",
                    ["descriptionKey"] = "region.region_1.desc",
                    ["effectKind"] = "economyStepDelta",
                    ["economyStepDeltas"] = new Dictionary<string, int>
                    {
                        ["buyPrice"] = 0,
                        ["toll"] = 0,
                        ["incomeSettlement"] = 0,
                        ["buildCost"] = 0,
                        ["upgradeCost"] = 0
                    }
                }
            }
        };
        return JsonSerializer.Serialize(payload);
    }

    private sealed class FakeResourceLoader : IResourceLoader
    {
        private readonly Dictionary<string, string?> _texts;
        private readonly byte[] _bytes = { 1, 2, 3 };

        public FakeResourceLoader(Dictionary<string, string?> texts)
        {
            _texts = texts;
        }

        public List<string> LoadTextCalls { get; } = new();

        public List<string> LoadBytesCalls { get; } = new();

        public string? LoadText(string path)
        {
            LoadTextCalls.Add(path);
            return _texts.TryGetValue(path, out var content) ? content : null;
        }

        public byte[]? LoadBytes(string path)
        {
            LoadBytesCalls.Add(path);
            return _bytes;
        }
    }
}
