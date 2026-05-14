using FluentAssertions;
using System;
using System.IO;
using System.Linq;
using System.Text;
using Xunit;

namespace Game.Core.Tests.Docs;

public sealed class UiGddFlowDocumentationTests
{
    private const string UiGddRelativePath = "docs/gdd/ui-gdd-flow.md";
    private const string OverlayIndexRef = "docs/architecture/overlays/PRD-SANGUO-V4/08/_index.md";
    private const string MatrixHeading = "## 5. UI Wiring Matrix";
    private const string CandidateHeading = "## 11. Next UI Wiring Task Candidates";
    private const string UnwiredHeading = "## 10. Unwired UI Feature List";
    private const string AdrToken = "ADR-0005";
    private const string Ch01Token = "CH01";
    private const string Ch07Token = "CH07";

    // ACC:T187.1
    // ACC:T187.2
    // ACC:T187.4
    // ACC:T187.5
    // ACC:T187.6
    [Fact]
    public void ShouldContainGovernedUiGddTraceability_WhenValidatingTask187Scope()
    {
        var docPath = ResolveRepoFile(UiGddRelativePath);
        File.Exists(docPath).Should().BeTrue($"UI GDD flow doc must exist at '{docPath}'");

        var text = File.ReadAllText(docPath, Encoding.UTF8);
        text.Should().Contain(MatrixHeading);
        text.Should().Contain(UnwiredHeading);
        text.Should().Contain(CandidateHeading);
        text.Should().Contain(AdrToken);
        text.Should().Contain(Ch01Token);
        text.Should().Contain(Ch07Token);
        text.Should().Contain(OverlayIndexRef);
    }

    // ACC:T187.3
    [Fact]
    public void ShouldReferenceRequiredOverlayArtifacts_WhenValidatingTask187OverlayTraceability()
    {
        var docPath = ResolveRepoFile(UiGddRelativePath);
        var text = File.ReadAllText(docPath, Encoding.UTF8);

        text.Should().Contain("PRD-SANGUO-T2");
        text.Should().Contain("PRD-SANGUO-V3");
        text.Should().Contain("Matrix link: `## 5. UI Wiring Matrix row Entry And Bootstrap");
    }

    private static string ResolveRepoFile(string relativePath)
    {
        var repoRoot = RepoRootLocator.FindRepoRoot();
        return Path.Combine(repoRoot, relativePath.Replace('/', Path.DirectorySeparatorChar));
    }
}
