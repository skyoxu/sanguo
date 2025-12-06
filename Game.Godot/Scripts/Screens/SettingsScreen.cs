using Godot;

namespace Game.Godot.Scripts.Screens;

public partial class SettingsScreen : Control
{
    public override void _Ready()
    {
        GD.Print("[SettingsScreen] _Ready");
        var back = GetNodeOrNull<Button>("Center/VBox/Back");
        if (back != null)
            back.Pressed += OnBack;
    }

    public void Enter() => GD.Print("[SettingsScreen] Enter");
    public void Exit()  => GD.Print("[SettingsScreen] Exit");

    private void OnBack()
    {
        var nav = GetNodeOrNull<Node>("/root/Main/ScreenNavigator");
        if (nav != null && nav.HasMethod("SwitchTo"))
            nav.Call("SwitchTo", "res://Game.Godot/Scenes/Screens/StartScreen.tscn");
    }
}
