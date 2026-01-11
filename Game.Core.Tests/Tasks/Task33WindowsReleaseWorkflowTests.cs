using System;
using System.IO;
using System.Linq;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks
{
    public sealed class Task33WindowsReleaseWorkflowTests
    {
        private const string ExpectedBuildScriptPath = "scripts/python/build_windows.py";

        [Fact]
        public void ShouldKeepExpectedBuildScriptPathStable_WhenValidated()
        {
            ExpectedBuildScriptPath.Should().Be("scripts/python/build_windows.py");
            ExpectedBuildScriptPath.Should().EndWith(".py");
            ExpectedBuildScriptPath.Should().NotContain("\\");
        }

        // ACC:T33.2
        [Fact]
        public void ShouldReferenceBuildWindowsScriptFromWindowsReleaseWorkflows_WhenWorkflowsExist()
        {
            var workflowRelativePaths = new[]
            {
                Path.Combine(".github", "workflows", "windows-release.yml"),
                Path.Combine(".github", "workflows", "windows-release-tag.yml"),
            };

            workflowRelativePaths.Should().HaveCount(2);
            workflowRelativePaths.All(p => p.EndsWith(".yml", StringComparison.OrdinalIgnoreCase)).Should().BeTrue();

            var repoRoot = TryFindRepoRoot();
            repoRoot.Should().NotBeNull("repo root should be discoverable from the test base directory");

            foreach (var relativePath in workflowRelativePaths)
            {
                var fullPath = Path.Combine(repoRoot!, relativePath);
                File.Exists(fullPath).Should().BeTrue($"workflow must exist: {relativePath}");

                var yaml = File.ReadAllText(fullPath);
                yaml.Should().NotBeNullOrWhiteSpace($"workflow must not be empty: {relativePath}");

                yaml.Should().Contain(ExpectedBuildScriptPath);
                yaml.Should().Contain("py -3 scripts/python/build_windows.py");
            }
        }

        private static string? TryFindRepoRoot()
        {
            var candidates = new[]
            {
                new DirectoryInfo(Directory.GetCurrentDirectory()),
                new DirectoryInfo(AppContext.BaseDirectory),
            };

            foreach (var start in candidates.Where(d => d.Exists))
            {
                var dir = start;
                while (dir != null)
                {
                    var marker = Path.Combine(dir.FullName, "project.godot");
                    if (File.Exists(marker))
                    {
                        return dir.FullName;
                    }

                    dir = dir.Parent;
                }
            }

            return null;
        }
    }
}
