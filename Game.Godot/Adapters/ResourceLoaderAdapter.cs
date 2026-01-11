using Godot;
using Game.Core.Ports;
using Game.Godot.Scripts.Security;

namespace Game.Godot.Adapters;

public partial class ResourceLoaderAdapter : Node, IResourceLoader
{
    public string? LoadText(string path)
    {
        return SecurityFileAdapter.TryReadText(path, caller: nameof(ResourceLoaderAdapter), out var text, out _)
            ? text
            : null;
    }

    public byte[]? LoadBytes(string path)
    {
        return SecurityFileAdapter.TryReadBytes(path, caller: nameof(ResourceLoaderAdapter), out var bytes, out _)
            ? bytes
            : null;
    }
}
