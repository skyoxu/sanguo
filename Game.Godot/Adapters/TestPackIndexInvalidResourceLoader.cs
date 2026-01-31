using Godot;
using Game.Core.Ports;
using Game.Core.Services.Sanguo;
using Game.Godot.Scripts.Security;
using System;

namespace Game.Godot.Adapters;

/// <summary>
/// Test-only loader that returns invalid content pack index but otherwise delegates to SecurityFileAdapter.
/// </summary>
public sealed partial class TestPackIndexInvalidResourceLoader : Node, IResourceLoader
{
    public string? LoadText(string path)
    {
        if (string.Equals(path, SanguoContentPackResolver.PacksIndexResPath, StringComparison.Ordinal))
        {
            return "[]";
        }

        return SecurityFileAdapter.TryReadText(path, caller: nameof(TestPackIndexInvalidResourceLoader), out var text, out _)
            ? text
            : null;
    }

    public byte[]? LoadBytes(string path)
    {
        return SecurityFileAdapter.TryReadBytes(path, caller: nameof(TestPackIndexInvalidResourceLoader), out var bytes, out _)
            ? bytes
            : null;
    }
}
