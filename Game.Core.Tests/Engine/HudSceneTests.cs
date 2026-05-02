using System;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Engine;

public sealed class HudSceneTests
{
    [Fact]
    public void ShouldExposeDiceButton_WhenHudSceneLoaded()
    {
        var path = ResolvePath("Game.Godot/Scenes/UI/HUD.tscn");
        ContainsTokenInFile(path, "node name=\"DiceButton\"")
            .Should().BeTrue("HUD should expose a DiceButton node for input");
    }

    [Theory]
    [InlineData("ActivePlayerLabel")]
    [InlineData("DateLabel")]
    [InlineData("MoneyLabel")]
    public void ShouldExposeCoreStatusLabels_WhenHudSceneLoaded(string nodeName)
    {
        var path = ResolvePath("Game.Godot/Scenes/UI/HUD.tscn");
        ContainsTokenInFile(path, $"node name=\"{nodeName}\"")
            .Should().BeTrue($"HUD should expose {nodeName} for status display");
    }

    [Fact]
    public void ShouldContainTurnEventHandling_WhenReadingHudScript()
    {
        var code = File.ReadAllText(ResolvePath("Game.Godot/Scripts/UI/HudEventHandlerRegistry.cs"));
        code.Should().MatchRegex(new Regex("\\bSanguoGameTurnStarted\\.EventType\\b", RegexOptions.CultureInvariant));
    }

    [Fact]
    public void ShouldContainDiceRolledHandling_WhenReadingHudScript()
    {
        var path = ResolvePath("Game.Godot/Scripts/UI/HudEventHandlerRegistry.cs");
        ContainsTokenInFile(path, "SanguoDiceRolled.EventType").Should().BeTrue();
    }

    private static string ResolvePath(string relativePath)
    {
        return Path.Combine(
            AppContext.BaseDirectory,
            "..",
            "..",
            "..",
            "..",
            relativePath.Replace('/', Path.DirectorySeparatorChar));
    }

    private static bool ContainsTokenInFile(string absolutePath, string token)
    {
        return File.ReadLines(absolutePath).Any(line => line.Contains(token, StringComparison.Ordinal));
    }
}
