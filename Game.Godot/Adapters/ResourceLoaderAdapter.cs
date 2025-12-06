using Godot;
using Game.Core.Ports;

namespace Game.Godot.Adapters;

public partial class ResourceLoaderAdapter : Node, IResourceLoader
{
    public string? LoadText(string path)
    {
        try
        {
            if (!IsPathSafe(path)) return null;
            using var f = FileAccess.Open(path, FileAccess.ModeFlags.Read);
            if (f == null) return null;
            return f.GetAsText();
        }
        catch
        {
            return null;
        }
    }

    public byte[]? LoadBytes(string path)
    {
        try
        {
            if (!IsPathSafe(path)) return null;
            using var f = FileAccess.Open(path, FileAccess.ModeFlags.Read);
            if (f == null) return null;
            return f.GetBuffer((long)f.GetLength());
        }
        catch
        {
            return null;
        }
    }

    private static bool IsPathSafe(string path)
    {
        if (string.IsNullOrEmpty(path)) return false;
        var p = path.Trim();
        if (!(p.StartsWith("res://", System.StringComparison.OrdinalIgnoreCase) || p.StartsWith("user://", System.StringComparison.OrdinalIgnoreCase)))
            return false;
        if (p.Contains("../")) return false;
        return true;
    }
}
