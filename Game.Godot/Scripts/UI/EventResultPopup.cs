using Godot;
using System;
using System.Collections.Generic;

namespace Game.Godot.Scripts.UI;

public partial class EventResultPopup : Control
{
    [Export(PropertyHint.Range, "0,10,0.1,or_greater")]
    public double AutoHideSeconds { get; set; } = 3.0;

    private Label _message = default!;
    private Button _closeButton = default!;
    private SceneTreeTimer? _hideTimer;
    private readonly Queue<ResultMessage> _queue = new();

    public override void _Ready()
    {
        ProcessMode = Node.ProcessModeEnum.Always;
        _message = GetNode<Label>("Center/Panel/VBox/Message");
        _closeButton = GetNode<Button>("Center/Panel/VBox/CloseButton");
        _closeButton.Pressed += OnClosePressed;
        _closeButton.Text = TranslateOrFallback("ui.hud.result.close", "Close");
        Visible = false;
    }

    public void ShowMessage(string message, double? autoHideSeconds = null)
    {
        if (string.IsNullOrWhiteSpace(message))
        {
            return;
        }

        var entry = new ResultMessage(message, autoHideSeconds);
        if (Visible)
        {
            _queue.Enqueue(entry);
            return;
        }

        Display(entry);
    }

    private void Display(ResultMessage entry)
    {
        _message.Text = entry.Text;
        Visible = true;
        RestartTimer(entry.AutoHideSeconds ?? AutoHideSeconds);
    }

    private void RestartTimer(double seconds)
    {
        _hideTimer?.Dispose();
        _hideTimer = null;

        if (seconds <= 0)
        {
            return;
        }

        _hideTimer = GetTree().CreateTimer(seconds);
        _hideTimer.Timeout += OnAutoHideTimeout;
    }

    private void OnAutoHideTimeout()
    {
        HideAndContinue();
    }

    private void OnClosePressed()
    {
        HideAndContinue();
    }

    private void HideAndContinue()
    {
        Visible = false;
        _hideTimer?.Dispose();
        _hideTimer = null;

        if (_queue.Count == 0)
        {
            return;
        }

        Display(_queue.Dequeue());
    }

    private static string TranslateOrFallback(string key, string fallback)
    {
        if (string.IsNullOrWhiteSpace(key))
        {
            return fallback;
        }

        var translated = TranslationServer.Translate(key);
        if (string.IsNullOrWhiteSpace(translated) || string.Equals(translated, key, StringComparison.Ordinal))
        {
            return fallback;
        }

        return translated;
    }

    private readonly record struct ResultMessage(string Text, double? AutoHideSeconds);
}
