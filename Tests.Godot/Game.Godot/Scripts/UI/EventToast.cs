using Godot;
using System;

namespace Game.Godot.Scripts.UI;

public partial class EventToast : Control
{
    [Export(PropertyHint.Range, "0,10,0.1,or_greater")]
    public double AutoHideSeconds { get; set; } = 2.0;

    private Label _label = default!;
    private SceneTreeTimer? _hideTimer;

    public override void _Ready()
    {
        _label = GetNode<Label>("Panel/Label");
        Visible = false;
    }

    public void ShowMessage(string message)
    {
        if (string.IsNullOrWhiteSpace(message))
        {
            return;
        }

        _label.Text = message;
        Visible = true;

        _hideTimer?.Dispose();
        _hideTimer = null;

        if (AutoHideSeconds <= 0)
        {
            return;
        }

        _hideTimer = GetTree().CreateTimer(AutoHideSeconds);
        _hideTimer.Timeout += () =>
        {
            Visible = false;
            _hideTimer?.Dispose();
            _hideTimer = null;
        };
    }
}

