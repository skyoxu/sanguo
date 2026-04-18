using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Ports;
using Game.Core.Services;
using Game.Core.Utilities;
using MoneyValue = Game.Core.Domain.ValueObjects.Money;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task127CampBuildingEffectSetATests
{
    // ACC:T127.1
    [Fact]
    public async Task ShouldEmitDeterministicBuiltOutputs_WhenBuildingSetAIsBuiltSequentially()
    {
        var city = CreateCityAtIndex(positionIndex: 0, baseTollMajorUnits: 10m);
        var player = new SanguoPlayer(playerId: "p1", money: 1000m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        player.TryBuyCity(city, priceMultiplier: 1.0m).Should().BeTrue();

        var boardState = new SanguoBoardState(
            players: new[] { player },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal) { [city.Id] = city });

        var bus = new RecordingEventBus();
        var manager = new SanguoTurnManager(
            bus: bus,
            economy: new SanguoEconomyManager(bus),
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new FixedRng(fixedNextInt: 1, fixedNextDouble: 1.0),
            randomSeed: 12701,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            buildingsCatalog: CreateSetABuildingsCatalog());

        await StartSinglePlayerGameAsync(manager, correlationId: "corr-start-build");

        await manager.ExecuteHumanTileActionAsync(action: "build", correlationId: "corr-build-1", causationId: "ut.build");
        await manager.ExecuteHumanTileActionAsync(action: "build", correlationId: "corr-build-2", causationId: "ut.build");
        await manager.ExecuteHumanTileActionAsync(action: "build", correlationId: "corr-build-3", causationId: "ut.build");

        var builtEvents = bus.Published.Where(evt => evt.Type == SanguoBuildingBuilt.EventType).ToArray();
        builtEvents.Should().HaveCount(3);

        var buildingIds = builtEvents
            .Select(evt => ReadPayload(evt).GetProperty("BuildingId").GetString())
            .ToArray();

        buildingIds.Should().Equal(
            "building_defense_center",
            "building_relic_workshop",
            "building_tavern");

        var tollDeltas = builtEvents
            .Select(evt => ReadPayload(evt).GetProperty("EconomyStepDeltas").GetProperty("Toll").GetInt32())
            .ToArray();

        tollDeltas.Should().Equal(2, 1, 0);
    }

    // ACC:T127.1
    [Fact]
    public async Task ShouldProduceDeterministicRelicOutputEvidence_WhenSetARelicPoolAndSeedAreStable()
    {
        var firstRun = await RunSingleFacilityLootAsync(CreateValidSetARelicsCatalog(), randomSeed: 12711, correlationId: "corr-deterministic-1");
        var secondRun = await RunSingleFacilityLootAsync(CreateValidSetARelicsCatalog(), randomSeed: 12711, correlationId: "corr-deterministic-2");

        firstRun.lootPickedId.Should().Be(secondRun.lootPickedId);
        firstRun.lootPickedIndex.Should().Be(secondRun.lootPickedIndex);
        firstRun.lootRngContextId.Should().Be(secondRun.lootRngContextId);
        firstRun.lootCandidatesHash.Should().Be(secondRun.lootCandidatesHash);

        firstRun.appliedRelicId.Should().Be(secondRun.appliedRelicId);
        firstRun.appliedEffectKind.Should().Be(secondRun.appliedEffectKind);
        firstRun.appliedMoneyDelta.Should().Be(secondRun.appliedMoneyDelta);
        firstRun.appliedStepDelta.Should().Be(secondRun.appliedStepDelta);
    }

    // ACC:T127.1
    [Fact]
    public async Task ShouldEmitFallbackNoOpRelicAppliedAndKeepLootAuditable_WhenRelicEffectDataIsMissingOrInvalid()
    {
        var scenario = CreateFacilityLootScenario(CreateInvalidSetARelicsCatalog(), randomSeed: 12721);

        await StartSinglePlayerGameAsync(scenario.manager, correlationId: "corr-invalid-loot");
        await scenario.manager.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-invalid-roll", causationId: "ut.roll");

        var lootEvents = scenario.bus.Published.Where(evt => evt.Type == SanguoLootGranted.EventType).ToArray();
        lootEvents.Should().ContainSingle();
        var appliedEvents = scenario.bus.Published.Where(evt => evt.Type == SanguoRelicApplied.EventType).ToArray();
        appliedEvents.Should().ContainSingle();

        var lootPayload = ReadPayload(lootEvents[0]);
        lootPayload.GetProperty("LootKind").GetString().Should().Be("relic");
        lootPayload.GetProperty("PickedId").GetString().Should().NotBeNullOrWhiteSpace();
        lootPayload.GetProperty("RelicId").ValueKind.Should().Be(JsonValueKind.Null);
        lootPayload.GetProperty("CandidatesSortedIdsHash").GetString().Should().NotBeNullOrWhiteSpace();

        var appliedPayload = ReadPayload(appliedEvents[0]);
        appliedPayload.GetProperty("RelicId").GetString().Should().NotBeNullOrWhiteSpace();
        appliedPayload.GetProperty("EffectKind").GetString().Should().Be("fallback_noop");
        ReadNullableInt(appliedPayload, "MoneyDelta").Should().Be(0);
        ReadNullableInt(appliedPayload, "StepDelta").Should().Be(0);

        scenario.player.Money.ToDecimal().Should().Be(1000m);
    }

    // ACC:T127.1
    private static async Task StartSinglePlayerGameAsync(SanguoTurnManager manager, string correlationId)
    {
        await manager.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: correlationId,
            causationId: "ut.start");
    }

    private static async Task<(string? lootPickedId, int? lootPickedIndex, string? lootRngContextId, string? lootCandidatesHash, string? appliedRelicId, string? appliedEffectKind, int? appliedMoneyDelta, int? appliedStepDelta)> RunSingleFacilityLootAsync(
        SanguoRelicsCatalog relicsCatalog,
        int randomSeed,
        string correlationId)
    {
        var scenario = CreateFacilityLootScenario(relicsCatalog, randomSeed);

        await StartSinglePlayerGameAsync(scenario.manager, correlationId);
        await scenario.manager.ExecuteHumanRollDiceAndResolveAsync(correlationId: correlationId + "-roll", causationId: "ut.roll");

        var lootEvent = scenario.bus.Published.Single(evt => evt.Type == SanguoLootGranted.EventType);
        var appliedEvent = scenario.bus.Published.Single(evt => evt.Type == SanguoRelicApplied.EventType);

        var lootPayload = ReadPayload(lootEvent);
        var appliedPayload = ReadPayload(appliedEvent);

        return (
            lootPickedId: lootPayload.GetProperty("PickedId").GetString(),
            lootPickedIndex: ReadNullableInt(lootPayload, "PickedIndex"),
            lootRngContextId: lootPayload.GetProperty("RngContextId").GetString(),
            lootCandidatesHash: lootPayload.GetProperty("CandidatesSortedIdsHash").GetString(),
            appliedRelicId: appliedPayload.GetProperty("RelicId").GetString(),
            appliedEffectKind: appliedPayload.GetProperty("EffectKind").GetString(),
            appliedMoneyDelta: ReadNullableInt(appliedPayload, "MoneyDelta"),
            appliedStepDelta: ReadNullableInt(appliedPayload, "StepDelta"));
    }

    private static (SanguoTurnManager manager, RecordingEventBus bus, SanguoPlayer player) CreateFacilityLootScenario(
        SanguoRelicsCatalog relicsCatalog,
        int randomSeed)
    {
        var player = new SanguoPlayer(playerId: "p1", money: 1000m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
        var boardState = new SanguoBoardState(
            players: new[] { player },
            citiesById: new Dictionary<string, City>(StringComparer.Ordinal));

        var bus = new RecordingEventBus();
        var manager = new SanguoTurnManager(
            bus: bus,
            economy: new SanguoEconomyManager(bus),
            boardState: boardState,
            treasury: new SanguoTreasury(),
            rng: new FixedRng(fixedNextInt: 1, fixedNextDouble: 1.0),
            randomSeed: randomSeed,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            relicsCatalog: relicsCatalog,
            tileTypesByPositionIndex: new Dictionary<int, string>
            {
                [0] = SanguoMapTileDefinitionV2.TileKindFacility,
            });

        return (manager, bus, player);
    }

    private static SanguoBuildingsCatalog CreateSetABuildingsCatalog()
    {
        return new SanguoBuildingsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Buildings: new[]
            {
                new SanguoBuildingDefinition(
                    BuildingId: "building_defense_center",
                    NameKey: "building.defense_center.name",
                    DescriptionKey: "building.defense_center.desc",
                    MaxLevel: 1,
                    BuildCostBase: 0,
                    UpgradeCostBase: 0,
                    SettlementIncomeBase: 0,
                    EconomyStepDeltas: new SanguoEconomyStepDeltas(
                        BuyPrice: 0,
                        Toll: 2,
                        IncomeSettlement: 0,
                        BuildCost: 0,
                        UpgradeCost: 0)),
                new SanguoBuildingDefinition(
                    BuildingId: "building_relic_workshop",
                    NameKey: "building.relic_workshop.name",
                    DescriptionKey: "building.relic_workshop.desc",
                    MaxLevel: 1,
                    BuildCostBase: 0,
                    UpgradeCostBase: 0,
                    SettlementIncomeBase: 0,
                    EconomyStepDeltas: new SanguoEconomyStepDeltas(
                        BuyPrice: 0,
                        Toll: 1,
                        IncomeSettlement: 1,
                        BuildCost: 0,
                        UpgradeCost: 0)),
                new SanguoBuildingDefinition(
                    BuildingId: "building_tavern",
                    NameKey: "building.tavern.name",
                    DescriptionKey: "building.tavern.desc",
                    MaxLevel: 1,
                    BuildCostBase: 0,
                    UpgradeCostBase: 0,
                    SettlementIncomeBase: 0,
                    EconomyStepDeltas: new SanguoEconomyStepDeltas(
                        BuyPrice: 0,
                        Toll: 0,
                        IncomeSettlement: 2,
                        BuildCost: 0,
                        UpgradeCost: 0)),
            });
    }

    private static SanguoRelicsCatalog CreateValidSetARelicsCatalog()
    {
        return new SanguoRelicsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Relics: new[]
            {
                new SanguoRelicDefinition(
                    RelicId: "relic_defense_center_guard",
                    NameKey: "relic.defense_center_guard.name",
                    DescriptionKey: "relic.defense_center_guard.desc",
                    EffectKind: SanguoEffectKinds.EconomyStepDelta,
                    MoneyDelta: null,
                    EconomyStepDelta: 1),
                new SanguoRelicDefinition(
                    RelicId: "relic_relic_workshop_cache",
                    NameKey: "relic.relic_workshop_cache.name",
                    DescriptionKey: "relic.relic_workshop_cache.desc",
                    EffectKind: SanguoEffectKinds.MoneyDelta,
                    MoneyDelta: 30,
                    EconomyStepDelta: null),
                new SanguoRelicDefinition(
                    RelicId: "relic_tavern_supply",
                    NameKey: "relic.tavern_supply.name",
                    DescriptionKey: "relic.tavern_supply.desc",
                    EffectKind: SanguoEffectKinds.MoneyDelta,
                    MoneyDelta: 20,
                    EconomyStepDelta: null),
            });
    }

    private static SanguoRelicsCatalog CreateInvalidSetARelicsCatalog()
    {
        return new SanguoRelicsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Relics: new[]
            {
                new SanguoRelicDefinition(
                    RelicId: "relic_defense_center_missing_step",
                    NameKey: "relic.defense_center_missing_step.name",
                    DescriptionKey: "relic.defense_center_missing_step.desc",
                    EffectKind: SanguoEffectKinds.EconomyStepDelta,
                    MoneyDelta: null,
                    EconomyStepDelta: null),
                new SanguoRelicDefinition(
                    RelicId: "relic_relic_workshop_invalid_kind",
                    NameKey: "relic.relic_workshop_invalid_kind.name",
                    DescriptionKey: "relic.relic_workshop_invalid_kind.desc",
                    EffectKind: "invalid_effect_kind",
                    MoneyDelta: null,
                    EconomyStepDelta: null),
                new SanguoRelicDefinition(
                    RelicId: "relic_tavern_missing_money",
                    NameKey: "relic.tavern_missing_money.name",
                    DescriptionKey: "relic.tavern_missing_money.desc",
                    EffectKind: SanguoEffectKinds.MoneyDelta,
                    MoneyDelta: null,
                    EconomyStepDelta: null),
            });
    }

    private static City CreateCityAtIndex(int positionIndex, decimal baseTollMajorUnits)
    {
        return new City(
            id: "c1",
            name: "City1",
            regionId: "r1",
            basePrice: MoneyValue.Zero,
            baseToll: MoneyValue.FromDecimal(baseTollMajorUnits),
            positionIndex: positionIndex);
    }

    private static JsonElement ReadPayload(DomainEvent evt)
    {
        evt.Data.Should().BeOfType<JsonElementEventData>();
        return ((JsonElementEventData)evt.Data!).Value;
    }

    private static int? ReadNullableInt(JsonElement payload, string propertyName)
    {
        var property = payload.GetProperty(propertyName);
        return property.ValueKind == JsonValueKind.Null ? null : property.GetInt32();
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
            public void Dispose()
            {
            }
        }
    }

    private sealed class FixedRng : IRandomNumberGenerator
    {
        private readonly int fixedNextInt;
        private readonly double fixedNextDouble;

        public FixedRng(int fixedNextInt, double fixedNextDouble)
        {
            this.fixedNextInt = fixedNextInt;
            this.fixedNextDouble = fixedNextDouble;
        }

        public int NextInt(int minInclusive, int maxExclusive) => fixedNextInt;

        public double NextDouble() => fixedNextDouble;
    }
}
