using Godot;

namespace Game.Godot.Scripts.UI;

public partial class PrimaryButton : Button
{
    public enum ButtonVariant { Primary, Secondary, Danger }
    public enum ButtonSize { Small, Medium, Large }

    [Export] public ButtonVariant Variant { get; set; } = ButtonVariant.Primary;
    [Export] public new ButtonSize Size { get; set; } = ButtonSize.Medium;

    public override void _Ready()
    {
        ApplyVariant();
        ApplySize();
    }

    private void ApplyVariant()
    {
        var normalStyle = new StyleBoxFlat();
        var hoverStyle = new StyleBoxFlat();
        switch (Variant)
        {
            case ButtonVariant.Primary:
                normalStyle.BgColor = new Color(0.2f, 0.5f, 1f);
                hoverStyle.BgColor = new Color(0.3f, 0.6f, 1f);
                break;
            case ButtonVariant.Secondary:
                normalStyle.BgColor = new Color(0.5f, 0.5f, 0.5f);
                hoverStyle.BgColor = new Color(0.6f, 0.6f, 0.6f);
                break;
            case ButtonVariant.Danger:
                normalStyle.BgColor = new Color(1f, 0.2f, 0.2f);
                hoverStyle.BgColor = new Color(1f, 0.3f, 0.3f);
                break;
        }
        // Godot 4: set corner radius individually (CornerRadiusAll removed)
        normalStyle.CornerRadiusTopLeft = 8; normalStyle.CornerRadiusTopRight = 8; normalStyle.CornerRadiusBottomRight = 8; normalStyle.CornerRadiusBottomLeft = 8;
        hoverStyle.CornerRadiusTopLeft = 8; hoverStyle.CornerRadiusTopRight = 8; hoverStyle.CornerRadiusBottomRight = 8; hoverStyle.CornerRadiusBottomLeft = 8;
        AddThemeStyleboxOverride("normal", normalStyle);
        AddThemeStyleboxOverride("hover", hoverStyle);
    }

    private void ApplySize()
    {
        Vector2 size = Size switch
        {
            ButtonSize.Small => new Vector2(80, 28),
            ButtonSize.Medium => new Vector2(100, 40),
            ButtonSize.Large => new Vector2(140, 52),
            _ => new Vector2(100, 40)
        };
        CustomMinimumSize = size;
    }
}

