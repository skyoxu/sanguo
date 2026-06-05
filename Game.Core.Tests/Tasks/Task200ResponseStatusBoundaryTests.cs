using System;
using System.IO;
using System.Linq;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task200ResponseStatusBoundaryTests
{
    // ACC:T200.9
    [Fact]
    [Trait("acceptance", "ACC:T200.9")]
    public void ShouldKeepResponseStatusAdaptersOutsideGameCore_WhenHudRendersPlatformAndAdapterState()
    {
        var repoRoot = FindRepoRoot();
        var coreRoot = Path.Combine(repoRoot, "Game.Core");
        var offendingFiles = Directory
            .EnumerateFiles(coreRoot, "*.cs", SearchOption.AllDirectories)
            .Where(path => !path.Contains($"{Path.DirectorySeparatorChar}bin{Path.DirectorySeparatorChar}", StringComparison.Ordinal)
                           && !path.Contains($"{Path.DirectorySeparatorChar}obj{Path.DirectorySeparatorChar}", StringComparison.Ordinal))
            .Where(path =>
            {
                var text = File.ReadAllText(path);
                return text.Contains("using Godot", StringComparison.Ordinal)
                       || text.Contains("Godot.", StringComparison.Ordinal);
            })
            .Select(path => Path.GetRelativePath(repoRoot, path))
            .ToArray();

        offendingFiles.Should().BeEmpty(
            "Task 200 response status rendering must keep Godot-facing persistence, localization, audio, performance, and platform adapters outside Game.Core");
    }

    private static string FindRepoRoot()
    {
        var dir = AppContext.BaseDirectory;
        for (var i = 0; i < 8 && !string.IsNullOrWhiteSpace(dir); i++)
        {
            if (File.Exists(Path.Combine(dir, "Game.sln")) && Directory.Exists(Path.Combine(dir, "Game.Core")))
            {
                return dir;
            }

            dir = Directory.GetParent(dir)?.FullName ?? string.Empty;
        }

        throw new DirectoryNotFoundException("Could not locate repository root from test base directory.");
    }
}
