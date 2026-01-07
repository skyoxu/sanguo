using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;

namespace Game.Core.Services;

/// <summary>
/// Optimized AI policy (Task 25): a more aggressive baseline than <see cref="DefaultSanguoAiDecisionPolicy"/>.
/// </summary>
public sealed class OptimizedSanguoAiDecisionPolicy : ISanguoAiDecisionPolicy
{
    private const string OptimizedNode = "sanguo.ai.decision.optimized.v1";

    public SanguoAiDecision Decide(ISanguoPlayerView self)
    {
        ArgumentNullException.ThrowIfNull(self, nameof(self));

        if (self.IsEliminated)
        {
            return new SanguoAiDecision(
                DecisionType: SanguoAiDecisionType.Skip,
                DecisionNode: OptimizedNode,
                FromState: SanguoAiState.Eliminated.ToString(),
                ToState: SanguoAiState.Eliminated.ToString(),
                Reason: "self_is_eliminated");
        }

        var reason = self.Money <= Money.Zero ? "money_zero_never_skip" : "money_positive_never_skip";

        return new SanguoAiDecision(
            DecisionType: SanguoAiDecisionType.RollDice,
            DecisionNode: OptimizedNode,
            FromState: SanguoAiState.RollDice.ToString(),
            ToState: SanguoAiState.RollDice.ToString(),
            Reason: reason);
    }
}
