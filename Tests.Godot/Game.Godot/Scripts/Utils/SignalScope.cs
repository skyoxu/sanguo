using Godot;

namespace Game.Godot.Scripts.Utils;

public sealed class SignalScope : System.IDisposable
{
    private readonly System.Collections.Generic.List<(GodotObject Emitter, StringName Signal, Callable Callable)> _connections = new();

    public void Connect(GodotObject emitter, StringName signal, Callable callable)
    {
        if (emitter == null) return;
        emitter.Connect(signal, callable);
        _connections.Add((emitter, signal, callable));
    }

    public void DisconnectAll()
    {
        foreach (var (emitter, signal, callable) in _connections)
        {
            if (GodotObject.IsInstanceValid(emitter))
            {
                try { emitter.Disconnect(signal, callable); } catch { }
            }
        }
        _connections.Clear();
    }

    public void Dispose() => DisconnectAll();
}

