using Godot;

namespace Game.Godot.Scripts.Utils;

public partial class NodeWithSignals : Node
{
    protected readonly SignalScope Signals = new();

    public override void _ExitTree()
    {
        Signals.Dispose();
        base._ExitTree();
    }
}

