using System;
using System.Collections.Generic;
using System.Linq;
using FluentAssertions;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task25AiTests
{
    // ACC:T25.1
    [Fact]
    [Trait("acceptance", "ACC:T25.1")]
    public void ShouldNotReferenceGodotAssemblies_WhenUsingAiPoliciesInGameCore()
    {
        var referenced = typeof(DefaultSanguoAiDecisionPolicy).Assembly.GetReferencedAssemblies();
        referenced.Should().NotContain(a => a.Name != null && a.Name.StartsWith("Godot", StringComparison.OrdinalIgnoreCase));
    }

    // ACC:T25.2
    [Fact]
    [Trait("acceptance", "ACC:T25.2")]
    public void ShouldBeDeterministicAndDocumentBaselineLimitations_WhenUsingDefaultPolicy()
    {
        var viewRich = new FakePlayerView(
            playerId: "ai-1",
            money: Money.FromMajorUnits(500),
            positionIndex: 7,
            ownedCityIds: new[] { "c1" },
            isEliminated: false);

        var viewPoor = new FakePlayerView(
            playerId: "ai-1",
            money: Money.Zero,
            positionIndex: 0,
            ownedCityIds: Array.Empty<string>(),
            isEliminated: false);

        var policyA = new DefaultSanguoAiDecisionPolicy();
        var seqA = new[]
        {
            policyA.Decide(viewRich),
            policyA.Decide(viewRich),
            policyA.Decide(viewRich),
        };
        seqA.Should().OnlyContain(d => d.DecisionNode == "sanguo.ai.decision.roll_unless_blocked.v1");
        seqA.Should().OnlyContain(d => d.Reason == "rules_allow_roll");

        var policyB = new DefaultSanguoAiDecisionPolicy();
        var seqB = new[]
        {
            policyB.Decide(viewPoor),
            policyB.Decide(viewPoor),
            policyB.Decide(viewPoor),
        };

        seqA.Select(d => d.DecisionType).Should().Equal(
            SanguoAiDecisionType.RollDice,
            SanguoAiDecisionType.RollDice,
            SanguoAiDecisionType.RollDice);

        seqA.Should().Equal(seqB, "the baseline policy is expected to ignore Money/Position/OwnedCityIds and be reproducible for the same PlayerId");
    }

    // ACC:T25.3
    [Fact]
    [Trait("acceptance", "ACC:T25.3")]
    public void ShouldChooseMoreAggressiveAction_WhenUsingOptimizedPolicy()
    {
        var view = new FakePlayerView(
            playerId: "ai-1",
            money: Money.FromMajorUnits(200),
            positionIndex: 0,
            ownedCityIds: Array.Empty<string>(),
            isEliminated: false);

        var baseline = new DefaultSanguoAiDecisionPolicy();
        _ = baseline.Decide(view);
        var baselineSecond = baseline.Decide(view);
        baselineSecond.DecisionType.Should().Be(SanguoAiDecisionType.RollDice);
        baselineSecond.DecisionNode.Should().Be("sanguo.ai.decision.roll_unless_blocked.v1");
        baselineSecond.Reason.Should().Be("rules_allow_roll");

        var optimized = new OptimizedSanguoAiDecisionPolicy();
        _ = optimized.Decide(view);
        var optimizedSecond = optimized.Decide(view);

        optimizedSecond.DecisionType.Should().Be(
            SanguoAiDecisionType.RollDice,
            "the optimized policy should avoid skipping in this regression case");
        optimizedSecond.DecisionNode.Should().Be("sanguo.ai.decision.optimized.v1");
        optimizedSecond.Reason.Should().Be("money_positive_never_skip");

        var viewLowMoney = new FakePlayerView(
            playerId: "ai-1",
            money: Money.Zero,
            positionIndex: 0,
            ownedCityIds: Array.Empty<string>(),
            isEliminated: false);

        optimized.Decide(viewLowMoney).Reason.Should().Be("money_zero_never_skip");
    }

    // ACC:T25.4
    [Fact]
    [Trait("acceptance", "ACC:T25.4")]
    public void ShouldSkip_WhenOptimizedPolicyAndPlayerIsEliminated()
    {
        var view = new FakePlayerView(
            playerId: "ai-1",
            money: Money.FromMajorUnits(200),
            positionIndex: 0,
            ownedCityIds: Array.Empty<string>(),
            isEliminated: true);

        var baseline = new DefaultSanguoAiDecisionPolicy();
        var baselineDecision = baseline.Decide(view);
        baselineDecision.DecisionType.Should().Be(SanguoAiDecisionType.Skip);
        baselineDecision.DecisionNode.Should().Be("sanguo.ai.decision.eliminated.v1");
        baselineDecision.Reason.Should().Be("self_is_eliminated");

        var policy = new OptimizedSanguoAiDecisionPolicy();
        var decision = policy.Decide(view);

        decision.DecisionType.Should().Be(SanguoAiDecisionType.Skip);
        decision.Reason.Should().Be("self_is_eliminated");
    }

    private sealed class FakePlayerView : ISanguoPlayerView
    {
        public FakePlayerView(
            string playerId,
            Money money,
            int positionIndex,
            IReadOnlyCollection<string> ownedCityIds,
            bool isEliminated)
        {
            PlayerId = playerId ?? throw new ArgumentNullException(nameof(playerId));
            Money = money;
            PositionIndex = positionIndex;
            OwnedCityIds = ownedCityIds ?? throw new ArgumentNullException(nameof(ownedCityIds));
            IsEliminated = isEliminated;
        }

        public string PlayerId { get; }
        public Money Money { get; }
        public int PositionIndex { get; }
        public IReadOnlyCollection<string> OwnedCityIds { get; }
        public bool IsEliminated { get; }
    }
}
