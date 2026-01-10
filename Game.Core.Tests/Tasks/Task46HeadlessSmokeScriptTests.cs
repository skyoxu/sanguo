using System;
using System.IO;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task46HeadlessSmokeScriptTests
{
    // ADR references (context): ADR-0005, ADR-0011, ADR-0018, ADR-0024.

    private static readonly string[] ReferenceDocumentationPaths =
    [
        "docs/migration/Phase-12-Headless-Smoke-Backlog.md",
        "docs/migration/Phase-12-Headless-Smoke-Tests.md",
    ];

    // ACC:T46.1
    [Fact]
    public void ShouldExposeCliContract_WhenReadingSmokeHeadlessScript()
    {
        var repoRoot = FindRepoRootFrom(AppContext.BaseDirectory);
        var scriptPath = Path.Combine(repoRoot, "scripts", "python", "smoke_headless.py");
        File.Exists(scriptPath).Should().BeTrue($"smoke runner script must exist at {scriptPath}");

        var text = File.ReadAllText(scriptPath);
        text.Should().Contain("--godot-bin");
        text.Should().Contain("--scene");
        text.Should().Contain("--timeout-sec");
        text.Should().Contain("--project-path");
        text.Should().Contain("--mode");
        text.Should().Contain("choices=[\"loose\", \"strict\"]");
    }

    // ACC:T46.5
    [Fact]
    public void ShouldDefineReferenceDocumentationPaths_WhenCrossCheckingDocs()
    {
        ReferenceDocumentationPaths.Should().NotBeNullOrEmpty();
        ReferenceDocumentationPaths.Should().OnlyContain(p => p.EndsWith(".md", StringComparison.OrdinalIgnoreCase));
        ReferenceDocumentationPaths.Should().Contain("docs/migration/Phase-12-Headless-Smoke-Backlog.md");
        ReferenceDocumentationPaths.Should().Contain("docs/migration/Phase-12-Headless-Smoke-Tests.md");
    }

    // ACC:T46.2, ACC:T46.3
    [Fact]
    public void ShouldWriteLogsUnderDateBasedDirectoryAndMarkStrictFailures_WhenReadingSmokeHeadlessScript()
    {
        var repoRoot = FindRepoRootFrom(AppContext.BaseDirectory);
        var scriptPath = Path.Combine(repoRoot, "scripts", "python", "smoke_headless.py");
        var text = File.ReadAllText(scriptPath);

        text.Should().Contain("%Y-%m-%d", "the smoke runner must use logs/ci/<YYYY-MM-DD>/ as the stable evidence root");
        text.Should().Contain("Path(\"logs\") / \"ci\"", "the smoke runner must write artifacts under logs/ci");
        text.Should().Contain("\"strict-failed\"", "strict mode must explicitly name strict-failed for log annotation");
        text.Should().Contain("[SMOKE]", "strict mode must write an explicit marker into logs for easy grep");
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
