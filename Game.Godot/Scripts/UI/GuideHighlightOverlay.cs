using Godot;

namespace Game.Godot.Scripts.UI;

public partial class GuideHighlightOverlay : Control
{
    private Rect2 _highlightRect = new Rect2();
    private bool _hasHighlight;
    private float _pulseTime;
    private float _overlayAlpha = 0.35f;
    private float _borderAlpha = 0.95f;
    private float _borderWidth = 3.0f;

    [Export] public bool EnablePulse { get; set; } = true;
    [Export] public float PulseSpeed { get; set; } = 2.0f;
    [Export] public float OverlayBaseAlpha { get; set; } = 0.35f;
    [Export] public float OverlayPulseAmplitude { get; set; } = 0.05f;
    [Export] public float BorderBaseAlpha { get; set; } = 0.95f;
    [Export] public float BorderPulseAmplitude { get; set; } = 0.08f;
    [Export] public float BorderBaseWidth { get; set; } = 3.0f;
    [Export] public float BorderPulseWidth { get; set; } = 0.6f;

    public override void _Ready()
    {
        MouseFilter = MouseFilterEnum.Ignore;
        UpdatePulseStyle(0.0f);
    }

    public override void _Process(double delta)
    {
        if (!_hasHighlight)
        {
            return;
        }

        if (EnablePulse)
        {
            _pulseTime += (float)delta * PulseSpeed;
            if (_pulseTime > Mathf.Tau)
            {
                _pulseTime -= Mathf.Tau;
            }
        }

        UpdatePulseStyle(_pulseTime);
        QueueRedraw();
    }

    public void SetHighlightRect(Rect2 rect)
    {
        _highlightRect = rect;
        _hasHighlight = rect.Size.X > 1 && rect.Size.Y > 1;
        QueueRedraw();
    }

    public void ClearHighlight()
    {
        _highlightRect = new Rect2();
        _hasHighlight = false;
        QueueRedraw();
    }

    public Rect2 GetHighlightRect()
    {
        return _highlightRect;
    }

    public bool HasHighlight()
    {
        return _hasHighlight;
    }

    public override void _Draw()
    {
        if (!_hasHighlight)
        {
            return;
        }

        DrawRect(new Rect2(Vector2.Zero, Size), new Color(0f, 0f, 0f, _overlayAlpha), true);
        DrawRect(_highlightRect, new Color(1f, 0.85f, 0.2f, _borderAlpha), false, _borderWidth);
    }

    private void UpdatePulseStyle(float time)
    {
        var pulse = EnablePulse ? (Mathf.Sin(time) + 1.0f) * 0.5f : 0.5f;
        var centered = pulse * 2.0f - 1.0f;

        _overlayAlpha = Mathf.Clamp(OverlayBaseAlpha + OverlayPulseAmplitude * centered, 0.0f, 1.0f);
        _borderAlpha = Mathf.Clamp(BorderBaseAlpha + BorderPulseAmplitude * centered, 0.0f, 1.0f);
        _borderWidth = Mathf.Max(0.5f, BorderBaseWidth + BorderPulseWidth * centered);
    }
}
