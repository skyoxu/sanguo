using FluentAssertions;
using System;
using System.IO;
using System.Linq;
using System.Text;
using Xunit;

namespace Game.Core.Tests.Docs;

public sealed class HelpTutorialDocumentationTests
{
    private const string DocRelativePath = "docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md";
    private const string SectionTitle = "\u6559\u7a0b\u53c2\u8003\u7684\u5b98\u65b9\u793a\u4f8b\u6e05\u5355";
    private const string LearningRouteTitle = "\u5b66\u4e60\u8def\u7ebf\u5efa\u8bae";
    private const string TeamKnowledgeBaseTitle = "\u56e2\u961f\u77e5\u8bc6\u5e93";
    private const string EmDash = "\u2014";

    // acceptance: ACC:T30.6
    [Fact]
    public void TutorialDoc_WhenCheckingOfficialExamplesList_ShouldContainAtLeastOneEntry()
    {
        var repoRoot = RepoRootLocator.FindRepoRoot();
        var docPath = Path.Combine(repoRoot, DocRelativePath.Replace('/', Path.DirectorySeparatorChar));

        File.Exists(docPath).Should().BeTrue($"doc file should exist at '{docPath}'");

        var text = File.ReadAllText(docPath, Encoding.UTF8);
        text.Should().Contain(SectionTitle);
        text.Should().Contain(LearningRouteTitle);
        text.Should().Contain(TeamKnowledgeBaseTitle);

        var listEntries = text
            .Split('\n')
            .Select(l => l.Trim())
            .Where(l => l.StartsWith("- [", StringComparison.Ordinal) && l.Contains("](", StringComparison.Ordinal) && l.Contains(EmDash, StringComparison.Ordinal))
            .ToArray();

        listEntries.Length.Should().BeGreaterThan(0, $"the doc must contain at least one official example list entry formatted like '- [Name](url) {EmDash} reason'");

        var hasOfficialSourceLink = listEntries
            .Select(TryExtractMarkdownUrl)
            .Where(url => !string.IsNullOrWhiteSpace(url))
            .Any(url =>
                url!.Contains("github.com/godotengine/godot-demo-projects", StringComparison.OrdinalIgnoreCase) ||
                url!.Contains("docs.godotengine.org", StringComparison.OrdinalIgnoreCase));

        hasOfficialSourceLink.Should().BeTrue("at least one example link must point to an official Godot source (godotengine/godot-demo-projects or docs.godotengine.org)");
    }

    private static string? TryExtractMarkdownUrl(string line)
    {
        var open = line.IndexOf("](", StringComparison.Ordinal);
        if (open < 0) return null;
        open += 2;
        var close = line.IndexOf(')', open);
        if (close <= open) return null;
        return line.Substring(open, close - open).Trim();
    }
}

internal static class RepoRootLocator
{
    public static string FindRepoRoot()
    {
        var start = new DirectoryInfo(AppContext.BaseDirectory);
        var cursor = start;
        while (cursor != null)
        {
            if (File.Exists(Path.Combine(cursor.FullName, "project.godot")))
            {
                return cursor.FullName;
            }

            cursor = cursor.Parent;
        }

        throw new DirectoryNotFoundException($"Unable to locate repo root from '{start.FullName}'.");
    }
}

