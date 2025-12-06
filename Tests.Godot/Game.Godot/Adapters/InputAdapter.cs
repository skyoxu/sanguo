using Godot;
using Game.Core.Ports;

namespace Game.Godot.Adapters;

public partial class InputAdapter : Node, IInput
{
    public bool IsPressed(string action) => Input.IsActionPressed(action);

    public float GetAxis(string negativeAction, string positiveAction)
        => Input.GetAxis(negativeAction, positiveAction);
}

