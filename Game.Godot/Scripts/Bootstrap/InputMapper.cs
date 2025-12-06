using Godot;

namespace Game.Godot.Scripts.Bootstrap;

public partial class InputMapper : Node
{
    public override void _Ready()
    {
        Ensure("ui_accept", Key.Enter, Key.Space);
        Ensure("ui_cancel", Key.Escape);
        Ensure("ui_up", Key.Up);
        Ensure("ui_down", Key.Down);
        Ensure("ui_left", Key.Left);
        Ensure("ui_right", Key.Right);
    }

    private void Ensure(string action, params Key[] keys)
    {
        if (!InputMap.HasAction(action))
            InputMap.AddAction(action);
        // do not duplicate events if already added
        foreach (var k in keys)
        {
            var ev = new InputEventKey { Keycode = k };
            InputMap.ActionAddEvent(action, ev);
        }
    }
}
