namespace Game.Core.State;

public enum GameFlowState
{
    Initialized,
    Running,
    Paused,
    GameOver
}

public class GameStateMachine
{
    public GameFlowState State { get; private set; } = GameFlowState.Initialized;

    public event Action<GameFlowState, GameFlowState>? OnTransition;

    private void Transition(GameFlowState next)
    {
        var prev = State;
        State = next;
        OnTransition?.Invoke(prev, next);
    }

    public bool Start()
    {
        if (State != GameFlowState.Initialized) return false;
        Transition(GameFlowState.Running);
        return true;
    }

    public bool Pause()
    {
        if (State != GameFlowState.Running) return false;
        Transition(GameFlowState.Paused);
        return true;
    }

    public bool Resume()
    {
        if (State != GameFlowState.Paused) return false;
        Transition(GameFlowState.Running);
        return true;
    }

    public bool End()
    {
        if (State == GameFlowState.GameOver) return false;
        Transition(GameFlowState.GameOver);
        return true;
    }
}

