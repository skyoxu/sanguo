using Godot;

namespace Game.Godot.Examples.Screens;

public partial class DemoScreen : Control
{
    private Button _btnToast = default!;
    private Button _btnModal = default!;
    private Button _btnGoSettings = default!;

    private Control? _overlays;
    private Control? _toast;
    private Control? _modal;

    public override void _Ready()
    {
        _btnToast = GetNode<Button>("VBox/BtnToast");
        _btnModal = GetNode<Button>("VBox/BtnModal");
        _btnGoSettings = GetNode<Button>("VBox/BtnGoSettings");

        _btnToast.Pressed += OnToast;
        _btnModal.Pressed += OnModal;
        _btnGoSettings.Pressed += OnGoSettings;

        // Locate overlays container in Main scene
        _overlays = GetNodeOrNull<Control>("/root/Main/Overlays");

        // If Modal/Toast exist under this screen, reparent them under Overlays for proper layering
        var modalLocal = GetNodeOrNull<Control>("Modal");
        if (_overlays != null && modalLocal != null)
        {
            modalLocal.GetParent()?.RemoveChild(modalLocal);
            _overlays.AddChild(modalLocal);
            _modal = modalLocal;
        }
        var toastLocal = GetNodeOrNull<Control>("Toast");
        if (_overlays != null && toastLocal != null)
        {
            toastLocal.GetParent()?.RemoveChild(toastLocal);
            _overlays.AddChild(toastLocal);
            _toast = toastLocal;
        }

        // If not present, instantiate from examples and attach to Overlays
        if (_overlays != null && _modal == null)
        {
            var ps = ResourceLoader.Load<PackedScene>("res://Game.Godot/Examples/Components/Modal.tscn");
            if (ps != null) { _modal = ps.Instantiate<Control>(); _overlays.AddChild(_modal); }
        }
        if (_overlays != null && _toast == null)
        {
            var ps = ResourceLoader.Load<PackedScene>("res://Game.Godot/Examples/Components/Toast.tscn");
            if (ps != null) { _toast = ps.Instantiate<Control>(); _overlays.AddChild(_toast); }
        }
    }

    private void OnToast()
    {
        var node = _toast ?? GetNodeOrNull<Control>("/root/Main/Overlays/Toast");
        if (node != null && node.HasMethod("ShowToast"))
            node.Call("ShowToast", "Hello from Toast!", 2.0);
    }

    private void OnModal()
    {
        var node = _modal ?? GetNodeOrNull<Control>("/root/Main/Overlays/Modal");
        if (node != null && node.HasMethod("Open"))
            node.Call("Open", "Are you ready?");
    }

    private void OnGoSettings()
    {
        var nav = GetNodeOrNull<Node>("/root/Main/ScreenNavigator");
        if (nav != null && nav.HasMethod("SwitchTo"))
            nav.Call("SwitchTo", "res://Game.Godot/Scenes/Screens/SettingsScreen.tscn");
    }
}
