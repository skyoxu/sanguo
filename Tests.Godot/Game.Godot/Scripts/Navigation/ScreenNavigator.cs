using Godot;

namespace Game.Godot.Scripts.Navigation;

public partial class ScreenNavigator : Node
{
    [Export] public NodePath ScreenRootPath { get; set; } = new NodePath("../ScreenRoot");
    [Export] public NodePath OverlaysPath { get; set; } = new NodePath("../Overlays");
    [Export] public bool UseFadeTransition { get; set; } = true;
    [Export] public float FadeDurationSec { get; set; } = 0.25f;

    private Control? _root;
    private Control? _overlays;
    private Control? _current;
    private bool _busy;

    public override void _Ready()
    {
        _root = GetNodeOrNull<Control>(ScreenRootPath);
        if (_root == null)
        {
            GD.PushWarning("[Navigator] ScreenRoot not found; navigation disabled.");
        }
        _overlays = GetNodeOrNull<Control>(OverlaysPath);
    }

    public bool SwitchTo(string scenePath)
    {
        if (_busy) return false;
        if (_root == null) return false;
        var packed = ResourceLoader.Load<PackedScene>(scenePath);
        if (packed == null)
        {
            GD.PushWarning($"[Navigator] Scene not found: {scenePath}");
            return false;
        }
        if (UseFadeTransition && _overlays != null)
        {
            _ = FadeAndSwitch(packed);
            return true;
        }
        DoSwitch(packed);
        return true;
    }

    private void DoSwitch(PackedScene packed)
    {
        // Call Exit on current if present, then remove
        if (_current != null)
        {
            if (_current.HasMethod("Exit")) _current.CallDeferred("Exit");
            _current.QueueFree();
            _current = null;
        }
        var inst = packed.Instantiate<Control>();
        _root!.AddChild(inst);
        _current = inst;
        if (_current.HasMethod("Enter")) _current.CallDeferred("Enter");
    }

    private async System.Threading.Tasks.Task FadeAndSwitch(PackedScene packed)
    {
        if (_overlays == null)
        {
            DoSwitch(packed);
            return;
        }
        _busy = true;
        var fade = new ColorRect
        {
            Name = "__ScreenFade__",
            Color = new Color(0, 0, 0, 0),
            MouseFilter = Control.MouseFilterEnum.Stop // block input during transition
        };
        fade.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        _overlays.AddChild(fade);
        var tween = _overlays.CreateTween();
        tween.TweenProperty(fade, "color:a", 1.0, FadeDurationSec).SetTrans(Tween.TransitionType.Cubic).SetEase(Tween.EaseType.In);
        await ToSignal(tween, Tween.SignalName.Finished);

        // Switch content while fully faded
        DoSwitch(packed);

        var tween2 = _overlays.CreateTween();
        tween2.TweenProperty(fade, "color:a", 0.0, FadeDurationSec).SetTrans(Tween.TransitionType.Cubic).SetEase(Tween.EaseType.Out);
        await ToSignal(tween2, Tween.SignalName.Finished);
        fade.QueueFree();
        _busy = false;
    }
}
