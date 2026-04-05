using Godot;

namespace Game.Godot.Scripts.UI;

/// <summary>
/// Task 68 integration closure gate.
/// Closure is complete only when both split-task evidences are present.
/// </summary>
public partial class HudExplainabilityIntegrationClosureGate : RefCounted
{
    public bool Evaluate(bool hasTask81Evidence, bool hasTask82Evidence)
    {
        return hasTask81Evidence && hasTask82Evidence;
    }
}
