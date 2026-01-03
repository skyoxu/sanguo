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
    private readonly SanguoAiDecisionStateMachine _machine = new();

    public SanguoAiDecision Decide(ISanguoPlayerView self)
    {
        ArgumentNullException.ThrowIfNull(self, nameof(self));
        return _machine.Decide(self);
    }
}

internal sealed class SanguoAiDecisionStateMachine
{
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
            return new SanguoAiDecision(SanguoAiDecisionType.Skip);
        }

        SanguoAiState state;
        lock (_gate)
        {
            if (!_stateByPlayerId.TryGetValue(self.PlayerId, out state))
                state = SanguoAiState.RollDice;

            // Deterministic transition: alternate between RollDice and Skip per AI player.
            _stateByPlayerId[self.PlayerId] = state == SanguoAiState.RollDice ? SanguoAiState.Skip : SanguoAiState.RollDice;
        }

        return state == SanguoAiState.Skip
            ? new SanguoAiDecision(SanguoAiDecisionType.Skip)
            : new SanguoAiDecision(SanguoAiDecisionType.RollDice);
    }
}

internal enum SanguoAiState
{
    RollDice,
    Skip,
    Eliminated,
}
