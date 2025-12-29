using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task9UiBoundaryTests
{
    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var marker = Path.Combine(dir.FullName, "project.godot");
            if (File.Exists(marker))
                return dir.FullName;
            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException("Repo root not found (missing project.godot).");
    }

    // ACC:T9.3
    [Fact]
    public void ShouldNotReferenceSanguoPlayerEntity_InGodotUiScripts()
    {
        var repoRoot = FindRepoRoot();
        var uiDir = Path.Combine(repoRoot, "Game.Godot", "Scripts", "UI");
        Directory.Exists(uiDir).Should().BeTrue($"UI scripts dir must exist: {uiDir}");

        var offenderFiles = new List<string>();
        var rx = new Regex(@"\bSanguoPlayer\b", RegexOptions.CultureInvariant);

        foreach (var file in Directory.EnumerateFiles(uiDir, "*.cs", SearchOption.AllDirectories))
        {
            var text = File.ReadAllText(file);
            if (rx.IsMatch(text))
                offenderFiles.Add(file);
        }

        offenderFiles.Should().BeEmpty(
            "UI must not reference SanguoPlayer entity directly; use view snapshots/DTOs across layers instead.");
    }
}

