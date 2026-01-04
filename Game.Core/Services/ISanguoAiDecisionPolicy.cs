using Game.Core.Domain;

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

public interface ISanguoAiDecisionPolicy
{
    SanguoAiDecision Decide(ISanguoPlayerView self);
}

public sealed class DefaultSanguoAiDecisionPolicy : ISanguoAiDecisionPolicy
{
    private readonly SanguoAiDecisionStateMachine _machine = new();

    public SanguoAiDecision Decide(ISanguoPlayerView self)
    {
        ArgumentNullException.ThrowIfNull(self, nameof(self));
        return _machine.Decide(self);
    }
}

internal sealed class SanguoAiDecisionStateMachine
{
    private const string RollSkipNode = "sanguo.ai.decision.roll_skip.v1";
    private const string EliminatedNode = "sanguo.ai.decision.eliminated.v1";
    private readonly Dictionary<string, SanguoAiState> _stateByPlayerId = new(StringComparer.Ordinal);
    private readonly object _gate = new();

    public SanguoAiDecision Decide(ISanguoPlayerView self)
    {
        // Explicit state machine (Subtask 17.2): decisions are not a single hard-coded action.
        if (self.IsEliminated)
        {
            lock (_gate)
            {
                _stateByPlayerId[self.PlayerId] = SanguoAiState.Eliminated;
            }
            return new SanguoAiDecision(
                DecisionType: SanguoAiDecisionType.Skip,
                DecisionNode: EliminatedNode,
                FromState: SanguoAiState.Eliminated.ToString(),
                ToState: SanguoAiState.Eliminated.ToString(),
                Reason: "self_is_eliminated");
        }

        SanguoAiState state;
        SanguoAiState nextState;
        lock (_gate)
        {
            if (!_stateByPlayerId.TryGetValue(self.PlayerId, out state))
                state = SanguoAiState.RollDice;

            // Deterministic transition: alternate between RollDice and Skip per AI player.
            nextState = state == SanguoAiState.RollDice ? SanguoAiState.Skip : SanguoAiState.RollDice;
            _stateByPlayerId[self.PlayerId] = nextState;
        }

        var decisionType = state == SanguoAiState.Skip ? SanguoAiDecisionType.Skip : SanguoAiDecisionType.RollDice;
        return new SanguoAiDecision(
            DecisionType: decisionType,
            DecisionNode: RollSkipNode,
            FromState: state.ToString(),
            ToState: nextState.ToString(),
            Reason: "alternate_per_player");
    }
}

internal enum SanguoAiState
{
    RollDice,
    Skip,
    Eliminated,
}
