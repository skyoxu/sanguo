using System;
using System.IO;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task10BoardViewScriptsTests
{
    [Fact]
    public void SanguoBoardView_ShouldConsumeTokenMovedEvent()
    {
        var code = ReadText("Game.Godot/Scripts/Sanguo/SanguoBoardView.cs");
        code.Should().Contain("SanguoTokenMoved.EventType");
    }

    [Fact]
    public void SanguoBoardViewMirror_ShouldConsumeTokenMovedEvent()
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
