using Godot;
using System;
using System.Collections.Generic;

namespace Game.Godot.Scripts.UI;

public partial class EventResultPopup : Control
{
    [Export(PropertyHint.Range, "0,10,0.1,or_greater")]
    public double AutoHideSeconds { get; set; } = 3.0;

    [Export(PropertyHint.Range, "0,3,0.05,or_greater")]
    public double QueueDrainAutoHideSeconds { get; set; } = 0.35;

    private Label _message = default!;
    private Button _closeButton = default!;
    private SceneTreeTimer? _hideTimer;
    private readonly Queue<ResultMessage> _queue = new();
    private bool _resumeOnHide;
    private double _currentAutoHideSeconds;

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
            TryAccelerateCurrentAutoHideForQueueDrain();
            return;
        }

        Display(entry, fromQueue: false);
    }

    private void Display(ResultMessage entry, bool fromQueue)
    {
        _message.Text = entry.Text;
        PauseGameIfNeeded();
        Visible = true;
        var requestedSeconds = entry.AutoHideSeconds ?? AutoHideSeconds;
        var effectiveSeconds = ResolveEffectiveAutoHideSeconds(requestedSeconds, fromQueue);
        RestartTimer(effectiveSeconds);
    }

    private void RestartTimer(double seconds)
    {
        _hideTimer?.Dispose();
        _hideTimer = null;
        _currentAutoHideSeconds = 0;

        if (seconds <= 0)
        {
            return;
        }

        _currentAutoHideSeconds = seconds;
        _hideTimer = GetTree().CreateTimer(seconds, true);
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
        _currentAutoHideSeconds = 0;

        if (_queue.Count == 0)
        {
            ResumeGameIfNeeded();
            return;
        }

        Display(_queue.Dequeue(), fromQueue: true);
    }

    private void TryAccelerateCurrentAutoHideForQueueDrain()
    {
        if (_hideTimer == null || _currentAutoHideSeconds <= 0)
        {
            return;
        }

        if (QueueDrainAutoHideSeconds <= 0)
        {
            return;
        }

        if (_currentAutoHideSeconds <= QueueDrainAutoHideSeconds)
        {
            return;
        }

        RestartTimer(QueueDrainAutoHideSeconds);
    }

    private double ResolveEffectiveAutoHideSeconds(double requestedSeconds, bool fromQueue)
    {
        if (requestedSeconds <= 0)
        {
            return requestedSeconds;
        }

        if (!fromQueue || QueueDrainAutoHideSeconds <= 0)
        {
            return requestedSeconds;
        }

        return Math.Min(requestedSeconds, QueueDrainAutoHideSeconds);
    }

    private void PauseGameIfNeeded()
    {
        var tree = GetTree();
        if (tree == null || tree.Paused)
        {
            return;
        }

        tree.Paused = true;
        _resumeOnHide = true;
    }

    private void ResumeGameIfNeeded()
    {
        if (!_resumeOnHide)
        {
            return;
        }

        var tree = GetTree();
        if (tree != null)
        {
            tree.Paused = false;
        }
        _resumeOnHide = false;
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
