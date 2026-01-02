using Game.Core.Domain;

namespace Game.Core.Services;

public enum SanguoAiDecisionType
{
    RollDice,
    Skip,
}

public sealed record SanguoAiDecision(SanguoAiDecisionType DecisionType);

public interface ISanguoAiDecisionPolicy
{
    SanguoAiDecision Decide(ISanguoPlayerView self);
}

public sealed class DefaultSanguoAiDecisionPolicy : ISanguoAiDecisionPolicy
{
    public SanguoAiDecision Decide(ISanguoPlayerView self)
    {
        ArgumentNullException.ThrowIfNull(self, nameof(self));
        if (self.IsEliminated)
            return new SanguoAiDecision(SanguoAiDecisionType.Skip);

        return new SanguoAiDecision(SanguoAiDecisionType.RollDice);
    }
}

