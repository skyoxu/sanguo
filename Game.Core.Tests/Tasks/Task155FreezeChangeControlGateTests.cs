using System.IO;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task155FreezeChangeControlGateTests
{
    private const string FreezeDocPath = "docs/architecture/overlays/PRD-SANGUO-V3/08/08-governance-freeze-change-control.md";

    // ACC:T155.1
    [Fact]
    [Trait("acceptance", "ACC:T155.1")]
    public void ShouldRequireFreezeChangeControlDocumentToExist()
    {
        var fullPath = Path.Combine(FindRepoRoot(), FreezeDocPath.Replace('/', Path.DirectorySeparatorChar));
        File.Exists(fullPath).Should().BeTrue("freeze change-control doc is required as CI governance evidence");
    }

    // ACC:T155.2
    [Fact]
    [Trait("acceptance", "ACC:T155.2")]
    public void ShouldContainTripletChangeControlKeywords_InFreezeDocument()
    {
        var fullPath = Path.Combine(FindRepoRoot(), FreezeDocPath.Replace('/', Path.DirectorySeparatorChar));
        var text = File.ReadAllText(fullPath);

        text.Should().Contain("freeze", "freeze revision rule must be documented");
        text.Should().Contain("assertion", "assertion update rule must be documented");
        text.Should().Contain("test", "test evidence update rule must be documented");
    }

    private static string FindRepoRoot()
    {
        var current = new DirectoryInfo(System.AppContext.BaseDirectory);
        while (current is not null)
        {
            var marker = Path.Combine(current.FullName, ".taskmaster", "tasks", "tasks.json");
            if (File.Exists(marker))
            {
                return current.FullName;
            }

            current = current.Parent;
        }

        throw new DirectoryNotFoundException("Repo root not found (missing .taskmaster/tasks/tasks.json).");
    }
}

