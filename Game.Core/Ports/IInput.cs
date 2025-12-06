namespace Game.Core.Ports;

public interface IInput
{
    bool IsPressed(string action);
    float GetAxis(string negativeAction, string positiveAction);
}

