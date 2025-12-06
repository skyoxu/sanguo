using Godot;

namespace Game.Godot.Scripts.UI;

public partial class ThemeApplier : Node
{
    [Export]
    public string FontPath { get; set; } = "res://Game.Godot/Fonts/NotoSans-Regular.ttf";

    public override void _Ready()
    {
        TryApplyFont(FontPath);
    }

    private void TryApplyFont(string path)
    {
        if (!FileAccess.FileExists(path))
            return;

        var font = ResourceLoader.Load<FontFile>(path);
        if (font == null)
            return;

        ApplyFontToControls(GetTree().Root, font);
    }

    private void ApplyFontToControls(Node root, Font font)
    {
        if (root is Control c)
        {
            c.AddThemeFontOverride("font", font);
        }
        foreach (var child in root.GetChildren())
        {
            if (child is Node n)
                ApplyFontToControls(n, font);
        }
    }
}

