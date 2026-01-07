using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;

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

        // Minimal, deterministic heuristic: avoid the "alternate_per_player" skip behavior by always rolling dice,
        // while still making the policy input-sensitive (so it can be tuned and regression-tested).
        var reason = self.Money <= Money.Zero ? "money_zero_never_skip" : "money_positive_never_skip";

        return new SanguoAiDecision(
            DecisionType: SanguoAiDecisionType.RollDice,
            DecisionNode: OptimizedNode,
            FromState: SanguoAiState.RollDice.ToString(),
            ToState: SanguoAiState.RollDice.ToString(),
            Reason: reason);
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
