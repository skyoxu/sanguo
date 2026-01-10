using System;
using System.IO;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks
{
    public sealed class Task46HeadlessSmokeCiExampleTests
    {
        // ADR References: ADR-0005, ADR-0011, ADR-0018, ADR-0024
        // ACC:T46.4
        // This is a documentation guardrail for CI: strict headless smoke must be runnable on Windows.
        [Fact]
        public void ShouldContainStrictModeExample_WhenReviewingWindowsQualityGateWorkflow()
        {
            var repoRoot = FindRepoRootFrom(AppContext.BaseDirectory);
            var workflowPath = Path.Combine(repoRoot, ".github", "workflows", "windows-quality-gate.yml");
            File.Exists(workflowPath).Should().BeTrue($"workflow must exist at {workflowPath}");

            var text = File.ReadAllText(workflowPath);
            text.Should().Contain("smoke_headless.py", "workflow must document the strict smoke runner");
            text.Should().Contain("--mode strict", "workflow must document strict mode usage");
            text.Should().Contain("--project-path", "workflow example must match the smoke_headless.py CLI contract");
        }

        private static string FindRepoRootFrom(string startDir)
        {
            var dir = new DirectoryInfo(startDir);
            while (dir is not null)
            {
                if (File.Exists(Path.Combine(dir.FullName, "Game.sln")))
                {
                    return dir.FullName;
                }

                dir = dir.Parent;
            }

            throw new DirectoryNotFoundException("Unable to locate repo root (Game.sln not found).");
        }
    }
}
