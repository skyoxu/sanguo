using Godot;

namespace Game.Godot.Examples.Components;

public partial class Toast : Control
{
    private Label _text = default!;
    private Timer _timer = default!;
    private Tween? _tween;

    public override void _Ready()
    {
        _text = GetNode<Label>("Panel/Label");
        _timer = GetNode<Timer>("Timer");
        _timer.Timeout += OnTimeout;
        Hide();
    }

    public void ShowToast(string message, double seconds = 2.0)
    {
        _text.Text = message ?? string.Empty;
        Modulate = new Color(1,1,1,1);
        Show();
        _timer.Stop();
        _timer.WaitTime = seconds;
        _timer.Start();
    }

    private void OnTimeout()
    {
        _tween?.Kill();
        _tween = CreateTween();
        _tween.TweenProperty(this, "modulate:a", 0.0, 0.4).SetTrans(Tween.TransitionType.Cubic).SetEase(Tween.EaseType.Out);
        _tween.Finished += () => Hide();
    }
}

