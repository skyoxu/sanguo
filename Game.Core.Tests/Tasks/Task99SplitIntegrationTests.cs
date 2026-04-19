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

public sealed class Task99SplitIntegrationTests
{
    private static readonly string[] ExpectedSetABuildings =
    [
        "building_defense_center",
        "building_relic_workshop",
        "building_tavern",
    ];

    private static readonly string[] ExpectedSetBBuildings =
    [
        "building_training_ground",
        "building_war_hall",
    ];

    // ACC:T99.1
    [Fact]
    public async Task ShouldCloseIntegration_WhenRuntimeEvidenceContainsBothSplitTaskBuildingSets()
    {
        var scenario = await RunBuildSequenceAsync(CreateCombinedBuildingsCatalog(), buildCount: 5, randomSeed: 9901);

        var builtIds = scenario.builtEvents
            .Select(evt => ReadPayload(evt).GetProperty("BuildingId").GetString())
            .Where(id => !string.IsNullOrWhiteSpace(id))
            .Cast<string>()
            .ToArray();

        var hasSetA = ExpectedSetABuildings.All(id => builtIds.Contains(id, StringComparer.Ordinal));
        var hasSetB = ExpectedSetBBuildings.All(id => builtIds.Contains(id, StringComparer.Ordinal));
        hasSetA.Should().BeTrue("split task 127 evidence must be present in runtime build outputs");
        hasSetB.Should().BeTrue("split task 128 evidence must be present in runtime build outputs");

        var setBEffectByBuildingId = scenario.relicAppliedEvents
            .Select(evt => ReadPayload(evt))
            .Where(payload => ExpectedSetBBuildings.Contains(payload.GetProperty("RelicId").GetString() ?? string.Empty, StringComparer.Ordinal))
            .ToDictionary(
                payload => payload.GetProperty("RelicId").GetString() ?? string.Empty,
                payload => new
                {
                    EffectKind = payload.GetProperty("EffectKind").GetString(),
                    MoneyDelta = ReadNullableInt(payload, "MoneyDelta"),
                    StepDelta = ReadNullableInt(payload, "StepDelta"),
                },
                StringComparer.Ordinal);

        setBEffectByBuildingId["building_training_ground"].EffectKind.Should().Be(SanguoEffectKinds.EconomyStepDelta);
        setBEffectByBuildingId["building_training_ground"].StepDelta.Should().Be(1);
        setBEffectByBuildingId["building_training_ground"].MoneyDelta.Should().BeNull();

        setBEffectByBuildingId["building_war_hall"].EffectKind.Should().Be(SanguoEffectKinds.MoneyDelta);
        setBEffectByBuildingId["building_war_hall"].MoneyDelta.Should().Be(40);
        setBEffectByBuildingId["building_war_hall"].StepDelta.Should().BeNull();
    }

    // ACC:T99.1
    [Fact]
    public async Task ShouldFailAcceptance_WhenRuntimeEvidenceIsMissingTask127BuildingSetA()
    {
        var scenario = await RunBuildSequenceAsync(CreateSetBOnlyBuildingsCatalog(), buildCount: 2, randomSeed: 9902);

        var builtIds = scenario.builtEvents
            .Select(evt => ReadPayload(evt).GetProperty("BuildingId").GetString())
            .Where(id => !string.IsNullOrWhiteSpace(id))
            .Cast<string>()
            .ToArray();

        var hasSetA = ExpectedSetABuildings.All(id => builtIds.Contains(id, StringComparer.Ordinal));
        var hasSetB = ExpectedSetBBuildings.All(id => builtIds.Contains(id, StringComparer.Ordinal));

        hasSetA.Should().BeFalse("if split task 127 evidence is missing, task 99 acceptance must fail");
        hasSetB.Should().BeTrue();
    }

    // ACC:T99.1
    [Fact]
    public async Task ShouldFailAcceptance_WhenRuntimeEvidenceIsMissingTask128BuildingSetB()
    {
        var scenario = await RunBuildSequenceAsync(CreateSetAOnlyBuildingsCatalog(), buildCount: 3, randomSeed: 9903);

        var builtIds = scenario.builtEvents
            .Select(evt => ReadPayload(evt).GetProperty("BuildingId").GetString())
            .Where(id => !string.IsNullOrWhiteSpace(id))
            .Cast<string>()
            .ToArray();

        var hasSetA = ExpectedSetABuildings.All(id => builtIds.Contains(id, StringComparer.Ordinal));
        var hasSetB = ExpectedSetBBuildings.All(id => builtIds.Contains(id, StringComparer.Ordinal));

        hasSetA.Should().BeTrue();
        hasSetB.Should().BeFalse("if split task 128 evidence is missing, task 99 acceptance must fail");
    }

    private static async Task<(DomainEvent[] builtEvents, DomainEvent[] relicAppliedEvents)> RunBuildSequenceAsync(
        SanguoBuildingsCatalog buildingsCatalog,
        int buildCount,
        int randomSeed)
    {
        var city = CreateCityAtIndex(positionIndex: 0, baseTollMajorUnits: 10m);
        var player = new SanguoPlayer(playerId: "p1", money: 2000m, positionIndex: 0, economyRules: SanguoEconomyRules.Default);
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
            randomSeed: randomSeed,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            buildingsCatalog: buildingsCatalog);

        await StartSinglePlayerGameAsync(manager, correlationId: $"corr-task99-build-start-{randomSeed}");

        for (var i = 0; i < buildCount; i++)
        {
            await manager.ExecuteHumanTileActionAsync(
                action: "build",
                correlationId: $"corr-task99-build-{randomSeed}-{i}",
                causationId: "ut.build");
        }

        var builtEvents = bus.Published.Where(evt => evt.Type == SanguoBuildingBuilt.EventType).ToArray();
        var relicAppliedEvents = bus.Published.Where(evt => evt.Type == SanguoRelicApplied.EventType).ToArray();
        return (builtEvents, relicAppliedEvents);
    }

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

    private static SanguoBuildingsCatalog CreateCombinedBuildingsCatalog()
    {
        return new SanguoBuildingsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Buildings: CreateSetABuildingsCatalog().Buildings
                .Concat(CreateSetBOnlyBuildingsCatalog().Buildings)
                .ToArray());
    }

    private static SanguoBuildingsCatalog CreateSetAOnlyBuildingsCatalog()
    {
        return new SanguoBuildingsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Buildings: CreateSetABuildingsCatalog().Buildings.ToArray());
    }

    private static SanguoBuildingsCatalog CreateSetBOnlyBuildingsCatalog()
    {
        return new SanguoBuildingsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Buildings:
            [
                new SanguoBuildingDefinition(
                    BuildingId: "building_training_ground",
                    NameKey: "building.training_ground.name",
                    DescriptionKey: "building.training_ground.desc",
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
                    BuildingId: "building_war_hall",
                    NameKey: "building.war_hall.name",
                    DescriptionKey: "building.war_hall.desc",
                    MaxLevel: 1,
                    BuildCostBase: 0,
                    UpgradeCostBase: 0,
                    SettlementIncomeBase: 0,
                    EconomyStepDeltas: new SanguoEconomyStepDeltas(
                        BuyPrice: 0,
                        Toll: 3,
                        IncomeSettlement: 0,
                        BuildCost: 0,
                        UpgradeCost: 0)),
            ]);
    }

    private static SanguoBuildingsCatalog CreateSetABuildingsCatalog()
    {
        return new SanguoBuildingsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Buildings:
            [
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
            ]);
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
