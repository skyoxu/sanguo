using Game.Core.Ports;

namespace Game.Core.Tests.Fakes;

public class FakeInput : IInput
{
    private readonly HashSet<string> _pressed = new();

    public bool IsPressed(string action) => _pressed.Contains(action);

    public void SetPressed(string action, bool pressed)
    {
        if (pressed) _pressed.Add(action); else _pressed.Remove(action);
    }

    public float GetAxis(string negativeAction, string positiveAction)
    {
        var v = 0f;
        if (IsPressed(negativeAction)) v -= 1f;
        if (IsPressed(positiveAction)) v += 1f;
        return v;
    }
}

