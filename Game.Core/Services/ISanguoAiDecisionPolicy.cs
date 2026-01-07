using Game.Core.Domain;

namespace Game.Core.Services;

public interface ISanguoAiDecisionPolicy
{
    SanguoAiDecision Decide(ISanguoPlayerView self);
}
