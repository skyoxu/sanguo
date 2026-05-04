using System.IO;
using System;
using FluentAssertions;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task179I18nMissingKeyExposurePolicyTests
{
    [Fact]
    public void ShouldPointToExistingTask179EvidenceFiles_WhenCheckingTask179AcceptanceRefs()
    {
        var repoRoot = ResolveRepoRoot();
        var back = File.ReadAllText(Path.Combine(repoRoot, ".taskmaster", "tasks", "tasks_back.json"));
        var gameplay = File.ReadAllText(Path.Combine(repoRoot, ".taskmaster", "tasks", "tasks_gameplay.json"));

        back.Should().Contain("Tests.Godot/tests/Integration/test_task179_hud_integration.gd");
        back.Should().Contain("Tests.Godot/tests/UI/test_task179_orphan_hud_isolation.gd");
        gameplay.Should().Contain("Tests.Godot/tests/Integration/test_task179_hud_integration.gd");
        gameplay.Should().Contain("Tests.Godot/tests/UI/test_task179_orphan_hud_isolation.gd");
    }

    [Theory]
    [InlineData("Friendly fallback", "Friendly fallback")]
    [InlineData("", I18nMissingKeyExposurePolicy.DefaultFriendlyFallback)]
    [InlineData("   ", I18nMissingKeyExposurePolicy.DefaultFriendlyFallback)]
    public void ShouldReturnFriendlyFallback_WhenReleaseMissingKeyPolicyEvaluatesFallback(string fallback, string expected)
    {
        var actual = I18nMissingKeyExposurePolicy.ResolveForBuildMode("release", "i18n.task179.missing", fallback);
        actual.Should().Be(expected);
        actual.Should().NotStartWith("i18n.");
    }

    [Fact]
    // ACC:T179.8
    public void ShouldFallbackToFriendlyMessage_WhenReleaseModeReceivesPlainTextMessage()
    {
        var actual = I18nMissingKeyExposurePolicy.ResolveForBuildMode("release", "Explanation blocked by policy");
        actual.Should().Be(I18nMissingKeyExposurePolicy.DefaultFriendlyFallback);
        actual.Should().NotStartWith("i18n.");
    }

    private static string ResolveRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null)
        {
            if (Directory.Exists(Path.Combine(dir.FullName, ".taskmaster")))
            {
                return dir.FullName;
            }

            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException("Could not locate repo root that contains .taskmaster.");
    }
}
