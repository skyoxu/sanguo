using System;
using System.IO;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task10BoardViewScriptsTests
{
    [Fact]
    public void ShouldContainTokenMovedEventType_WhenReadingSanguoBoardViewScript()
    {
        var code = ReadText("Game.Godot/Scripts/Sanguo/SanguoBoardView.cs");
        code.Should().Contain("SanguoTokenMoved.EventType");
    }

    [Fact]
    public void ShouldContainTokenMovedEventType_WhenReadingSanguoBoardViewMirrorScript()
    {
        var code = ReadText("Tests.Godot/Game.Godot/Scripts/Sanguo/SanguoBoardView.cs");
        code.Should().Contain("SanguoTokenMoved.EventType");
    }

    private static string ReadText(string relativePath)
    {
        var full = Path.Combine(
            AppContext.BaseDirectory,
            "..",
            "..",
            "..",
            "..",
            relativePath.Replace('/', Path.DirectorySeparatorChar));

        return File.ReadAllText(full);
    }
}
