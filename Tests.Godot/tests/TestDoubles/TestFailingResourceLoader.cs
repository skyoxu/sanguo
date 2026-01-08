using Godot;
using Game.Core.Ports;

namespace Tests.Godot.TestDoubles;

/// <summary>
/// Test-only resource loader that always fails.
/// </summary>
public sealed partial class TestFailingResourceLoader : Node, IResourceLoader
{
    public string? LoadText(string path) => null;

    public byte[]? LoadBytes(string path) => null;
}

