using System;
using System.IO;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task69UiLocalizationWiringTests
{
    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var marker = Path.Combine(dir.FullName, ".taskmaster", "tasks", "tasks.json");
            if (File.Exists(marker))
            {
                return dir.FullName;
            }

            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException("Repo root not found (missing .taskmaster/tasks/tasks.json).");
    }

    [Fact]
    public void ShouldKeepTask69UiLocalizationWiringPointBoundToGate_WhenHandlingMissingTranslation()
    {
        var repoRoot = FindRepoRoot();
        var sourcePath = Path.Combine(repoRoot, "Game.Godot", "Scripts", "UI", "EventExplainService.cs");
        var source = File.ReadAllText(sourcePath);

        source.Should().Contain("Task69ExplanationLocalizationGate.IsTask69ExplanationKey(key)");
        source.Should().Contain("var buildMode = OS.IsDebugBuild() ? \"dev\" : \"release\";");
        source.Should().Contain("Task69ExplanationLocalizationGate.ResolveMissingTranslation(buildMode, key, fallback)");
    }
}
