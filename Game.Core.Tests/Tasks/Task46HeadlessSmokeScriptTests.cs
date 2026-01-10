using System;
using System.Linq;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task46HeadlessSmokeScriptTests
{
    // ADR references (context): ADR-0005, ADR-0011, ADR-0018, ADR-0024.

    private static readonly string[] RequiredCliArguments =
    [
        "--godot-bin",
        "--scene",
        "--timeout-sec",
        "--project-path",
    ];

    private static readonly string[] SupportedModes =
    [
        "loose",
        "strict",
    ];

    private static readonly string[] ReferenceDocumentationPaths =
    [
        "docs/migration/Phase-12-Headless-Smoke-Backlog.md",
        "docs/migration/Phase-12-Headless-Smoke-Tests.md",
    ];

    // ACC:T46.1
    [Fact]
    public void ShouldDefineRequiredCliArguments_WhenValidatingCliContract()
    {
        RequiredCliArguments.Should().NotBeNullOrEmpty();
        RequiredCliArguments.Should().OnlyContain(arg => arg.StartsWith("--", StringComparison.Ordinal));
        RequiredCliArguments.Should().Contain(new[] { "--godot-bin", "--scene", "--timeout-sec", "--project-path" });
        RequiredCliArguments.Distinct(StringComparer.Ordinal).Count().Should().Be(RequiredCliArguments.Length);

        SupportedModes.Should().BeEquivalentTo(new[] { "loose", "strict" });
    }

    // ACC:T46.5
    [Fact]
    public void ShouldDefineReferenceDocumentationPaths_WhenCrossCheckingDocs()
    {
        ReferenceDocumentationPaths.Should().NotBeNullOrEmpty();
        ReferenceDocumentationPaths.Should().OnlyContain(p => p.EndsWith(".md", StringComparison.OrdinalIgnoreCase));
        ReferenceDocumentationPaths.Should().Contain("docs/migration/Phase-12-Headless-Smoke-Backlog.md");
        ReferenceDocumentationPaths.Should().Contain("docs/migration/Phase-12-Headless-Smoke-Tests.md");
        ReferenceDocumentationPaths.Distinct(StringComparer.Ordinal).Count().Should().Be(ReferenceDocumentationPaths.Length);
    }
}
