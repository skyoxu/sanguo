using System;
using System.IO;
using System.Text.RegularExpressions;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Engine;

public sealed class HudSceneTests
{
    [Fact]
    public void HudScene_ShouldExposeDiceButton_ForPlayableLoop()
    {
        var tscn = ReadText("Game.Godot/Scenes/UI/HUD.tscn");
        tscn.Should().Contain("node name=\"DiceButton\"", "HUD should expose a DiceButton node for input");
    }

    [Theory]
    [InlineData("ActivePlayerLabel")]
    [InlineData("DateLabel")]
    [InlineData("MoneyLabel")]
    public void HudScene_ShouldExposeCoreStatusLabels(string nodeName)
    {
        var tscn = ReadText("Game.Godot/Scenes/UI/HUD.tscn");
        tscn.Should().Contain($"node name=\"{nodeName}\"", $"HUD should expose {nodeName} for status display");
    }

    [Fact]
    public void HudScript_ShouldHandleSanguoTurnEvents()
    {
        var code = ReadText("Game.Godot/Scripts/UI/HUD.cs");
        code.Should().MatchRegex(new Regex("\\bSanguoGameTurnStarted\\b", RegexOptions.CultureInvariant));
    }

    [Fact]
    public void HudScript_ShouldHandleSanguoDiceRolledDomainEvent()
    {
        var code = ReadText("Game.Godot/Scripts/UI/HUD.cs");
        code.Should().Contain("SanguoDiceRolled.EventType");
    }

    [Fact]
    public void HudScriptMirror_ShouldHandleSanguoDiceRolledDomainEvent()
    {
        var code = ReadText("Tests.Godot/Game.Godot/Scripts/UI/HUD.cs");
        code.Should().Contain("SanguoDiceRolled.EventType");
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
