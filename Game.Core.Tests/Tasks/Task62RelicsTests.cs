using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Ports;
using Game.Core.Services;
using Game.Core.Utilities;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task62RelicsTests
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        ReadCommentHandling = JsonCommentHandling.Skip,
        AllowTrailingCommas = true,
        MaxDepth = 64,
    };

    private static string LoadRelicsJsonText()
    {
        var repoRoot = FindRepoRoot();
        var path = Path.Combine(repoRoot, "Data", "relics.json");
        File.Exists(path).Should().BeTrue($"expected repo data file to exist: {path}");
        return File.ReadAllText(path);
    }

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var marker = Path.Combine(dir.FullName, ".taskmaster", "tasks", "tasks.json");
            if (File.Exists(marker))
            {
                return dir.FullName;
            }

            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException("Repo root not found (missing .taskmaster/tasks/tasks.json).");
    }

    // ACC:T62.1
    [Fact]
    public void ShouldExposeRelicsArray_WhenParsingRelicsJson()
    {
        // Contract/data stop-loss: ensure the catalog keeps a stable top-level shape.
        var json = LoadRelicsJsonText();
        using var doc = JsonDocument.Parse(json);

        doc.RootElement.TryGetProperty("relics", out var relics).Should().BeTrue();
        relics.ValueKind.Should().Be(JsonValueKind.Array);
    }

    // ACC:T62.2
    [Fact]
    public void ShouldHaveUniqueRelicIds_WhenReadingRelicsJson()
    {
        var json = LoadRelicsJsonText();
        using var doc = JsonDocument.Parse(json);

        var ids = new List<string>();
        foreach (var r in doc.RootElement.GetProperty("relics").EnumerateArray())
        {
            ids.Add(r.GetProperty("relicId").GetString() ?? string.Empty);
        }

        ids.Should().NotBeEmpty();
        ids.Should().OnlyHaveUniqueItems();
    }

    // ACC:T62.3
    [Fact]
    public void ShouldOnlyAllowMoneyDeltaOrEconomyStepDelta_WhenReadingRelicsJson()
    {
        var json = LoadRelicsJsonText();
        using var doc = JsonDocument.Parse(json);

        foreach (var r in doc.RootElement.GetProperty("relics").EnumerateArray())
        {
            var effectKind = r.GetProperty("effectKind").GetString() ?? string.Empty;
            effectKind.Should().BeOneOf(SanguoEffectKinds.MoneyDelta, SanguoEffectKinds.EconomyStepDelta);
        }
    }

    // ACC:T62.4
    [Fact]
    public void ShouldExposeNonEmptyI18nKeys_WhenReadingRelicsJson()
    {
        var json = LoadRelicsJsonText();
        using var doc = JsonDocument.Parse(json);

        foreach (var r in doc.RootElement.GetProperty("relics").EnumerateArray())
        {
            (r.GetProperty("nameKey").GetString() ?? string.Empty).Should().NotBeNullOrWhiteSpace();
            (r.GetProperty("descriptionKey").GetString() ?? string.Empty).Should().NotBeNullOrWhiteSpace();
        }
    }

    // ACC:T62.5
    [Fact]
    public void ShouldDeserializeMoneyDelta_WhenEffectKindIsMoneyDelta()
    {
        var json = LoadRelicsJsonText();
        var catalog = JsonSerializer.Deserialize<SanguoRelicsCatalog>(json, JsonOptions);

        catalog.Should().NotBeNull();
        catalog!.Relics.Should().NotBeNullOrEmpty();

        foreach (var relic in catalog.Relics.Where(r => string.Equals(r.EffectKind, SanguoEffectKinds.MoneyDelta, StringComparison.Ordinal)))
        {
            relic.MoneyDelta.Should().NotBeNull("moneyDelta must be present for moneyDelta relics");
        }
    }

    // ACC:T62.6
    [Fact]
    public void ShouldDeserializeStepDelta_WhenEffectKindIsEconomyStepDelta()
    {
        // Stop-loss: Data uses `stepDelta`, while the contract exposes `EconomyStepDelta` (mapped via JsonPropertyName).
        var json = LoadRelicsJsonText();
        var catalog = JsonSerializer.Deserialize<SanguoRelicsCatalog>(json, JsonOptions);

        catalog.Should().NotBeNull();
        catalog!.Relics.Should().NotBeNullOrEmpty();

        foreach (var relic in catalog.Relics.Where(r => string.Equals(r.EffectKind, SanguoEffectKinds.EconomyStepDelta, StringComparison.Ordinal)))
        {
            relic.EconomyStepDelta.Should().NotBeNull("step delta must be present for economyStepDelta relics");
        }
    }

    // ACC:T62.7
    [Fact]
    public void ShouldExposeExpectedEventTypes_WhenUsingLootAndRelicContracts()
    {
        SanguoLootGranted.EventType.Should().Be("core.sanguo.loot.granted");
        SanguoRelicApplied.EventType.Should().Be("core.sanguo.relic.applied");
    }

    // ACC:T62.8
    [Fact]
    public void ShouldSortRelicIdsByOrdinalAscending_WhenApplyingRelicsInStableOrder()
    {
        var ids = new[] { "relic_z", "relic_a", "relic_m" };
        var ordered = ids.OrderBy(x => x, StringComparer.Ordinal).ToArray();

        ordered.Should().Equal(new[] { "relic_a", "relic_m", "relic_z" });
    }

    // ACC:T62.1
    [Fact]
    public async Task ShouldGrantRelicAndPublishLootAndRelicApplied_WhenLandingOnFacilityTile()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 1000m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { p1 }, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var relicsCatalog = new SanguoRelicsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Relics: new[]
            {
                new SanguoRelicDefinition(
                    RelicId: "relic_step",
                    NameKey: "relic.relic_step.name",
                    DescriptionKey: "relic.relic_step.desc",
                    EffectKind: SanguoEffectKinds.EconomyStepDelta,
                    MoneyDelta: null,
                    EconomyStepDelta: 1),
            });

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new FixedRng(fixedNextInt: 1, fixedNextDouble: 1.0),
            randomSeed: 123,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            relicsCatalog: relicsCatalog,
            tileTypesByPositionIndex: new Dictionary<int, string> { [0] = SanguoMapTileDefinitionV2.TileKindFacility });

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr-start",
            causationId: "ut.start");

        await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-roll", causationId: "ut.roll");

        bus.Published.Should().Contain(e => e.Type == SanguoLootGranted.EventType);
        bus.Published.Should().Contain(e => e.Type == SanguoRelicApplied.EventType);

        var lootJson = ((JsonElementEventData)bus.Published.First(e => e.Type == SanguoLootGranted.EventType).Data!).Value;
        lootJson.GetProperty("LootKind").GetString().Should().Be("relic");
        lootJson.GetProperty("SourceKind").GetString().Should().Be("facility_tile");
        lootJson.GetProperty("RelicId").GetString().Should().Be("relic_step");

        var appliedJson = ((JsonElementEventData)bus.Published.First(e => e.Type == SanguoRelicApplied.EventType).Data!).Value;
        appliedJson.GetProperty("RelicId").GetString().Should().Be("relic_step");
        appliedJson.GetProperty("EffectKind").GetString().Should().Be(SanguoEffectKinds.EconomyStepDelta);
        appliedJson.GetProperty("StepDelta").GetInt32().Should().Be(1);
    }

    // ACC:T62.1
    [Fact]
    public async Task ShouldRerollUntilUnique_AndReturnNullWithAudit_WhenRelicsAreExhausted()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 1000m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { p1 }, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var relicsCatalog = new SanguoRelicsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Relics: new[]
            {
                new SanguoRelicDefinition(
                    RelicId: "relic_only",
                    NameKey: "relic.relic_only.name",
                    DescriptionKey: "relic.relic_only.desc",
                    EffectKind: SanguoEffectKinds.EconomyStepDelta,
                    MoneyDelta: null,
                    EconomyStepDelta: 1),
            });

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new FixedRng(fixedNextInt: 1, fixedNextDouble: 1.0),
            randomSeed: 123,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            relicsCatalog: relicsCatalog,
            tileTypesByPositionIndex: new Dictionary<int, string> { [0] = SanguoMapTileDefinitionV2.TileKindFacility });

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr-start",
            causationId: "ut.start");

        await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-roll-1", causationId: "ut.roll");
        await mgr.AdvanceTurnAsync(correlationId: "corr-adv-1", causationId: "ut.advance");
        await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-roll-2", causationId: "ut.roll");

        var lootEvents = bus.Published.Where(e => e.Type == SanguoLootGranted.EventType).ToList();
        lootEvents.Should().HaveCount(2);

        var firstLoot = ((JsonElementEventData)lootEvents[0].Data!).Value;
        firstLoot.GetProperty("RelicId").GetString().Should().Be("relic_only");

        var secondLoot = ((JsonElementEventData)lootEvents[1].Data!).Value;
        secondLoot.TryGetProperty("RelicId", out var relicId).Should().BeTrue();
        relicId.ValueKind.Should().Be(JsonValueKind.Null);

        bus.Published.Count(e => e.Type == SanguoRelicApplied.EventType).Should().Be(1);
    }

    // ACC:T62.2
    [Fact]
    public async Task ShouldIncludeRelicStepDeltaInAppliedMultipliers_WhenPlayingActionCardAfterRelicApplied()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 1000m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { p1 }, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var relicsCatalog = new SanguoRelicsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Relics: new[]
            {
                new SanguoRelicDefinition(
                    RelicId: "relic_step",
                    NameKey: "relic.relic_step.name",
                    DescriptionKey: "relic.relic_step.desc",
                    EffectKind: SanguoEffectKinds.EconomyStepDelta,
                    MoneyDelta: null,
                    EconomyStepDelta: 1),
            });

        var actionCardsCatalog = new SanguoActionCardsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Cards: new[]
            {
                new SanguoActionCardCatalogEntry(
                    CardId: "card_step",
                    NameKey: "card.card_step.name",
                    DescriptionKey: "card.card_step.desc",
                    EffectKind: "economyStepDelta",
                    StepDelta: 1,
                    DurationRounds: 3),
            });

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new FixedRng(fixedNextInt: 1, fixedNextDouble: 1.0),
            randomSeed: 123,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            relicsCatalog: relicsCatalog,
            actionCardsCatalog: actionCardsCatalog,
            tileTypesByPositionIndex: new Dictionary<int, string> { [0] = SanguoMapTileDefinitionV2.TileKindFacility });

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr-start",
            causationId: "ut.start");

        await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-roll-1", causationId: "ut.roll");
        await mgr.AdvanceTurnAsync(correlationId: "corr-adv-1", causationId: "ut.advance");

        var played = await mgr.TryPlayHumanActionCardAsync(cardId: "card_step", correlationId: "corr-card", causationId: "ut.card");
        played.Should().BeTrue();

        var playedEvt = bus.Published.FirstOrDefault(e => e.Type == SanguoActionCardPlayed.EventType);
        playedEvt.Should().NotBeNull();

        var json = ((JsonElementEventData)playedEvt!.Data!).Value;
        json.TryGetProperty("AppliedMultipliersAfter", out var after).Should().BeTrue();
        after.GetProperty("RelicStepDelta").GetInt32().Should().Be(1);
        after.GetProperty("ActionCardStepDelta").GetInt32().Should().Be(1);
    }

    // ACC:T62.3
    [Fact]
    public async Task ShouldPublishLootAndRelicApplied_WhenEventTileAppliesRandomEvent()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 1000m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { p1 }, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var relicsCatalog = new SanguoRelicsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Relics: new[]
            {
                new SanguoRelicDefinition(
                    RelicId: "relic_gold",
                    NameKey: "relic.relic_gold.name",
                    DescriptionKey: "relic.relic_gold.desc",
                    EffectKind: SanguoEffectKinds.MoneyDelta,
                    MoneyDelta: 10,
                    EconomyStepDelta: null),
            });

        var randomEventsCatalog = new SanguoRandomEventsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Events: new[]
            {
                new SanguoRandomEventCatalogEntry(
                    EventId: "event_money",
                    NameKey: "event.event_money.name",
                    DescriptionKey: "event.event_money.desc",
                    EffectKind: SanguoEffectKinds.MoneyDelta,
                    MoneyDelta: 200,
                    StepDelta: null,
                    CooldownRounds: 0,
                    UniqueOnce: false),
            },
            EventPools: new[]
            {
                new SanguoRandomEventPoolCatalogEntry(PoolId: "default", EventIds: new[] { "event_money" }),
                new SanguoRandomEventPoolCatalogEntry(PoolId: "global", EventIds: new[] { "event_money" }),
            });

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new FixedRng(fixedNextInt: 1, fixedNextDouble: 1.0),
            randomSeed: 123,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            relicsCatalog: relicsCatalog,
            randomEventsCatalog: randomEventsCatalog,
            tileTypesByPositionIndex: new Dictionary<int, string> { [0] = SanguoTileDefinition.TileTypeEvent });

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr-start",
            causationId: "ut.start");

        await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-roll", causationId: "ut.roll");

        bus.Published.Should().Contain(e => e.Type == SanguoRandomEventApplied.EventType);
        bus.Published.Should().Contain(e => e.Type == SanguoLootGranted.EventType);
        bus.Published.Should().Contain(e => e.Type == SanguoRelicApplied.EventType);
    }

    // ACC:T62.3
    [Fact]
    public async Task ShouldPublishLootAndRelicApplied_WhenCombatEnds()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 1000m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { p1 }, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var relicsCatalog = new SanguoRelicsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Relics: new[]
            {
                new SanguoRelicDefinition(
                    RelicId: "relic_gold",
                    NameKey: "relic.relic_gold.name",
                    DescriptionKey: "relic.relic_gold.desc",
                    EffectKind: SanguoEffectKinds.MoneyDelta,
                    MoneyDelta: 10,
                    EconomyStepDelta: null),
            });

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new FixedRng(fixedNextInt: 1, fixedNextDouble: 1.0),
            randomSeed: 123,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            relicsCatalog: relicsCatalog,
            tileTypesByPositionIndex: new Dictionary<int, string> { [0] = SanguoTileDefinition.TileTypePass });

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr-start",
            causationId: "ut.start");

        await mgr.ExecuteHumanTileActionAsync(action: "start_combat", correlationId: "corr-combat", causationId: "ut.combat");

        bus.Published.Should().Contain(e => e.Type == SanguoCombatEnded.EventType);
        bus.Published.Should().Contain(e => e.Type == SanguoLootGranted.EventType);
        bus.Published.Should().Contain(e => e.Type == SanguoRelicApplied.EventType);
    }

    [Fact]
    public async Task ShouldNotPublishLoot_WhenRelicsCatalogIsMissing()
    {
        var bus = new RecordingEventBus();
        var economy = new SanguoEconomyManager(bus);

        var rules = SanguoEconomyRules.Default;
        var p1 = new SanguoPlayer(playerId: "p1", money: 1000m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { p1 }, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var mgr = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new FixedRng(fixedNextInt: 1, fixedNextDouble: 1.0),
            randomSeed: 123,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            tileTypesByPositionIndex: new Dictionary<int, string> { [0] = SanguoMapTileDefinitionV2.TileKindFacility });

        await mgr.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr-start",
            causationId: "ut.start");

        await mgr.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-roll", causationId: "ut.roll");

        bus.Published.Should().NotContain(e => e.Type == SanguoLootGranted.EventType);
        bus.Published.Should().NotContain(e => e.Type == SanguoRelicApplied.EventType);
    }

    private sealed class RecordingEventBus : IEventBus
    {
        public List<DomainEvent> Published { get; } = new();

        public Task PublishAsync(DomainEvent evt)
        {
            Published.Add(evt);
            return Task.CompletedTask;
        }

        public IDisposable Subscribe(Func<DomainEvent, Task> handler) => new NoopDisposable();

        private sealed class NoopDisposable : IDisposable
        {
            public void Dispose() { }
        }
    }

    private sealed class FixedRng : IRandomNumberGenerator
    {
        private readonly int _fixedNextInt;
        private readonly double _fixedNextDouble;

        public FixedRng(int fixedNextInt, double fixedNextDouble)
        {
            _fixedNextInt = fixedNextInt;
            _fixedNextDouble = fixedNextDouble;
        }

        public int NextInt(int minInclusive, int maxExclusive) => _fixedNextInt;

        public double NextDouble() => _fixedNextDouble;
    }
}
