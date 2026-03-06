using System;
using System.IO;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task1WindowsPlatformGateTests
{
    [Fact]
    public void ShouldReportWindowsOnlyEvidence_WhenTask1PreflightHasRun()
    {
        if (!Task1PreflightEvidenceGuard.TryGetLatestArtifact(out var artifact, out var reason))
        {
            Task1PreflightEvidenceGuard.EnsureOrSkip(reason);
            return;
        }

        using var document = JsonDocument.Parse(File.ReadAllText(artifact.TaskJsonPath));
        var root = document.RootElement;
        var windowsOnly = root.GetProperty("windows_only_check");

        root.GetProperty("os_platform").GetString().Should().Be("Windows");
        windowsOnly.GetProperty("result").GetString().Should().Be("pass");
        windowsOnly.GetProperty("reason").GetString().Should().BeEmpty();

        var evidenceFile = windowsOnly.GetProperty("evidence_file").GetString();
        evidenceFile.Should().NotBeNullOrWhiteSpace();
        File.Exists(Path.Combine(artifact.RepoRoot, evidenceFile!.Replace('/', Path.DirectorySeparatorChar))).Should().BeTrue();
    }

    [Theory]
    [InlineData("Windows", true)]
    [InlineData("Linux", false)]
    [InlineData("Darwin", false)]
    [InlineData("", false)]
    public void ShouldValidateWindowsPlatformContract_WhenPlatformChanges(string platformName, bool expected)
    {
        IsWindowsPlatformContract(platformName).Should().Be(expected);
    }

    private static bool IsWindowsPlatformContract(string platformName)
    {
        return string.Equals(platformName, "Windows", StringComparison.OrdinalIgnoreCase);
    }
}
