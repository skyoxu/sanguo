using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task61AiDeterministicStrategyTests
{
    // ACC:T61.1
    [Fact]
    public async Task GivenSameContextAndCandidates_WhenDecidingTwice_ThenAuditFieldsAndPickAreDeterministic()
    {
        var bus = new CapturingEventBus();
        var samples = new[]
        {
            new PublishScenario("BeforeRoll", new SanguoAiDeterministicDecisionApi.DecisionCandidatesContext(CanRoll: true, CanUseCard: true)),
            new PublishScenario("ResolveLanding", new SanguoAiDeterministicDecisionApi.DecisionCandidatesContext(CanBuyLand: true, CanBuild: true, CanUseCard: true)),
            new PublishScenario("Discard", new SanguoAiDeterministicDecisionApi.DecisionCandidatesContext(CardsToDiscard: 2)),
        };

        foreach (var sample in samples)
        {
            var rngContextId = $"rng-ctx-001:{sample.DecisionPoint}";
            var candidates = SanguoAiDeterministicDecisionApi.GetCandidatesForActor("Ai", sample.DecisionPoint, sample.Context);
            candidates.Should().NotBeNullOrEmpty();

            var d1 = SanguoAiDeterministicDecisionApi.MakeDecision(sample.DecisionPoint, rngContextId, candidates);
            var d2 = SanguoAiDeterministicDecisionApi.MakeDecision(sample.DecisionPoint, rngContextId, candidates.Reverse().ToArray());

            d1.RngContextId.Should().Be(rngContextId);
            d2.RngContextId.Should().Be(rngContextId);

            d1.CandidatesSortedIdsHash.Should().NotBeNullOrWhiteSpace();
            d1.PickedId.Should().NotBeNullOrWhiteSpace();
            d1.PickedIndex.Should().BeGreaterOrEqualTo(0);

            d1.CandidatesSortedIdsHash.Should().Be(d2.CandidatesSortedIdsHash);
            d1.PickedId.Should().Be(d2.PickedId);
            d1.PickedIndex.Should().Be(d2.PickedIndex);

            var expectedHash = SanguoDeterminism.ComputeCandidatesSortedIdsHash(candidates);
            d1.CandidatesSortedIdsHash.Should().Be(expectedHash);
            d1.PickedIndex.Should().Be(0);
            candidates[0].Should().Be(d1.PickedId);

            var beforeCount = bus.Published.Count;
            await SanguoAiDeterministicDecisionApi.PublishDecisionAsync(bus, d1);
            await SanguoAiDeterministicDecisionApi.PublishDecisionAsync(bus, d2);

            bus.Published.Count.Should().Be(beforeCount + 2, "each decision must publish exactly one DomainEvent");

            var published = bus.Published.Skip(beforeCount).Take(2).ToArray();
            published.Should().HaveCount(2);
            foreach (var evt in published)
            {
                evt.Type.Should().Be(SanguoAiDecisionMade.EventType);
                var audit = ReadDecisionAudit(evt);
                audit.RngContextId.Should().Be(rngContextId);
                audit.CandidatesSortedIdsHash.Should().Be(expectedHash);
                audit.PickedIndex.Should().Be(0);
                audit.PickedId.Should().Be(d1.PickedId);
            }
        }
    }

    // ACC:T61.2
    [Fact]
    public async Task GivenAtLeastOneLegalOption_WhenDecidingConcurrently_ThenAlwaysPicksFirstCandidateInDeterministicOrder()
    {
        var rngContextId = "rng-ctx-002";

        var scenarios = new[]
        {
            new CandidateScenario(
                DecisionPoint: "BeforeRoll",
                Context: new SanguoAiDeterministicDecisionApi.DecisionCandidatesContext(CanRoll: true, CanUseCard: true),
                MustContain: new[] { "roll", "use_card" },
                ExpectedPick: "roll"),
            new CandidateScenario(
                DecisionPoint: "ResolveLanding",
                Context: new SanguoAiDeterministicDecisionApi.DecisionCandidatesContext(CanBuyLand: true, CanBuild: true, CanUseCard: true),
                MustContain: new[] { "buy_land", "build", "use_card" },
                ExpectedPick: "build"),
            new CandidateScenario(
                DecisionPoint: "Discard",
                Context: new SanguoAiDeterministicDecisionApi.DecisionCandidatesContext(CardsToDiscard: 2),
                MustContain: new[] { "discard_card_1", "discard_card_2" },
                ExpectedPick: "discard_card_1"),

            // Ensure "buy_land" is selectable when it becomes the first legal option.
            new CandidateScenario(
                DecisionPoint: "ResolveLanding",
                Context: new SanguoAiDeterministicDecisionApi.DecisionCandidatesContext(CanBuyLand: true, CanBuild: false, CanUseCard: false),
                MustContain: new[] { "buy_land" },
                ExpectedPick: "buy_land"),

            // Ensure "use_card" is selectable when it becomes the first legal option.
            new CandidateScenario(
                DecisionPoint: "BeforeRoll",
                Context: new SanguoAiDeterministicDecisionApi.DecisionCandidatesContext(CanRoll: false, CanUseCard: true),
                MustContain: new[] { "use_card" },
                ExpectedPick: "use_card"),
        };

        foreach (var scenario in scenarios)
        {
            var playerCandidates = SanguoAiDeterministicDecisionApi.GetCandidatesForActor("Player", scenario.DecisionPoint, scenario.Context);
            var aiCandidates = SanguoAiDeterministicDecisionApi.GetCandidatesForActor("Ai", scenario.DecisionPoint, scenario.Context);

            playerCandidates.Should().NotBeNullOrEmpty();
            aiCandidates.Should().Equal(playerCandidates, "AI must reuse the same legality checks and candidate ordering as the player");

            aiCandidates.Should().Contain(scenario.MustContain);
            aiCandidates[0].Should().Be(scenario.ExpectedPick);
            var expectedPick = scenario.ExpectedPick;

            var bus = new CapturingEventBus();
            var tasks = Enumerable.Range(0, 32)
                .Select(i =>
                {
                    var order = (i % 2 == 0) ? aiCandidates.ToArray() : aiCandidates.Reverse().ToArray();
                    return Task.Run(async () =>
                    {
                        var decision = SanguoAiDeterministicDecisionApi.MakeDecision(scenario.DecisionPoint, rngContextId, order);
                        await SanguoAiDeterministicDecisionApi.PublishDecisionAsync(bus, decision);
                        return decision;
                    });
                })
                .ToArray();

            var results = await Task.WhenAll(tasks);

            results.Should().NotBeNullOrEmpty();
            results.Select(r => r.RngContextId).Distinct().Should().ContainSingle().Which.Should().Be(rngContextId);
            results.Select(r => r.CandidatesSortedIdsHash).Distinct().Should().ContainSingle();
            results.Select(r => r.PickedId).Distinct().Should().ContainSingle().Which.Should().Be(expectedPick);

            foreach (var r in results)
            {
                r.PickedIndex.Should().Be(0);
            }

            bus.Published.Should().HaveCount(32);
            foreach (var evt in bus.Published)
            {
                var audit = ReadDecisionAudit(evt);
                audit.RngContextId.Should().Be(rngContextId);
                audit.PickedId.Should().Be(expectedPick);
                audit.PickedIndex.Should().Be(0);
                audit.CandidatesSortedIdsHash.Should().NotBeNullOrWhiteSpace();
            }
        }
    }

    // ACC:T61.3
    [Fact]
    public void GivenElimination_WhenEvaluatingGameOverTiming_ThenPlayerIsImmediateAndAiIsAfterTurnAdvanced()
    {
        SanguoGameOverTimingPolicy.GetGameOverCheckPhaseForElimination("Player").Should().Be("Immediate");
        SanguoGameOverTimingPolicy.GetGameOverCheckPhaseForElimination("Ai").Should().Be("AfterTurnAdvanced");
    }

    // ACC:T61.4
    [Fact]
    public void GivenTurnFlow_WhenComparingAiAndPlayerDecisionPoints_ThenSequencesMatchAndContainRequiredPoints()
    {
        var player = SanguoTurnDecisionPoints.GetDecisionPointSequence("Player");
        var ai = SanguoTurnDecisionPoints.GetDecisionPointSequence("Ai");

        player.Should().NotBeNullOrEmpty();
        ai.Should().Equal(player);

        RequireInOrder(player, "BeforeRoll", "ResolveLanding", "Discard");
    }

    [Fact]
    public void GivenNoLegalOptions_WhenDeciding_ThenThrowsArgumentException()
    {
        var act = () => SanguoAiDeterministicDecisionApi.MakeDecision("BeforeRoll", "rng-ctx-empty", Array.Empty<string>());
        act.Should().Throw<ArgumentException>();
    }

    private static void RequireInOrder(IReadOnlyList<string> sequence, params string[] requiredInOrder)
    {
        var start = -1;
        foreach (var required in requiredInOrder)
        {
            var idx = IndexOf(sequence, required);
            idx.Should().BeGreaterThan(-1, "sequence should contain decision point '{0}'", required);
            idx.Should().BeGreaterThan(start, "decision points should preserve order: {0}", string.Join(" -> ", requiredInOrder));
            start = idx;
        }
    }

    private static int IndexOf(IReadOnlyList<string> sequence, string value)
    {
        for (var i = 0; i < sequence.Count; i++)
        {
            if (string.Equals(sequence[i], value, StringComparison.Ordinal))
            {
                return i;
            }
        }

        return -1;
    }

    private static DecisionAudit ReadDecisionAudit(DomainEvent evt)
    {
        evt.Type.Should().Be(SanguoAiDecisionMade.EventType);
        evt.Data.Should().BeOfType<JsonElementEventData>();
        var root = ((JsonElementEventData)evt.Data!).Value;

        return new DecisionAudit(
            RngContextId: ReadString(root, "RngContextId"),
            CandidatesSortedIdsHash: ReadString(root, "CandidatesSortedIdsHash"),
            PickedIndex: ReadInt(root, "PickedIndex"),
            PickedId: ReadString(root, "PickedId"));
    }

    private static string ReadString(JsonElement root, string name)
    {
        root.TryGetProperty(name, out var p).Should().BeTrue($"Expected JSON property '{name}'");
        p.ValueKind.Should().Be(JsonValueKind.String);
        return p.GetString() ?? string.Empty;
    }

    private static int ReadInt(JsonElement root, string name)
    {
        root.TryGetProperty(name, out var p).Should().BeTrue($"Expected JSON property '{name}'");
        p.ValueKind.Should().Be(JsonValueKind.Number);
        p.TryGetInt32(out var v).Should().BeTrue();
        return v;
    }

    private sealed record PublishScenario(string DecisionPoint, SanguoAiDeterministicDecisionApi.DecisionCandidatesContext Context);

    private sealed record CandidateScenario(
        string DecisionPoint,
        SanguoAiDeterministicDecisionApi.DecisionCandidatesContext Context,
        string[] MustContain,
        string ExpectedPick);

    private sealed record DecisionAudit(string RngContextId, string CandidatesSortedIdsHash, int PickedIndex, string PickedId);

    private sealed class CapturingEventBus : IEventBus
    {
        public List<DomainEvent> Published { get; } = new();
        private readonly object _gate = new();

        public Task PublishAsync(DomainEvent evt)
        {
            lock (_gate)
            {
                Published.Add(evt);
            }
            return Task.CompletedTask;
        }

        public IDisposable Subscribe(Func<DomainEvent, Task> handler) => throw new NotSupportedException();
    }
}
