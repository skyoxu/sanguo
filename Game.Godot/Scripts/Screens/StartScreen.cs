using Godot;

namespace Game.Godot.Scripts.Screens;

public partial class StartScreen : Control
{
    public override void _Ready()
    {
        // Minimal placeholder screen; add your UI here.
        GD.Print("[StartScreen] _Ready");
    }

    // Optional lifecycle hooks recognized by ScreenNavigator
    public void Enter()
    {
        GD.Print("[StartScreen] Enter");
    }

    public void Exit()
    {
        GD.Print("[StartScreen] Exit");
    }
}
