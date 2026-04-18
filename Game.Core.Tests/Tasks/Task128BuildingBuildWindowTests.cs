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

public sealed class Task128BuildingBuildWindowTests
{
    // ACC:T128.1
    [Fact]
    public async Task ShouldEmitDeterministicEffectOutputs_WhenWarHallAndTrainingGroundAreBuilt()
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
            rng: new FixedRng(ints: new[] { 1, 1 }, doubles: new[] { 1.0 }),
            randomSeed: 12801,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            buildingsCatalog: CreateSetBBuildingsCatalog());

        await StartSinglePlayerGameAsync(manager, correlationId: "corr-t128-build-start");

        await manager.ExecuteHumanTileActionAsync(action: "build", correlationId: "corr-t128-build-1", causationId: "ut.build");
        await manager.ExecuteHumanTileActionAsync(action: "build", correlationId: "corr-t128-build-2", causationId: "ut.build");

        var builtEvents = bus.Published.Where(evt => evt.Type == SanguoBuildingBuilt.EventType).ToArray();
        builtEvents.Should().HaveCount(2);

        var buildingIds = builtEvents
            .Select(evt => ReadPayload(evt).GetProperty("BuildingId").GetString())
            .ToArray();
        buildingIds.Should().Equal(
            "building_training_ground",
            "building_war_hall");

        var tollDeltas = builtEvents
            .Select(evt => ReadPayload(evt).GetProperty("EconomyStepDeltas").GetProperty("Toll").GetInt32())
            .ToArray();
        tollDeltas.Should().Equal(1, 3);

        var effectOutputEvents = bus.Published.Where(evt => evt.Type == SanguoRelicApplied.EventType).ToArray();
        effectOutputEvents.Should().HaveCount(2, "RED-FIRST: set-B build outputs are expected to publish deterministic effect evidence per build");
    }

    // ACC:T128.1
    [Fact]
    public async Task ShouldEmitFallbackOutput_WhenDefinedSetBEffectCannotBeApplied()
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
            rng: new FixedRng(ints: new[] { 1, 1 }, doubles: new[] { 1.0 }),
            randomSeed: 12811,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            buildingsCatalog: CreateSetBBuildingsCatalog(),
            relicsCatalog: CreateInvalidSetBRelicsCatalog(),
            tileTypesByPositionIndex: new Dictionary<int, string>
            {
                [0] = SanguoMapTileDefinitionV2.TileKindFacility,
            });

        await StartSinglePlayerGameAsync(manager, correlationId: "corr-t128-fallback-start");
        await manager.ExecuteHumanRollDiceAndResolveAsync(correlationId: "corr-t128-fallback-roll", causationId: "ut.roll");

        var lootEvents = bus.Published.Where(evt => evt.Type == SanguoLootGranted.EventType).ToArray();
        lootEvents.Should().ContainSingle();

        var appliedEvents = bus.Published.Where(evt => evt.Type == SanguoRelicApplied.EventType).ToArray();
        appliedEvents.Should().ContainSingle();

        var lootPayload = ReadPayload(lootEvents[0]);
        lootPayload.GetProperty("LootKind").GetString().Should().Be("relic");
        lootPayload.GetProperty("PickedId").GetString().Should().NotBeNullOrWhiteSpace();
        lootPayload.GetProperty("CandidatesSortedIdsHash").GetString().Should().NotBeNullOrWhiteSpace();
        lootPayload.GetProperty("RelicId").ValueKind.Should().Be(JsonValueKind.Null);

        var appliedPayload = ReadPayload(appliedEvents[0]);
        appliedPayload.GetProperty("EffectKind").GetString().Should().Be("fallback_noop");
        appliedPayload.GetProperty("MoneyDelta").GetInt32().Should().Be(0);
        appliedPayload.GetProperty("StepDelta").GetInt32().Should().Be(0);
        appliedPayload.GetProperty("CausationId").GetString().Should().Be(lootEvents[0].Id);

        player.Money.ToDecimal().Should().Be(1000m);
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

    private static SanguoBuildingsCatalog CreateSetBBuildingsCatalog()
    {
        return new SanguoBuildingsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Buildings: new[]
            {
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
            });
    }

    private static SanguoRelicsCatalog CreateInvalidSetBRelicsCatalog()
    {
        return new SanguoRelicsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Relics: new[]
            {
                new SanguoRelicDefinition(
                    RelicId: "relic_training_ground_missing_step",
                    NameKey: "relic.training_ground_missing_step.name",
                    DescriptionKey: "relic.training_ground_missing_step.desc",
                    EffectKind: SanguoEffectKinds.EconomyStepDelta,
                    MoneyDelta: null,
                    EconomyStepDelta: null),
                new SanguoRelicDefinition(
                    RelicId: "relic_war_hall_invalid_kind",
                    NameKey: "relic.war_hall_invalid_kind.name",
                    DescriptionKey: "relic.war_hall_invalid_kind.desc",
                    EffectKind: "invalid_effect_kind",
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
        private readonly Queue<int> ints;
        private readonly Queue<double> doubles;

        public FixedRng(IEnumerable<int>? ints = null, IEnumerable<double>? doubles = null)
        {
            this.ints = new Queue<int>(ints ?? Array.Empty<int>());
            this.doubles = new Queue<double>(doubles ?? Array.Empty<double>());
        }

        public int NextInt(int minInclusive, int maxExclusive)
        {
            if (ints.Count == 0)
            {
                return minInclusive;
            }

            return ints.Dequeue();
        }

        public double NextDouble()
        {
            if (doubles.Count == 0)
            {
                return 1.0;
            }

            return doubles.Dequeue();
        }
    }
}
