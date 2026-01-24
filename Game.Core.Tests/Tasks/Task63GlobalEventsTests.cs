#nullable enable

using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Services;
using Game.Core.Utilities;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task63GlobalEventsTests
{
    private const string RoundGateTypeName = "Game.Core.Services.SanguoGlobalEventRoundGate";
    private const string GlobalEventIdTypeName = "Game.Core.Services.SanguoGlobalEventId";
    private const string DeterminismTypeName = "Game.Core.Services.SanguoDeterminism";
    private const string SelectorTypeName = "Game.Core.Services.SanguoGlobalEventSelector";
    private const string OrderingRulesTypeName = "Game.Core.Contracts.Sanguo.SanguoEventOrderingRules";

    // ACC:T63.1
    [Fact]
    [Trait("acceptance", "ACC:T63.1")]
    public void GivenRoundNumber_WhenMarkingCheckedTwice_ThenSecondIsFalse()
    {
        var gateType = FindTypeOrNull(RoundGateTypeName);
        gateType.Should().NotBeNull($"Expected type '{RoundGateTypeName}' to exist to enforce once-per-round checks.");

        var gate = Activator.CreateInstance(gateType!);
        gate.Should().NotBeNull($"Expected '{RoundGateTypeName}' to be constructible.");

        var tryMarkChecked = gateType!.GetMethod(
            "TryMarkChecked",
            BindingFlags.Instance | BindingFlags.Public,
            binder: null,
            types: new[] { typeof(int) },
            modifiers: null);

        tryMarkChecked.Should().NotBeNull("Expected a public instance method TryMarkChecked(int roundNumber) to exist.");
        tryMarkChecked!.ReturnType.Should().Be(typeof(bool), "TryMarkChecked should return true only on the first check for a round.");

        var first = (bool)tryMarkChecked.Invoke(gate, new object[] { 1 })!;
        var second = (bool)tryMarkChecked.Invoke(gate, new object[] { 1 })!;
        var nextRound = (bool)tryMarkChecked.Invoke(gate, new object[] { 2 })!;

        first.Should().BeTrue("the first check for a given RoundNumber must run");
        second.Should().BeFalse("the second check within the same RoundNumber must not run");
        nextRound.Should().BeTrue("a new RoundNumber must allow a new check");
    }

    // ACC:T63.2
    [Fact]
    [Trait("acceptance", "ACC:T63.2")]
    public void ShouldPrefixGlobalId_WhenNormalizingGlobalEventId()
    {
        var idType = FindTypeOrNull(GlobalEventIdTypeName);
        idType.Should().NotBeNull($"Expected type '{GlobalEventIdTypeName}' to exist to normalize global event ids.");

        var prefixMethod = idType!.GetMethod(
            "Prefix",
            BindingFlags.Public | BindingFlags.Static,
            binder: null,
            types: new[] { typeof(string) },
            modifiers: null)
            ?? idType.GetMethod(
                "PrefixGlobal",
                BindingFlags.Public | BindingFlags.Static,
                binder: null,
                types: new[] { typeof(string) },
                modifiers: null)
            ?? idType.GetMethod(
                "WithGlobalPrefix",
                BindingFlags.Public | BindingFlags.Static,
                binder: null,
                types: new[] { typeof(string) },
                modifiers: null);

        prefixMethod.Should().NotBeNull("Expected a public static method Prefix/PrefixGlobal/WithGlobalPrefix(string eventId) to exist.");
        prefixMethod!.ReturnType.Should().Be(typeof(string));

        var raw = "drought";
        var prefixed = (string)prefixMethod.Invoke(null, new object[] { raw })!;
        var prefixedAgain = (string)prefixMethod.Invoke(null, new object[] { prefixed })!;

        prefixed.Should().Be("global:drought", "global events must be distinguishable via a 'global:' prefix");
        prefixedAgain.Should().Be("global:drought", "prefixing must be idempotent");
    }

    // ACC:T63.3
    [Fact]
    [Trait("acceptance", "ACC:T63.3")]
    public void GivenCandidates_WhenComputingEvidenceHash_ThenIsOrderInsensitive()
    {
        var determinismType = FindTypeOrNull(DeterminismTypeName);
        determinismType.Should().NotBeNull($"Expected type '{DeterminismTypeName}' to exist to compute determinism evidence.");

        var hashMethod = determinismType!.GetMethod(
            "ComputeCandidatesSortedIdsHash",
            BindingFlags.Public | BindingFlags.Static,
            binder: null,
            types: new[] { typeof(IEnumerable<string>) },
            modifiers: null)
            ?? determinismType.GetMethod(
                "ComputeCandidatesSortedIdsHash",
                BindingFlags.Public | BindingFlags.Static,
                binder: null,
                types: new[] { typeof(IReadOnlyList<string>) },
                modifiers: null)
            ?? determinismType.GetMethod(
                "ComputeCandidatesSortedIdsHash",
                BindingFlags.Public | BindingFlags.Static,
                binder: null,
                types: new[] { typeof(string[]) },
                modifiers: null);

        hashMethod.Should().NotBeNull("Expected a public static method ComputeCandidatesSortedIdsHash(...) to exist.");
        hashMethod!.ReturnType.Should().Be(typeof(string));

        var a = new[] { "b", "a", "c" };
        var b = new[] { "c", "b", "a" };
        var c = new[] { "b", "a", "d" };

        var ha = (string)hashMethod.Invoke(null, new object[] { a })!;
        var hb = (string)hashMethod.Invoke(null, new object[] { b })!;
        var hc = (string)hashMethod.Invoke(null, new object[] { c })!;

        ha.Should().NotBeNullOrWhiteSpace("evidence hash must be present for audit and replay");
        hb.Should().NotBeNullOrWhiteSpace();
        hc.Should().NotBeNullOrWhiteSpace();

        ha.Should().Be(hb, "candidate order must not affect the evidence hash (it must hash the sorted ids)");
        hc.Should().NotBe(ha, "changing the candidate set must change the evidence hash");
    }

    // ACC:T63.4
    [Fact]
    [Trait("acceptance", "ACC:T63.4")]
    public void ShouldAllowRandomEventAppliedBeforeTurnStarted_WhenValidatingEventOrdering()
    {
        var rulesType = FindTypeOrNull(OrderingRulesTypeName);
        rulesType.Should().NotBeNull($"Expected type '{OrderingRulesTypeName}' to exist to enforce/describe event ordering.");

        const string randomEventApplied = "core.sanguo.random_event.applied";
        const string turnStarted = "core.sanguo.game.turn.started";

        if (TryValidateSequence(rulesType!, new[] { randomEventApplied, turnStarted }, out var validationException))
        {
            validationException.Should().BeNull("global event checks must be able to publish random_event.applied before turn.started");
            return;
        }

        var orderIndex = TryGetOrderIndexMap(rulesType!);
        orderIndex.Should().NotBeNull(
            "Expected either a ValidateSequence/Validate method or an exposed ordering map/list to make ordering testable.");

        orderIndex!.TryGetValue(randomEventApplied, out var iApplied).Should().BeTrue("ordering rules must include random_event.applied");
        orderIndex!.TryGetValue(turnStarted, out var iTurnStarted).Should().BeTrue("ordering rules must include game.turn.started");

        iApplied.Should().BeLessThan(iTurnStarted, "random_event.applied must be allowed to occur before turn.started for global checks");
    }

    // ACC:T63.5
    [Fact]
    [Trait("acceptance", "ACC:T63.5")]
    public void GivenSameInputs_WhenSelectingGlobalEventTwice_ThenEvidenceIsIdentical()
    {
        var selectorType = FindTypeOrNull(SelectorTypeName);
        selectorType.Should().NotBeNull($"Expected type '{SelectorTypeName}' to exist to perform deterministic global-event selection.");

        var selectMethod = selectorType!.GetMethods(BindingFlags.Public | BindingFlags.Instance)
            .FirstOrDefault(m =>
            {
                if (!string.Equals(m.Name, "Select", StringComparison.Ordinal))
                    return false;

                var p = m.GetParameters();
                if (p.Length != 3)
                    return false;

                return p[0].ParameterType == typeof(string)
                    && p[1].ParameterType == typeof(int)
                    && typeof(IEnumerable<string>).IsAssignableFrom(p[2].ParameterType);
            });

        selectMethod.Should().NotBeNull(
            "Expected a public instance method Select(string rngContextId, int roundNumber, IEnumerable<string> candidates) to exist.");

        var selector = Activator.CreateInstance(selectorType!);
        selector.Should().NotBeNull($"Expected '{SelectorTypeName}' to be constructible.");

        var rngContextId = "global:turn-events:5:2:global:drought";
        var roundNumber = 2;
        var candidates = new[] { "drought", "flood", "locust" };

        var first = selectMethod!.Invoke(selector, new object[] { rngContextId, roundNumber, candidates });
        var second = selectMethod!.Invoke(selector, new object[] { rngContextId, roundNumber, candidates });

        first.Should().NotBeNull("selection must return determinism evidence");
        second.Should().NotBeNull();

        var firstEvidence = ReadEvidenceSnapshot(first!);
        var secondEvidence = ReadEvidenceSnapshot(second!);

        firstEvidence.RngContextId.Should().Be(rngContextId);
        secondEvidence.RngContextId.Should().Be(rngContextId);

        firstEvidence.Should().BeEquivalentTo(
            secondEvidence,
            "with identical inputs (RoundNumber, candidate set, and RNG context), selection must be exactly reproducible");

        firstEvidence.CandidatesSortedIdsHash.Should().NotBeNullOrWhiteSpace();
        firstEvidence.PickedId.Should().NotBeNullOrWhiteSpace();
        firstEvidence.PickedIndex.Should().BeGreaterOrEqualTo(0);

        var orderedCandidates = candidates.OrderBy(x => x, StringComparer.Ordinal).ToArray();
        firstEvidence.PickedIndex.Should().BeLessThan(orderedCandidates.Length);
        firstEvidence.PickedId.Should().Be(orderedCandidates[firstEvidence.PickedIndex]);

        var expectedHash = ComputeSha256Hex(string.Join("\n", orderedCandidates));
        firstEvidence.CandidatesSortedIdsHash.Should().Be(expectedHash);
    }

    // ACC:T63.4
    [Fact]
    [Trait("acceptance", "ACC:T63.4")]
    public async Task ShouldRunGlobalEventCheckBeforeTurnStarted_AndNotRepeatWithinSameRound()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;

        var players = new[]
        {
            new SanguoPlayer(playerId: "p1", money: 0m, positionIndex: 0, economyRules: rules),
            new SanguoPlayer(playerId: "p2", money: 0m, positionIndex: 0, economyRules: rules),
            new SanguoPlayer(playerId: "p3", money: 0m, positionIndex: 0, economyRules: rules),
            new SanguoPlayer(playerId: "p4", money: 0m, positionIndex: 0, economyRules: rules),
        };

        var boardState = new SanguoBoardState(players: players, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));
        var treasury = new SanguoTreasury();

        var catalog = new SanguoRandomEventsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Events: new[]
            {
                new SanguoRandomEventCatalogEntry(
                    EventId: "drought",
                    NameKey: "event.drought.name",
                    DescriptionKey: "event.drought.desc",
                    EffectKind: "economyStepDelta",
                    MoneyDelta: null,
                    StepDelta: 1,
                    CooldownRounds: 0,
                    UniqueOnce: false),
            },
            EventPools: new[]
            {
                new SanguoRandomEventPoolCatalogEntry(PoolId: "global", EventIds: new[] { "drought" }),
                new SanguoRandomEventPoolCatalogEntry(PoolId: "default", EventIds: new[] { "drought" }),
            });

        var manager = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: new FixedRng(),
            totalPositionsHint: 0,
            quarterEnvironmentEventTriggerChance: 0.0,
            quarterEnvironmentEventYieldMultiplier: 1.0m,
            randomEventsCatalog: catalog,
            globalEventIntervalTurns: 5,
            tileRandomEventPoolId: "default",
            globalRandomEventPoolId: "global");

        await manager.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "p2", "p3", "p4" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "c1",
            causationId: null);

        bus.Published.Should().Contain(
            e => e.Type == SanguoRandomEventApplied.EventType,
            "global round checks may emit core.sanguo.random_event.applied before the first turn starts");

        var iApplied = bus.Published.FindIndex(e => e.Type == SanguoRandomEventApplied.EventType);
        var iTurnStarted = bus.Published.FindIndex(e => e.Type == SanguoGameTurnStarted.EventType);
        iApplied.Should().BeGreaterOrEqualTo(0);
        iTurnStarted.Should().BeGreaterOrEqualTo(0);
        iApplied.Should().BeLessThan(iTurnStarted, "global checks must run before publishing turn.started when RoundNumber is not yet checked");

        var firstApplied = bus.Published.First(e => e.Type == SanguoRandomEventApplied.EventType);
        var data = (firstApplied.Data as JsonElementEventData)?.Value;
        data.HasValue.Should().BeTrue();
        if (data.HasValue)
        {
            data.Value.TryGetProperty("EventId", out var eventId).Should().BeTrue();
            eventId.GetString().Should().Be("global:drought");

            data.Value.TryGetProperty("PickedId", out var pickedId).Should().BeTrue();
            pickedId.GetString().Should().Be("drought");

            data.Value.TryGetProperty("RngContextId", out var rngContextId).Should().BeTrue();
            rngContextId.GetString().Should().NotBeNullOrWhiteSpace();

            data.Value.TryGetProperty("CandidatesSortedIdsHash", out var h).Should().BeTrue();
            h.GetString().Should().Be(ComputeSha256Hex("drought"));

            data.Value.TryGetProperty("PickedIndex", out var pickedIndex).Should().BeTrue();
            pickedIndex.GetInt32().Should().Be(0);
        }

        var appliedCount = bus.Published.Count(e => e.Type == SanguoRandomEventApplied.EventType);
        await manager.PublishStateSnapshotAsync(correlationId: "c2", causationId: null);
        bus.Published.Count(e => e.Type == SanguoRandomEventApplied.EventType)
            .Should().Be(appliedCount, "the same RoundNumber must not emit a second random_event.applied");
    }

    // ACC:T63.5
    [Fact]
    [Trait("acceptance", "ACC:T63.5")]
    public async Task ShouldNotUseUiDateFields_WhenRunningGlobalRoundCheck()
    {
        var a = await RunStartNewGameAndCaptureGlobalRoundEvidenceAsync(year: 1, month: 1, day: 1);
        var b = await RunStartNewGameAndCaptureGlobalRoundEvidenceAsync(year: 9, month: 12, day: 30);

        b.Should().BeEquivalentTo(a);
    }

    [Fact]
    public async Task ShouldPrefixEventId_WhenGlobalTurnRandomEventApplied()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;

        var players = new[]
        {
            new SanguoPlayer(playerId: "p1", money: 0m, positionIndex: 0, economyRules: rules),
        };

        var boardState = new SanguoBoardState(players: players, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));
        var treasury = new SanguoTreasury();

        var catalog = new SanguoRandomEventsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Events: new[]
            {
                new SanguoRandomEventCatalogEntry(
                    EventId: "drought",
                    NameKey: "event.drought.name",
                    DescriptionKey: "event.drought.desc",
                    EffectKind: "economyStepDelta",
                    MoneyDelta: null,
                    StepDelta: 1,
                    CooldownRounds: 0,
                    UniqueOnce: false),
            },
            EventPools: new[]
            {
                new SanguoRandomEventPoolCatalogEntry(PoolId: "global", EventIds: new[] { "drought" }),
                new SanguoRandomEventPoolCatalogEntry(PoolId: "default", EventIds: new[] { "drought" }),
            });

        var manager = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: new FixedRng(),
            totalPositionsHint: 0,
            quarterEnvironmentEventTriggerChance: 0.0,
            quarterEnvironmentEventYieldMultiplier: 1.0m,
            randomEventsCatalog: catalog,
            globalEventIntervalTurns: 5,
            tileRandomEventPoolId: "default",
            globalRandomEventPoolId: "global");

        await manager.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "c1",
            causationId: null);

        for (var i = 0; i < 5; i++)
            await manager.AdvanceTurnAsync(correlationId: $"adv-{i + 1}", causationId: null);

        var applied = bus.Published.FirstOrDefault(e =>
            e.Type == SanguoRandomEventApplied.EventType
            && HasRngContextToken(e, "global"));
        applied.Should().NotBeNull();

        var data = (applied!.Data as JsonElementEventData)?.Value;
        data.HasValue.Should().BeTrue();
        if (data.HasValue)
        {
            data.Value.TryGetProperty("EventId", out var eventId).Should().BeTrue();
            (eventId.GetString() ?? string.Empty).Should().StartWith("global:");
        }
    }

    [Fact]
    public async Task ShouldPublishRandomEventRejected_WhenNoEligibleCandidatesAtNewRound()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;

        var players = new[]
        {
            new SanguoPlayer(playerId: "p1", money: 0m, positionIndex: 0, economyRules: rules),
            new SanguoPlayer(playerId: "p2", money: 0m, positionIndex: 0, economyRules: rules),
            new SanguoPlayer(playerId: "p3", money: 0m, positionIndex: 0, economyRules: rules),
            new SanguoPlayer(playerId: "p4", money: 0m, positionIndex: 0, economyRules: rules),
        };

        var boardState = new SanguoBoardState(players: players, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));
        var treasury = new SanguoTreasury();

        var catalog = new SanguoRandomEventsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Events: new[]
            {
                new SanguoRandomEventCatalogEntry(
                    EventId: "unique_once",
                    NameKey: "event.unique_once.name",
                    DescriptionKey: "event.unique_once.desc",
                    EffectKind: "economyStepDelta",
                    MoneyDelta: null,
                    StepDelta: 1,
                    CooldownRounds: 0,
                    UniqueOnce: true),
            },
            EventPools: new[]
            {
                new SanguoRandomEventPoolCatalogEntry(PoolId: "global", EventIds: new[] { "unique_once" }),
                new SanguoRandomEventPoolCatalogEntry(PoolId: "default", EventIds: new[] { "unique_once" }),
            });

        var manager = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: new FixedRng(),
            totalPositionsHint: 0,
            quarterEnvironmentEventTriggerChance: 0.0,
            quarterEnvironmentEventYieldMultiplier: 1.0m,
            randomEventsCatalog: catalog,
            globalEventIntervalTurns: 20,
            tileRandomEventPoolId: "default",
            globalRandomEventPoolId: "global");

        await manager.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "p2", "p3", "p4" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "c1",
            causationId: null);

        for (var i = 0; i < 4; i++)
            await manager.AdvanceTurnAsync(correlationId: $"adv-{i + 1}", causationId: null);

        await manager.PublishStateSnapshotAsync(correlationId: "c2", causationId: null);

        bus.Published.Should().Contain(
            e => e.Type == SanguoRandomEventRejected.EventType,
            "when a UniqueOnce global event has no eligible candidates in the new round, it must be auditable via random_event.rejected");
    }

    [Fact]
    public void ShouldThrow_WhenPlayerStateChangedPrecedesTurnStarted()
    {
        Action act = () => SanguoEventOrderingRules.Validate(new[]
        {
            SanguoPlayerStateChanged.EventType,
            SanguoGameTurnStarted.EventType,
        });

        act.Should().Throw<InvalidOperationException>();
    }

    [Fact]
    public void ShouldThrow_WhenTurnEndedIsNotLast()
    {
        Action act = () => SanguoEventOrderingRules.Validate(new[]
        {
            SanguoGameTurnStarted.EventType,
            SanguoGameTurnEnded.EventType,
            SanguoPlayerStateChanged.EventType,
        });

        act.Should().Throw<InvalidOperationException>();
    }

    private static Type? FindTypeOrNull(string fullName)
    {
        foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
        {
            var type = assembly.GetType(fullName, throwOnError: false, ignoreCase: false);
            if (type is not null)
                return type;
        }

        return null;
    }

    private static bool TryValidateSequence(Type rulesType, IReadOnlyList<string> sequence, out Exception? exception)
    {
        exception = null;

        var methods = rulesType.GetMethods(BindingFlags.Public | BindingFlags.Static);
        var validate = methods.FirstOrDefault(m =>
        {
            if (!m.Name.Contains("Validate", StringComparison.OrdinalIgnoreCase))
                return false;

            var p = m.GetParameters();
            if (p.Length == 1 && typeof(IEnumerable<string>).IsAssignableFrom(p[0].ParameterType))
                return true;

            if (p.Length == 1 && p[0].ParameterType == typeof(string[]))
                return true;

            return false;
        });

        if (validate is null)
            return false;

        try
        {
            var arg = validate.GetParameters()[0].ParameterType == typeof(string[])
                ? sequence.ToArray()
                : sequence;

            _ = validate.Invoke(null, new[] { arg });
            return true;
        }
        catch (TargetInvocationException tie)
        {
            exception = tie.InnerException ?? tie;
            return true;
        }
        catch (Exception ex)
        {
            exception = ex;
            return true;
        }
    }

    private static Dictionary<string, int>? TryGetOrderIndexMap(Type rulesType)
    {
        const BindingFlags flags = BindingFlags.Public | BindingFlags.Static;

        foreach (var prop in rulesType.GetProperties(flags))
        {
            var value = prop.GetValue(null);
            var map = TryConvertToIndexMap(value);
            if (map is not null)
                return map;
        }

        foreach (var field in rulesType.GetFields(flags))
        {
            var value = field.GetValue(null);
            var map = TryConvertToIndexMap(value);
            if (map is not null)
                return map;
        }

        return null;
    }

    private static Dictionary<string, int>? TryConvertToIndexMap(object? value)
    {
        if (value is null)
            return null;

        if (value is IReadOnlyDictionary<string, int> roDict)
            return roDict.ToDictionary(kv => kv.Key, kv => kv.Value, StringComparer.Ordinal);

        if (value is IDictionary dict)
        {
            var result = new Dictionary<string, int>(StringComparer.Ordinal);
            foreach (DictionaryEntry entry in dict)
            {
                if (entry.Key is string k && entry.Value is int v)
                    result[k] = v;
            }

            return result.Count > 0 ? result : null;
        }

        if (value is IEnumerable<string> ordered)
        {
            var list = ordered.ToList();
            return list.Count > 0
                ? list.Select((t, i) => (t, i)).ToDictionary(x => x.t, x => x.i, StringComparer.Ordinal)
                : null;
        }

        return null;
    }

    private static EvidenceSnapshot ReadEvidenceSnapshot(object selectionResult)
    {
        var t = selectionResult.GetType();

        var rngContextId = ReadStringProperty(t, selectionResult, "RngContextId");
        var candidatesSortedIdsHash = ReadStringProperty(t, selectionResult, "CandidatesSortedIdsHash");
        var pickedId = ReadStringProperty(t, selectionResult, "PickedId");
        var pickedIndex = ReadIntProperty(t, selectionResult, "PickedIndex");

        return new EvidenceSnapshot(
            RngContextId: rngContextId,
            CandidatesSortedIdsHash: candidatesSortedIdsHash,
            PickedIndex: pickedIndex,
            PickedId: pickedId);
    }

    private static string ReadStringProperty(Type t, object instance, string name)
    {
        var p = t.GetProperty(name, BindingFlags.Public | BindingFlags.Instance);
        p.Should().NotBeNull($"Selection result must expose a public '{name}' property.");
        p!.PropertyType.Should().Be(typeof(string), $"'{name}' must be a string.");
        return (string)(p.GetValue(instance) ?? string.Empty);
    }

    private static int ReadIntProperty(Type t, object instance, string name)
    {
        var p = t.GetProperty(name, BindingFlags.Public | BindingFlags.Instance);
        p.Should().NotBeNull($"Selection result must expose a public '{name}' property.");
        p!.PropertyType.Should().Be(typeof(int), $"'{name}' must be an int.");
        return (int)p.GetValue(instance)!;
    }

    private sealed record EvidenceSnapshot(
        string RngContextId,
        string CandidatesSortedIdsHash,
        int PickedIndex,
        string PickedId);

    private static string ComputeSha256Hex(string value)
    {
        var bytes = Encoding.UTF8.GetBytes(value ?? string.Empty);
        var hash = SHA256.HashData(bytes);
        return Convert.ToHexString(hash).ToLowerInvariant();
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

    private sealed class FixedRng : IRandomNumberGenerator
    {
        public int NextInt(int minInclusive, int maxExclusive) => minInclusive;
        public double NextDouble() => 1.0;
    }

    private static async Task<GlobalRoundEvidence> RunStartNewGameAndCaptureGlobalRoundEvidenceAsync(int year, int month, int day)
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var rules = SanguoEconomyRules.Default;

        var players = new[]
        {
            new SanguoPlayer(playerId: "p1", money: 0m, positionIndex: 0, economyRules: rules),
            new SanguoPlayer(playerId: "p2", money: 0m, positionIndex: 0, economyRules: rules),
            new SanguoPlayer(playerId: "p3", money: 0m, positionIndex: 0, economyRules: rules),
            new SanguoPlayer(playerId: "p4", money: 0m, positionIndex: 0, economyRules: rules),
        };

        var boardState = new SanguoBoardState(players: players, citiesById: new Dictionary<string, City>(StringComparer.Ordinal));
        var treasury = new SanguoTreasury();

        var catalog = new SanguoRandomEventsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Events: new[]
            {
                new SanguoRandomEventCatalogEntry(
                    EventId: "drought",
                    NameKey: "event.drought.name",
                    DescriptionKey: "event.drought.desc",
                    EffectKind: "economyStepDelta",
                    MoneyDelta: null,
                    StepDelta: 1,
                    CooldownRounds: 0,
                    UniqueOnce: false),
            },
            EventPools: new[]
            {
                new SanguoRandomEventPoolCatalogEntry(PoolId: "global", EventIds: new[] { "drought" }),
                new SanguoRandomEventPoolCatalogEntry(PoolId: "default", EventIds: new[] { "drought" }),
            });

        var manager = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: boardState,
            treasury: treasury,
            rng: new FixedRng(),
            totalPositionsHint: 0,
            quarterEnvironmentEventTriggerChance: 0.0,
            quarterEnvironmentEventYieldMultiplier: 1.0m,
            randomEventsCatalog: catalog,
            globalEventIntervalTurns: 20,
            tileRandomEventPoolId: "default",
            globalRandomEventPoolId: "global");

        await manager.StartNewGameAsync(
            gameId: "g1",
            playerOrder: new[] { "p1", "p2", "p3", "p4" },
            year: year,
            month: month,
            day: day,
            correlationId: "c1",
            causationId: null);

        var applied = bus.Published.FirstOrDefault(e => e.Type == SanguoRandomEventApplied.EventType);
        applied.Should().NotBeNull();

        var data = (applied!.Data as JsonElementEventData)?.Value;
        data.HasValue.Should().BeTrue();
        if (!data.HasValue)
            throw new InvalidOperationException("Expected random_event.applied to contain JSON event data.");

        data.Value.TryGetProperty("RngContextId", out var rngContextId).Should().BeTrue();
        data.Value.TryGetProperty("CandidatesSortedIdsHash", out var hash).Should().BeTrue();
        data.Value.TryGetProperty("PickedIndex", out var pickedIndex).Should().BeTrue();
        data.Value.TryGetProperty("PickedId", out var pickedId).Should().BeTrue();

        return new GlobalRoundEvidence(
            RngContextId: rngContextId.GetString() ?? string.Empty,
            CandidatesSortedIdsHash: hash.GetString() ?? string.Empty,
            PickedIndex: pickedIndex.GetInt32(),
            PickedId: pickedId.GetString() ?? string.Empty);
    }

    private sealed record GlobalRoundEvidence(
        string RngContextId,
        string CandidatesSortedIdsHash,
        int PickedIndex,
        string PickedId);

    private static bool HasRngContextToken(DomainEvent evt, string token)
    {
        var data = (evt.Data as JsonElementEventData)?.Value;
        if (!data.HasValue)
            return false;

        if (!data.Value.TryGetProperty("RngContextId", out var rngContextId))
            return false;

        return (rngContextId.GetString() ?? string.Empty).Contains(token, StringComparison.Ordinal);
    }
}
