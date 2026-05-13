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
using Game.Core.Services;
using Game.Core.Utilities;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task181AcceptanceTests
{
    private const int TaskId = 181;
    private const string Task181Ref = "Game.Core.Tests/Tasks/Task181AcceptanceTests.cs";
    private const string CombatResolverRef = "Game.Core/Services/Sanguo/SanguoCombatResolver.cs";
    private const string CombatContractsRef = "Game.Core/Contracts/Sanguo/SanguoCombatContracts.cs";

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
    };

    // ACC:T181.1
    [Fact]
    [Trait("acceptance", "ACC:T181.1")]
    public async Task ShouldKeepSemanticEvidenceChainTraceable_WhenBoundaryBehaviorRemainsExecutable()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptance = ReadStringArray(task, "acceptance");
            var testRefs = ReadStringArray(task, "test_refs");

            acceptance.Should().HaveCount(9);
            acceptance[0].Should().Contain("semantic evidence");
            testRefs.Should().ContainSingle().Which.Should().Be(Task181Ref);
        }

        var win = Game.Core.Services.Sanguo.SanguoCombatResolver.ResolvePveCombat(
            combatRating: 20,
            encounterTarget: 20,
            seed: 7);
        var lose = Game.Core.Services.Sanguo.SanguoCombatResolver.ResolvePveCombat(
            combatRating: 19,
            encounterTarget: 20,
            seed: 7);
        win.Outcome.Should().Be("win");
        lose.Outcome.Should().Be("lose");
        lose.MoneyDelta.Should().Be(0m);

        var bus = new CapturingEventBus();
        var runtime = await CreateManagerAndStartGameAsync(
            bus: bus,
            tileTypeAtStartPosition: SanguoTileDefinition.TileTypePass,
            combatRating: 100);
        await runtime.Manager.ExecuteHumanTileActionAsync(
            action: "start_combat",
            correlationId: "corr-acc1-181",
            causationId: "ut.action");
        bus.Published.Should().Contain(x => x.Type == SanguoCombatStarted.EventType);
        bus.Published.Should().Contain(x => x.Type == SanguoCombatEnded.EventType);
    }

    // ACC:T181.2
    [Fact]
    [Trait("acceptance", "ACC:T181.2")]
    public async Task ShouldBindAcceptanceAnchorsToFalsifiableBehaviors_WhenStartedEndedRoleSetsStayStable()
    {
        var winBus = new CapturingEventBus();
        var win = await CreateManagerAndStartGameAsync(
            bus: winBus,
            tileTypeAtStartPosition: SanguoTileDefinition.TileTypePass,
            combatRating: 100);
        await win.Manager.ExecuteHumanTileActionAsync(
            action: "start_combat",
            correlationId: "corr-acc2-win-181",
            causationId: "ut.action");

        var winStarted = ExtractCombatEvent(winBus, SanguoCombatStarted.EventType);
        var winEnded = ExtractCombatEvent(winBus, SanguoCombatEnded.EventType);
        var winStartedRoles = ExtractRoleSetFromEvent(winStarted, "PlayerSnapshot", "EnemySnapshot");
        var winEndedRoles = ExtractRoleSetFromEvent(
            winEnded.GetProperty("Result"),
            "PlayerSnapshot",
            "EnemySnapshot");

        var loseBus = new CapturingEventBus();
        var lose = await CreateManagerAndStartGameAsync(
            bus: loseBus,
            tileTypeAtStartPosition: SanguoTileDefinition.TileTypePass,
            combatRating: 0);
        await lose.Manager.ExecuteHumanTileActionAsync(
            action: "start_combat",
            correlationId: "corr-acc2-lose-181",
            causationId: "ut.action");

        var loseStarted = ExtractCombatEvent(loseBus, SanguoCombatStarted.EventType);
        var loseEnded = ExtractCombatEvent(loseBus, SanguoCombatEnded.EventType);
        var loseStartedRoles = ExtractRoleSetFromEvent(loseStarted, "PlayerSnapshot", "EnemySnapshot");
        var loseEndedRoles = ExtractRoleSetFromEvent(
            loseEnded.GetProperty("Result"),
            "PlayerSnapshot",
            "EnemySnapshot");

        winStartedRoles.Should().BeEquivalentTo(winEndedRoles);
        loseStartedRoles.Should().BeEquivalentTo(loseEndedRoles);
        winEnded.GetProperty("Result").GetProperty("Outcome").GetString().Should().Be("win");
        loseEnded.GetProperty("Result").GetProperty("Outcome").GetString().Should().Be("lose");
    }

    // ACC:T181.3
    [Fact]
    [Trait("acceptance", "ACC:T181.3")]
    public void ShouldExposeThresholdCombatOutcome_WhenEncounterTargetBoundaryIsCrossed()
    {
        var win = Game.Core.Services.Sanguo.SanguoCombatResolver.ResolvePveCombat(
            combatRating: 20,
            encounterTarget: 20,
            seed: 7);
        var lose = Game.Core.Services.Sanguo.SanguoCombatResolver.ResolvePveCombat(
            combatRating: 19,
            encounterTarget: 20,
            seed: 7);

        win.Outcome.Should().Be("win");
        win.EncounterTarget.Should().Be(20);
        win.EffectiveCombatRating.Should().Be(20);
        lose.Outcome.Should().Be("lose");
        lose.EncounterTarget.Should().Be(20);
        lose.EffectiveCombatRating.Should().Be(19);
        lose.MoneyDelta.Should().Be(0m);
    }

    // ACC:T181.4
    [Fact]
    [Trait("acceptance", "ACC:T181.4")]
    public void ShouldKeepRuntimeSnapshotsUnset_WhenResolverOnlyEmitsMinimalResultSurface()
    {
        var result = Game.Core.Services.Sanguo.SanguoCombatResolver.ResolvePveCombat(
            combatRating: 25,
            encounterTarget: 20,
            seed: 7);

        result.PlayerSnapshot.Should().BeNull();
        result.EnemySnapshot.Should().BeNull();
        result.Rewards.Should().BeNull();
        result.RecentLogEntries.Should().BeNull();
    }

    // ACC:T181.5
    [Fact]
    [Trait("acceptance", "ACC:T181.5")]
    public void ShouldKeepEventSnapshotsUnset_WhenCombatEndedUsesCurrentMinimalResolverPayload()
    {
        var result = Game.Core.Services.Sanguo.SanguoCombatResolver.ResolvePveCombat(
            combatRating: 30,
            encounterTarget: 20,
            seed: 7);
        var ended = new Game.Core.Contracts.Sanguo.SanguoCombatEnded(
            GameId: "g-181",
            PlayerId: "p-181",
            EncounterId: "enc-181",
            Result: result,
            OccurredAt: DateTimeOffset.UnixEpoch,
            CorrelationId: "corr-181",
            CausationId: null);

        ended.PlayerSnapshot.Should().BeNull();
        ended.EnemySnapshot.Should().BeNull();
        ended.Result.PlayerSnapshot.Should().BeNull();
        ended.Result.EnemySnapshot.Should().BeNull();
    }

    // ACC:T181.6
    [Fact]
    [Trait("acceptance", "ACC:T181.6")]
    public void ShouldKeepLossResultLimitedToCombatOutcomeAndDelta_WhenMapReturnRecoveryIsOutOfScope()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptance = ReadStringArray(task, "acceptance");
            acceptance[5].Should().Contain("must not claim");
            acceptance[5].Should().Contain("map/main-loop return");
            acceptance[5].Should().Contain("later slice");
        }

        var contractsPath = Path.Combine(repoRoot, CombatContractsRef.Replace('/', Path.DirectorySeparatorChar));
        var contractsText = File.ReadAllText(contractsPath);
        contractsText.Should().Contain("SanguoCombatEnded");
        contractsText.Should().Contain("SanguoCombatResult");
        contractsText.Should().NotContain("Restore");
        contractsText.Should().NotContain("50% MaxHP");

        var loss = Game.Core.Services.Sanguo.SanguoCombatResolver.ResolvePveCombat(
            combatRating: 0,
            encounterTarget: 99,
            seed: 9);
        loss.Outcome.Should().Be("lose");
        loss.MoneyDelta.Should().Be(0m);
        loss.PlayerSnapshot.Should().BeNull();
        loss.EnemySnapshot.Should().BeNull();
    }

    // ACC:T181.7
    [Fact]
    [Trait("acceptance", "ACC:T181.7")]
    public void ShouldPreserveUnitRoleIdentityAcrossStartedAndEndedContracts_WhenOutcomeChanges()
    {
        var sample = BuildRoleStableSample();
        var startedRoles = ExtractRoleSet(sample.Started.PlayerSnapshot, sample.Started.EnemySnapshot);
        var endedWinRoles = ExtractRoleSet(sample.Win.Result.PlayerSnapshot, sample.Win.Result.EnemySnapshot);
        var endedLoseRoles = ExtractRoleSet(sample.Lose.Result.PlayerSnapshot, sample.Lose.Result.EnemySnapshot);

        sample.Win.Result.Outcome.Should().Be("win");
        sample.Lose.Result.Outcome.Should().Be("lose");
        startedRoles.Should().Contain(new[] { "player-main-unit", "boss-main-unit", "enemy-unit" });
        endedWinRoles.Should().BeEquivalentTo(startedRoles);
        endedLoseRoles.Should().BeEquivalentTo(startedRoles);
    }

    // ACC:T181.8
    [Fact]
    [Trait("acceptance", "ACC:T181.8")]
    public async Task ShouldEmitStartedEndedForValidStart_WhenInvalidStartLeavesStateUnchanged()
    {
        var validBus = new CapturingEventBus();
        var validPlayer = await CreateManagerAndStartGameAsync(
            bus: validBus,
            tileTypeAtStartPosition: SanguoTileDefinition.TileTypePass,
            combatRating: 100);

        await validPlayer.Manager.ExecuteHumanTileActionAsync(
            action: "start_combat",
            correlationId: "corr-valid-181",
            causationId: "ut.action");

        var started = validBus.Published.SingleOrDefault(x => x.Type == SanguoCombatStarted.EventType);
        var ended = validBus.Published.SingleOrDefault(x => x.Type == SanguoCombatEnded.EventType);
        started.Should().NotBeNull();
        ended.Should().NotBeNull();

        var startedJson = ((JsonElementEventData)started!.Data!).Value;
        var endedJson = ((JsonElementEventData)ended!.Data!).Value;
        startedJson.GetProperty("CorrelationId").GetString().Should().Be("corr-valid-181");
        endedJson.GetProperty("CorrelationId").GetString().Should().Be("corr-valid-181");
        startedJson.GetProperty("EncounterId").GetString().Should().NotBeNullOrWhiteSpace();
        startedJson.GetProperty("RandomSeed").GetInt32().Should().BeGreaterThan(0);
        endedJson.GetProperty("Result").GetProperty("EncounterTarget").GetInt32().Should().BeGreaterThan(0);

        var invalidBus = new CapturingEventBus();
        var invalidPlayer = await CreateManagerAndStartGameAsync(
            bus: invalidBus,
            tileTypeAtStartPosition: SanguoTileDefinition.TileTypeCity,
            combatRating: 100);
        var originalMoney = invalidPlayer.Player.Money.ToDecimal();

        await invalidPlayer.Manager.ExecuteHumanTileActionAsync(
            action: "start_combat",
            correlationId: "corr-invalid-181",
            causationId: "ut.action");

        invalidBus.Published.Should().NotContain(x => x.Type == SanguoCombatStarted.EventType);
        invalidBus.Published.Should().NotContain(x => x.Type == SanguoCombatEnded.EventType);
        invalidPlayer.Player.Money.ToDecimal().Should().Be(originalMoney);
    }

    // ACC:T181.9
    [Fact]
    [Trait("acceptance", "ACC:T181.9")]
    public void ShouldKeepEndedResultPayloadCompleteAcrossWinLose_WhenUsingSameBoundaryInput()
    {
        var winResult = Game.Core.Services.Sanguo.SanguoCombatResolver.ResolvePveCombat(
            combatRating: 20,
            encounterTarget: 20,
            seed: 7);
        var loseResult = Game.Core.Services.Sanguo.SanguoCombatResolver.ResolvePveCombat(
            combatRating: 19,
            encounterTarget: 20,
            seed: 7);

        var winEnded = new SanguoCombatEnded(
            GameId: "g-181",
            PlayerId: "p-181",
            EncounterId: "enc-181",
            Result: winResult,
            OccurredAt: DateTimeOffset.UnixEpoch,
            CorrelationId: "corr-win-181",
            CausationId: "ut.action");
        var loseEnded = new SanguoCombatEnded(
            GameId: "g-181",
            PlayerId: "p-181",
            EncounterId: "enc-181",
            Result: loseResult,
            OccurredAt: DateTimeOffset.UnixEpoch,
            CorrelationId: "corr-lose-181",
            CausationId: "ut.action");

        winEnded.Result.Outcome.Should().Be("win");
        loseEnded.Result.Outcome.Should().Be("lose");
        winEnded.Result.EncounterTarget.Should().Be(20);
        loseEnded.Result.EncounterTarget.Should().Be(20);
        winEnded.Result.EffectiveCombatRating.Should().Be(20);
        loseEnded.Result.EffectiveCombatRating.Should().Be(19);
        winEnded.Result.MoneyDelta.Should().Be(winResult.MoneyDelta);
        loseEnded.Result.MoneyDelta.Should().Be(loseResult.MoneyDelta);
    }

    private static string FindRepoRoot()
    {
        var current = new DirectoryInfo(AppContext.BaseDirectory);
        while (current is not null)
        {
            var marker = Path.Combine(current.FullName, ".taskmaster", "tasks", "tasks.json");
            if (File.Exists(marker))
            {
                return current.FullName;
            }

            current = current.Parent;
        }

        throw new DirectoryNotFoundException("Repo root not found (missing .taskmaster/tasks/tasks.json).");
    }

    private static JsonDocument LoadJson(string repoRoot, params string[] parts)
    {
        var path = Path.Combine(new[] { repoRoot }.Concat(parts).ToArray());
        using var stream = File.OpenRead(path);
        return JsonDocument.Parse(stream);
    }

    private static JsonElement GetTaskByTaskmasterId(string repoRoot, string fileName, int taskmasterId)
    {
        using var doc = LoadJson(repoRoot, ".taskmaster", "tasks", fileName);
        foreach (var task in doc.RootElement.EnumerateArray())
        {
            if (task.TryGetProperty("taskmaster_id", out var idProperty) &&
                idProperty.ValueKind == JsonValueKind.Number &&
                idProperty.TryGetInt32(out var idValue) &&
                idValue == taskmasterId)
            {
                return task.Clone();
            }
        }

        throw new InvalidOperationException($"Task {taskmasterId} not found in {fileName}.");
    }

    private static string[] ReadStringArray(JsonElement element, string propertyName)
    {
        element.TryGetProperty(propertyName, out var value).Should().BeTrue();
        value.ValueKind.Should().Be(JsonValueKind.Array);
        return value.EnumerateArray().Select(static item => item.GetString() ?? string.Empty).ToArray();
    }

    private static async Task<(SanguoTurnManager Manager, SanguoPlayer Player)> CreateManagerAndStartGameAsync(
        CapturingEventBus bus,
        string tileTypeAtStartPosition,
        int combatRating)
    {
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;
        var player = new SanguoPlayer(playerId: "p1", money: 300m, positionIndex: 0, economyRules: rules);
        var boardState = new SanguoBoardState(players: new[] { player }, citiesById: new Dictionary<string, City>());
        var treasury = new SanguoTreasury();

        var tileTypes = new Dictionary<int, string> { [0] = tileTypeAtStartPosition };
        var combatRatingByPlayerId = new Dictionary<string, int>(StringComparer.Ordinal) { ["p1"] = combatRating };

        var manager = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: new DeterministicRandomNumberGenerator(seed: 7),
            randomSeed: 7,
            totalPositionsHint: 1,
            quarterEnvironmentEventTriggerChance: 0.0,
            tileTypesByPositionIndex: tileTypes,
            combatRatingByPlayerId: combatRatingByPlayerId);

        await manager.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 3,
            month: 2,
            day: 1,
            correlationId: "corr-start-181",
            causationId: "ut.start");
        bus.Published.Clear();

        return (manager, player);
    }

    private static (SanguoCombatStarted Started, SanguoCombatEnded Win, SanguoCombatEnded Lose) BuildRoleStableSample()
    {
        var playerMain = new SanguoCombatUnitSnapshot(
            UnitId: "player-main",
            DisplayName: "Player Main Unit",
            UnitRole: "player-main-unit",
            Stats: new SanguoCombatStatsDefinition(MaxHP: 100, CurrentHP: 100, Attack: 18));
        var enemyMain = new SanguoCombatUnitSnapshot(
            UnitId: "enemy-boss-main",
            DisplayName: "Enemy Boss Main Unit",
            UnitRole: "boss-main-unit",
            Stats: new SanguoCombatStatsDefinition(MaxHP: 130, CurrentHP: 130, Attack: 22));
        var enemySummon = new SanguoCombatUnitSnapshot(
            UnitId: "enemy-summon-1",
            DisplayName: "Enemy Summon",
            UnitRole: "enemy-unit",
            Stats: new SanguoCombatStatsDefinition(MaxHP: 60, CurrentHP: 60, Attack: 12));

        var playerSnapshot = new SanguoCombatRuntimeSnapshot(MainUnit: playerMain);
        var enemySnapshot = new SanguoCombatRuntimeSnapshot(MainUnit: enemyMain, Summons: new[] { enemySummon });

        var started = new SanguoCombatStarted(
            GameId: "g-181",
            PlayerId: "p-181",
            EncounterId: "enc-boss-181",
            RandomSeed: 7,
            OccurredAt: DateTimeOffset.UnixEpoch,
            CorrelationId: "corr-181",
            CausationId: "ut.start_combat",
            PlayerSnapshot: playerSnapshot,
            EnemySnapshot: enemySnapshot);

        var win = new SanguoCombatEnded(
            GameId: started.GameId,
            PlayerId: started.PlayerId,
            EncounterId: started.EncounterId,
            Result: new SanguoCombatResult(
                Outcome: "win",
                MoneyDelta: 50m,
                EncounterTarget: 20,
                EffectiveCombatRating: 20,
                PlayerSnapshot: playerSnapshot,
                EnemySnapshot: enemySnapshot),
            OccurredAt: DateTimeOffset.UnixEpoch.AddSeconds(1),
            CorrelationId: started.CorrelationId,
            CausationId: started.CausationId,
            PlayerSnapshot: playerSnapshot,
            EnemySnapshot: enemySnapshot);

        var lose = win with
        {
            Result = win.Result with
            {
                Outcome = "lose",
                MoneyDelta = 0m,
            },
        };
        return (started, win, lose);
    }

    private static HashSet<string> ExtractRoleSet(
        SanguoCombatRuntimeSnapshot? playerSnapshot,
        SanguoCombatRuntimeSnapshot? enemySnapshot)
    {
        var set = new HashSet<string>(StringComparer.Ordinal);
        AddRoles(set, playerSnapshot);
        AddRoles(set, enemySnapshot);
        return set;
    }

    private static void AddRoles(HashSet<string> set, SanguoCombatRuntimeSnapshot? snapshot)
    {
        if (snapshot is null)
        {
            return;
        }

        if (!string.IsNullOrWhiteSpace(snapshot.MainUnit.UnitRole))
        {
            set.Add(snapshot.MainUnit.UnitRole);
        }

        if (snapshot.Summons is null)
        {
            return;
        }

        foreach (var summon in snapshot.Summons)
        {
            if (!string.IsNullOrWhiteSpace(summon.UnitRole))
            {
                set.Add(summon.UnitRole);
            }
        }
    }

    private static JsonElement ExtractCombatEvent(CapturingEventBus bus, string eventType)
    {
        var evt = bus.Published.SingleOrDefault(x => x.Type == eventType);
        evt.Should().NotBeNull();
        return ((JsonElementEventData)evt!.Data!).Value;
    }

    private static HashSet<string> ExtractRoleSetFromEvent(JsonElement payload, string playerSnapshotProperty, string enemySnapshotProperty)
    {
        var roles = new HashSet<string>(StringComparer.Ordinal);
        AddRolesFromSnapshotProperty(payload, playerSnapshotProperty, roles);
        AddRolesFromSnapshotProperty(payload, enemySnapshotProperty, roles);
        return roles;
    }

    private static void AddRolesFromSnapshotProperty(JsonElement payload, string propertyName, HashSet<string> roles)
    {
        if (!payload.TryGetProperty(propertyName, out var snapshot) || snapshot.ValueKind != JsonValueKind.Object)
        {
            return;
        }

        if (snapshot.TryGetProperty("MainUnit", out var mainUnit) &&
            mainUnit.ValueKind == JsonValueKind.Object &&
            mainUnit.TryGetProperty("UnitRole", out var roleNode))
        {
            var role = roleNode.GetString();
            if (!string.IsNullOrWhiteSpace(role))
            {
                roles.Add(role);
            }
        }

        if (!snapshot.TryGetProperty("Summons", out var summons) || summons.ValueKind != JsonValueKind.Array)
        {
            return;
        }

        foreach (var summon in summons.EnumerateArray())
        {
            if (summon.ValueKind != JsonValueKind.Object)
            {
                continue;
            }

            if (summon.TryGetProperty("UnitRole", out var summonRoleNode))
            {
                var role = summonRoleNode.GetString();
                if (!string.IsNullOrWhiteSpace(role))
                {
                    roles.Add(role);
                }
            }
        }
    }

    private sealed class CapturingEventBus : IEventBus
    {
        public List<DomainEvent> Published { get; } = new();

        public Task PublishAsync(DomainEvent evt)
        {
            Published.Add(evt);
            return Task.CompletedTask;
        }

        public IDisposable Subscribe(Func<DomainEvent, Task> handler) => new DummySubscription();

        private sealed class DummySubscription : IDisposable
        {
            public void Dispose()
            {
            }
        }
    }
}
