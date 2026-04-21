using System.Collections.Generic;
using System.Linq;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task102BossPressureIntegrationPackTests
{
    // ACC:T102.1
    [Fact]
    [Trait("acceptance", "ACC:T102.1")]
    public void ShouldCloseIntegration_WhenTask133AndTask134EvidenceArePresentAndNoAdditionalImplementationIsRequired()
    {
        var bossDiceOutcomes = new[] { 2, 4, 5, 6, 6 };
        var outcome = CurrentTask102IntegrationPack.Evaluate(
            bossDiceOutcomes,
            hasTask133Evidence: true,
            hasTask134Evidence: true,
            additionalImplementationRequired: false);

        outcome.EliteAttackCount.Should().Be(3, "Task 133 evidence must resolve elite outcomes (>=5) deterministically.");
        outcome.ExplainPayload.Should().HaveCount(2);
        outcome.ExplainPayload.Should().ContainSingle(item =>
            item.Source == "elite_attack_pressure"
            && item.Value == outcome.EliteAttackCount
            && item.Duration == 2);
        outcome.IsClosureComplete.Should().BeTrue("Task 102 closes only when split evidence from tasks 133 and 134 is both present.");
    }

    [Theory]
    [InlineData(false, true)]
    [InlineData(true, false)]
    [InlineData(false, false)]
    public void ShouldKeepIntegrationOpen_WhenAnySplitEvidenceIsMissing(
        bool hasTask133Evidence,
        bool hasTask134Evidence)
    {
        var bossDiceOutcomes = new[] { 2, 4, 5, 6, 6 };
        var outcome = CurrentTask102IntegrationPack.Evaluate(
            bossDiceOutcomes,
            hasTask133Evidence,
            hasTask134Evidence,
            additionalImplementationRequired: false);

        outcome.IsClosureComplete.Should().BeFalse("Task 102 acceptance requires split evidence from both task 133 and task 134.");
    }

    [Fact]
    public void ShouldKeepIntegrationOpen_WhenAdditionalImplementationIsStillRequired()
    {
        var bossDiceOutcomes = new[] { 2, 4, 5, 6, 6 };
        var outcome = CurrentTask102IntegrationPack.Evaluate(
            bossDiceOutcomes,
            hasTask133Evidence: true,
            hasTask134Evidence: true,
            additionalImplementationRequired: true);

        outcome.IsClosureComplete.Should().BeFalse(
            "Task 102 is a closure-only integration pack and must not close when additional implementation is still required.");
    }

    private sealed record IntegrationOutcome(
        int EliteAttackCount,
        IReadOnlyList<BossPressureExplainPayloadItem> ExplainPayload,
        bool IsClosureComplete);

    private static class CurrentTask102IntegrationPack
    {
        public static IntegrationOutcome Evaluate(
            IReadOnlyList<int> bossDiceOutcomes,
            bool hasTask133Evidence,
            bool hasTask134Evidence,
            bool additionalImplementationRequired)
        {
            var eliteAttackCount = BossEliteAttackPressureResolver.ResolveEliteAttackCount(bossDiceOutcomes);
            var explainPayload = BossPressureExplainPayloadMapper.Map(new[]
            {
                new BossPressureExplainPayloadInput(
                    Source: "base_boss_pressure",
                    Value: 1,
                    Duration: 1,
                    FromDelayStacking: false),
                new BossPressureExplainPayloadInput(
                    Source: "elite_attack_pressure",
                    Value: eliteAttackCount,
                    Duration: 2,
                    FromDelayStacking: true),
            });

            var explainPayloadMatchesResolver = explainPayload.Any(item =>
                item.Source == "elite_attack_pressure"
                && item.Value == eliteAttackCount
                && item.Duration == 2);

            return new IntegrationOutcome(
                EliteAttackCount: eliteAttackCount,
                ExplainPayload: explainPayload,
                IsClosureComplete: hasTask133Evidence
                    && hasTask134Evidence
                    && !additionalImplementationRequired
                    && explainPayloadMatchesResolver);
        }
    }
}
