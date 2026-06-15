using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task219ReadableLoopSummaryTests
{
    // ACC:T219.8
    // ACC:T219.9
    // ACC:T219.10
    // ACC:T219.11
    [Trait("acceptance", "ACC:T219.8")]
    [Trait("acceptance", "ACC:T219.9")]
    [Trait("acceptance", "ACC:T219.10")]
    [Trait("acceptance", "ACC:T219.11")]
    [Fact]
    public void ShouldProjectPrimaryReadableLoopState_WhenCoreInputsChange()
    {
        var summary = ReadableLoopSummaryProjector.Project(
            phase: "pressure",
            pressure: 4,
            resources: 120,
            hp: 82,
            prompt: "Choose combat response",
            outcome: "pending");

        summary.Phase.Should().Be("pressure");
        summary.Pressure.Should().Be(4);
        summary.Resources.Should().Be(120);
        summary.Hp.Should().Be(82);
        summary.Prompt.Should().Be("Choose combat response");
        summary.Outcome.Should().Be("pending");
        summary.VisibleText.Should().ContainAll(
            "Phase: pressure",
            "Pressure: 4",
            "Resources: 120",
            "HP: 82",
            "Prompt: Choose combat response",
            "Outcome: pending");
        summary.RefusalReason.Should().BeEmpty();
    }

    // ACC:T219.12
    // ACC:T219.13
    [Trait("acceptance", "ACC:T219.12")]
    [Trait("acceptance", "ACC:T219.13")]
    [Fact]
    public void ShouldKeepLoopStateUnchangedExceptFeedback_WhenActionIsRefused()
    {
        var before = ReadableLoopSummaryProjector.Project(
            phase: "board",
            pressure: 2,
            resources: 30,
            hp: 41,
            prompt: "Build or skip",
            outcome: "waiting");

        var after = ReadableLoopSummaryProjector.RefuseAction(before, "insufficient_resources");

        after.Phase.Should().Be(before.Phase);
        after.Pressure.Should().Be(before.Pressure);
        after.Resources.Should().Be(before.Resources);
        after.Hp.Should().Be(before.Hp);
        after.Prompt.Should().Be(before.Prompt);
        after.Outcome.Should().Be(before.Outcome);
        after.RefusalReason.Should().Be("insufficient_resources");
        after.VisibleText.Should().Contain("Refusal: insufficient_resources");
    }

    // ACC:T219.14
    // ACC:T219.15
    [Trait("acceptance", "ACC:T219.14")]
    [Trait("acceptance", "ACC:T219.15")]
    [Fact]
    public void ShouldExposeAuditEvidence_WhenProjectorDoesNotDependOnGodotTypes()
    {
        typeof(ReadableLoopSummaryProjector).Assembly.GetReferencedAssemblies()
            .Should().NotContain(assembly => assembly.Name == "GodotSharp");

        var summary = ReadableLoopSummaryProjector.Project(
            phase: "camp",
            pressure: 0,
            resources: 10,
            hp: 99,
            prompt: "Prepare",
            outcome: "ready");

        summary.EvidenceTags.Should().Contain(new[]
        {
            "pure-core",
            "readable-loop",
            "deterministic-summary",
        });
    }
}
