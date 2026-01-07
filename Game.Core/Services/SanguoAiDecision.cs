namespace Game.Core.Services;

public enum SanguoAiDecisionType
{
    RollDice,
    Skip,
}

public sealed record SanguoAiDecision(
    SanguoAiDecisionType DecisionType,
    string DecisionNode,
    string FromState,
    string ToState,
    string Reason);
