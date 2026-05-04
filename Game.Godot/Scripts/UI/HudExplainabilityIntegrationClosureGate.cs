using Godot;

namespace Game.Godot.Scripts.UI;

/// <summary>
/// Shared HUD integration closure gate used by explainability acceptance slices.
/// Closure is complete only when both prerequisite evidence tracks are present.
/// </summary>
public partial class HudExplainabilityIntegrationClosureGate : RefCounted
{
    public bool Evaluate(bool hasTask81Evidence, bool hasTask82Evidence)
    {
        return hasTask81Evidence && hasTask82Evidence;
    }
}
