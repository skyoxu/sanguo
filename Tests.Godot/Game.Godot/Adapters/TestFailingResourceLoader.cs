using Godot;
using Game.Core.Ports;

namespace Game.Godot.Adapters;

/// <summary>
/// Test-only resource loader that always fails.
/// </summary>
public partial class TestFailingResourceLoader : Node, IResourceLoader
{
    public string? LoadText(string path) => null;

    public byte[]? LoadBytes(string path) => null;
}

