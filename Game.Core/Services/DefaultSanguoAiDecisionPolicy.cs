using Game.Core.Domain;

namespace Game.Core.Services;

public sealed class DefaultSanguoAiDecisionPolicy : ISanguoAiDecisionPolicy
{
    public SanguoAiDecision Decide(ISanguoPlayerView self)
    {
        ArgumentNullException.ThrowIfNull(self, nameof(self));
        const string rollNode = "sanguo.ai.decision.roll_unless_blocked.v1";
        const string eliminatedNode = "sanguo.ai.decision.eliminated.v1";

        if (self.IsEliminated)
        {
            return new SanguoAiDecision(
                DecisionType: SanguoAiDecisionType.Skip,
                DecisionNode: eliminatedNode,
                FromState: SanguoAiState.Eliminated.ToString(),
                ToState: SanguoAiState.Eliminated.ToString(),
                Reason: "self_is_eliminated");
        }

        return new SanguoAiDecision(
            DecisionType: SanguoAiDecisionType.RollDice,
            DecisionNode: rollNode,
            FromState: SanguoAiState.RollDice.ToString(),
            ToState: SanguoAiState.RollDice.ToString(),
            Reason: "rules_allow_roll");
    }
}
