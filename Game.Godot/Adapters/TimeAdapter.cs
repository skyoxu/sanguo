using Godot;
using Game.Core.Ports;

namespace Game.Godot.Adapters;

public partial class TimeAdapter : Node, ITime
{
    public double DeltaSeconds => GetProcessDeltaTime();
}

